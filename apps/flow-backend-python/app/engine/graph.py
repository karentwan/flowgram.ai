"""IR → LangGraph StateGraph builder.

Takes a validated ``WorkflowIR`` (from loader.load_ir) and compiles it into a
runnable LangGraph. Walks nodes once to register node functions, then wires
edges (plain + conditional). Loop bodies (nested subgraphs) are built
recursively into a body-runner the loop node drives in serial mode.

This is the heart of phase 3: the Python execution surface.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.core.logging import get_logger
from app.engine.loader import load_ir
from app.engine.state import FlowState, set_workflow_status
from app.nodes.agent import make_agent_node
from app.nodes.code import make_code_node
from app.nodes.condition import make_condition_router
from app.nodes.control import make_end_node, make_start_node
from app.nodes.http import make_http_node
from app.nodes.llm import make_llm_node
from app.nodes.loop import BodyRunner, make_loop_node
from app.nodes.mcp import make_mcp_node
from app.schemas.ir import WorkflowEdge, WorkflowIR, WorkflowNode

_log = get_logger(__name__)

# Node types that produce a LangGraph node function.
_NODE_FACTORIES = {
    "start": make_start_node,
    "end": make_end_node,
    "llm": make_llm_node,
    "http": make_http_node,
    "mcp": make_mcp_node,
    "agent": make_agent_node,
    "code": make_code_node,
}


class GraphBuilder:
    """Compiles a WorkflowIR into a LangGraph runnable graph."""

    def __init__(self, ir: WorkflowIR) -> None:
        self.ir = ir
        # id → node, for edge lookups.
        self.nodes_by_id: dict[str, WorkflowNode] = {n.id: n for n in _flatten_nodes(ir.nodes)}
        # Edges grouped by source for wiring. Top-level edges only here; nested
        # loop-body edges are handled when building the loop's body runner.
        self.edges_by_source: dict[str, list[WorkflowEdge]] = {}
        for e in ir.edges:
            self.edges_by_source.setdefault(e.source_node_id, []).append(e)

    def build(self):
        """Compile and return a runnable LangGraph."""
        graph = StateGraph(FlowState)

        # 1. Register all top-level node functions.
        for node in self.ir.nodes:
            self._register_node(graph, node)

        # 2. Wire edges.
        for node in self.ir.nodes:
            self._wire_edges(graph, node)

        # 3. Wire START → first node, and any dangling outputs → END.
        self._wire_entry_exit(graph)

        return graph.compile()

    def _register_node(self, graph: StateGraph, node: WorkflowNode) -> None:
        """Add a node function to the graph. Skips block-start/block-end markers."""
        ntype = node.type
        if ntype in ("block-start", "block-end", "comment", "group", "root", "break"):
            # break is handled as a state flag; no standalone node fn needed in
            # the serial loop driver (it sets BREAK_KEY via a tiny fn below).
            if ntype == "break":
                graph.add_node(node.id, _make_break_node_fn(node.id))
            return

        if ntype == "condition":
            # condition nodes have no executable fn (they only route); register
            # a pass-through so they can still be a node in the graph.
            graph.add_node(node.id, _passthrough_node(node.id))
            return

        if ntype == "loop":
            body_runner = self._build_loop_body_runner(node)
            graph.add_node(node.id, make_loop_node(node, body_runner))
            return

        factory = _NODE_FACTORIES.get(ntype)
        if factory is None:
            raise ValueError(f"No executor for node type '{ntype}' ({node.id})")
        graph.add_node(node.id, factory(node))

    def _wire_edges(self, graph: StateGraph, node: WorkflowNode) -> None:
        """Wire outgoing edges for a node. Handles conditional vs plain."""
        out_edges = self.edges_by_source.get(node.id, [])
        # Also check node-level edges (loop body has its own edges, but those
        # are consumed by the body runner, not wired into the top-level graph).
        if not out_edges:
            return

        if node.type == "condition":
            router = make_condition_router(node)
            # Map each port key → target node id; unmatched ("") → END.
            path_map: dict[str, str] = {}
            for e in out_edges:
                key = e.source_port_id or ""
                path_map[key] = e.target_node_id
            # Default route when no condition matches.
            default_target = self._default_after(node)
            path_map[""] = default_target
            graph.add_conditional_edges(node.id, router, path_map)
            return

        if len(out_edges) == 1:
            e = out_edges[0]
            graph.add_edge(node.id, e.target_node_id)
            return

        # Multiple unconditional edges = fan-out (parallel branches). LangGraph
        # supports add_edge to multiple targets via separate calls.
        for e in out_edges:
            graph.add_edge(node.id, e.target_node_id)

    def _wire_entry_exit(self, graph: StateGraph) -> None:
        # ENTRY: START → start node (or first node if no start).
        start_node = next((n for n in self.ir.nodes if n.type == "start"), None)
        if start_node is not None:
            graph.add_edge(START, start_node.id)
        elif self.ir.nodes:
            graph.add_edge(START, self.ir.nodes[0].id)

        # EXIT: any node with no outgoing edges → END (unless it's a condition,
        # which always has edges).
        targets = {e.target_node_id for e in self.ir.edges}
        sources = {e.source_node_id for e in self.ir.edges}
        for node in self.ir.nodes:
            if node.type in ("block-start", "block-end", "comment", "group", "root"):
                continue
            if node.id not in sources and node.type != "condition":
                graph.add_edge(node.id, END)

    def _default_after(self, condition_node: WorkflowNode) -> str:
        """Default target when no condition branch matches (next sequential or END)."""
        return END

    def _build_loop_body_runner(self, loop_node: WorkflowNode) -> BodyRunner | None:
        """Build a callable that runs one loop iteration's subgraph.

        Phase 3 builds the body subgraph from ``loop_node.blocks`` + nested edges,
        then wraps it so each invocation resolves loopOutputs for that iteration.
        """
        blocks = loop_node.blocks or []
        if not blocks:
            return None

        nested_edges = loop_node.edges or []
        body_nodes_by_id = {b.id: b for b in blocks if b.type not in ("block-start", "block-end")}

        # Build a subgraph for the loop body.
        body_graph_builder = StateGraph(FlowState)
        for b in body_nodes_by_id.values():
            self._register_node_into(body_graph_builder, b)
        # Wire nested edges.
        edges_by_src: dict[str, list[WorkflowEdge]] = {}
        for e in nested_edges:
            edges_by_src.setdefault(e.source_node_id, []).append(e)
        for src, outs in edges_by_src.items():
            for e in outs:
                if e.target_node_id in body_nodes_by_id or e.target_node_id in {b.id for b in blocks}:
                    if e.target_node_id in body_nodes_by_id:
                        body_graph_builder.add_edge(src, e.target_node_id)
        # Entry: block-start → first body node.
        first_body = next((b for b in blocks if b.type == "block-start"), None)
        first_exec = next(
            (b for b in blocks if b.type not in ("block-start", "block-end")), None
        )
        if first_body and first_exec:
            body_graph_builder.add_edge(START, first_exec.id)
        elif first_exec:
            body_graph_builder.add_edge(START, first_exec.id)
        # Exit: body nodes with no outgoing → END.
        nested_sources = {e.source_node_id for e in nested_edges}
        for b in body_nodes_by_id.values():
            if b.id not in nested_sources:
                body_graph_builder.add_edge(b.id, END)

        compiled = body_graph_builder.compile()
        loop_outputs_decl = loop_node.data.get("loopOutputs") or {}

        async def runner(state: dict[str, Any], item: Any, index: int, loop_id: str) -> dict[str, Any]:
            # Run the body subgraph with the parent state as input. Loop-local
            # variables (item/index) are passed via locals_map to template/ref
            # resolution, not via the state.
            result_state = await compiled.ainvoke(dict(state))
            # Collect declared loopOutputs by resolving their refs against the
            # post-execution state (body node outputs are in the data channel).
            from app.engine.values import resolve_ref

            locals_map = {"item": item, "index": index}
            collected: dict[str, Any] = {}
            for name, ref in loop_outputs_decl.items():
                collected[name] = resolve_ref(ref, result_state, locals_map)
            return collected

        return runner

    def _register_node_into(self, graph: StateGraph, node: WorkflowNode) -> None:
        """Register a node into an arbitrary graph (used for loop body subgraphs)."""
        ntype = node.type
        if ntype in ("block-start", "block-end", "comment", "group", "root"):
            return
        if ntype == "break":
            graph.add_node(node.id, _make_break_node_fn(node.id))
            return
        if ntype == "condition":
            graph.add_node(node.id, _passthrough_node(node.id))
            return
        if ntype == "loop":
            # Nested loop (loop inside loop): recursive.
            body_runner = self._build_loop_body_runner(node)
            graph.add_node(node.id, make_loop_node(node, body_runner))
            return
        factory = _NODE_FACTORIES.get(ntype)
        if factory is None:
            raise ValueError(f"No executor for node type '{ntype}' ({node.id})")
        graph.add_node(node.id, factory(node))


def _flatten_nodes(nodes: list[WorkflowNode]) -> list[WorkflowNode]:
    """Flatten top-level nodes (loop body blocks are handled separately)."""
    return list(nodes)


def _passthrough_node(node_id: str):
    """A no-op node fn (used by condition nodes, which only route)."""
    async def fn(state: dict[str, Any]) -> dict[str, Any]:
        return {}
    return fn


def _make_break_node_fn(node_id: str):
    """A node fn that sets the loop-break flag (serial loop checks it)."""
    from app.engine.state import BREAK_KEY

    async def fn(state: dict[str, Any]) -> dict[str, Any]:
        return {BREAK_KEY: True}
    return fn


def build_graph(schema: dict[str, Any] | str):
    """Parse + validate + compile a workflow schema into a runnable LangGraph."""
    ir = load_ir(schema)
    builder = GraphBuilder(ir)
    graph = builder.build()
    _log.info("graph built", node_count=len(ir.nodes), edge_count=len(ir.edges))
    return graph
