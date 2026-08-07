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
from app.nodes.base import NodeFn
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

    def build(self, checkpointer: Any = None):
        """Compile and return a runnable LangGraph.

        If checkpointer is provided, the graph persists State per step (enables
        resume via thread_id on crash/restart).
        """
        graph = StateGraph(FlowState)

        # 1. Register all top-level node functions.
        for node in self.ir.nodes:
            self._register_node(graph, node)

        # 2. Wire edges.
        for node in self.ir.nodes:
            self._wire_edges(graph, node)

        # 3. Wire START → first node, and any dangling outputs → END.
        self._wire_entry_exit(graph)

        return graph.compile(checkpointer=checkpointer)

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
        """Build a callable that runs one loop iteration's body nodes.

        Body nodes are executed directly (NOT via a compiled subgraph) so that:
          1. locals_map (item/index) threads through to every body node's
             template/ref resolution (a compiled subgraph would lose this —
             locals aren't expressible in LangGraph state).
          2. snapshots produced by body nodes merge back into the parent state
             (a subgraph returns its own state, orphaning snapshots).

        Execution order is derived from nested edges (topological), with
        block-start as entry and block-end as exit markers.
        """
        blocks = loop_node.blocks or []
        if not blocks:
            return None

        nested_edges = loop_node.edges or []
        body_nodes_by_id = {b.id: b for b in blocks if b.type not in ("block-start", "block-end")}
        block_marker_ids = {b.id for b in blocks if b.type in ("block-start", "block-end")}

        # Build body node fns (reuse the same factories as top-level nodes).
        body_fns: dict[str, NodeFn] = {}
        for b in body_nodes_by_id.values():
            body_fns[b.id] = self._make_node_fn(b)

        # Compute execution order: BFS from block-start's successor.
        start_ids = [
            e.target_node_id
            for e in nested_edges
            if e.source_node_id in {x for x in block_marker_ids if any(b.id == x and b.type == "block-start" for b in blocks)}
            and e.target_node_id in body_nodes_by_id
        ]
        if not start_ids:
            start_ids = [next(iter(body_nodes_by_id))] if body_nodes_by_id else []
        # Adjacency among body nodes (skip edges touching markers).
        adj: dict[str, list[str]] = {nid: [] for nid in body_nodes_by_id}
        for e in nested_edges:
            if e.source_node_id in body_nodes_by_id and e.target_node_id in body_nodes_by_id:
                adj[e.source_node_id].append(e.target_node_id)
        # Topo order via BFS from starts.
        ordered: list[str] = []
        seen: set[str] = set()
        queue = list(start_ids)
        while queue:
            nid = queue.pop(0)
            if nid in seen or nid not in body_nodes_by_id:
                continue
            seen.add(nid)
            ordered.append(nid)
            queue.extend(adj.get(nid, []))
        # Append any unreached body nodes (defensive — shouldn't happen).
        for nid in body_nodes_by_id:
            if nid not in seen:
                ordered.append(nid)

        loop_outputs_decl = loop_node.data.get("loopOutputs") or {}

        async def runner(state: dict[str, Any], item: Any, index: int, loop_id: str) -> dict[str, Any]:
            # locals_map threads into every body node's value resolution.
            locals_map = {"item": item, "index": index}
            # Run body nodes in order against the parent state, merging each
            # node's partial update (outputs + snapshots) back into state.
            for nid in ordered:
                fn = body_fns.get(nid)
                if fn is None:
                    continue
                # The node fn reads state + (for templates) locals via the
                # module-level resolver; locals are passed by stashing them in
                # state under a per-loop key the resolver reads.
                _set_loop_locals(state, loop_id, locals_map)
                update = await fn(state)
                if isinstance(update, dict):
                    _merge_update(state, update)
            # Collect declared loopOutputs from the now-updated state.
            from app.engine.values import resolve_ref

            collected: dict[str, Any] = {}
            for name, ref in loop_outputs_decl.items():
                collected[name] = resolve_ref(ref, state, locals_map)
            return collected

        return runner

    def _make_node_fn(self, node: WorkflowNode) -> NodeFn:
        """Build a node fn from an IR node (same logic as _register_node_into
        but returns the fn instead of adding it to a graph). Used by the loop
        body runner to execute body nodes directly."""
        ntype = node.type
        if ntype in ("block-start", "block-end", "comment", "group", "root"):
            async def _noop(state): return {}
            return _noop  # type: ignore[return-value]
        if ntype == "break":
            return _make_break_node_fn(node.id)
        if ntype == "condition":
            return _passthrough_node(node.id)
        if ntype == "loop":
            body_runner = self._build_loop_body_runner(node)
            return make_loop_node(node, body_runner)
        factory = _NODE_FACTORIES.get(ntype)
        if factory is None:
            raise ValueError(f"No executor for node type '{ntype}' ({node.id})")
        return factory(node)

    def _register_node_into(self, graph: StateGraph, node: WorkflowNode) -> None:
        """Register a node into an arbitrary graph (used for loop body subgraphs)."""
        graph.add_node(node.id, self._make_node_fn(node))


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


# Loop-locals stash: body nodes read locals from state (since their fns are
# called without a locals_map arg). Keyed by loop_id under __loop_locals__.
_LOOP_LOCALS_KEY = "__loop_locals__"


def _set_loop_locals(state: dict[str, Any], loop_id: str, locals_map: dict[str, Any]) -> None:
    state.setdefault(_LOOP_LOCALS_KEY, {})[loop_id] = locals_map


def get_loop_locals(state: dict[str, Any], loop_id: str) -> dict[str, Any] | None:
    """Public: value resolvers call this to fetch the active loop's locals.

    The resolver matches the loop_id from a ref/template path like
    ``loop_RER-F_locals.item`` by checking which stashed loop_id the scope
    prefix belongs to.
    """
    return state.get(_LOOP_LOCALS_KEY, {}).get(loop_id)


def _merge_update(state: dict[str, Any], update: dict[str, Any]) -> None:
    """Merge a node fn's partial update into state (mirrors the FlowState
    reducers: data/outputs/node_status/snapshots merge; scalars overwrite)."""
    from app.engine.state import (
        DATA_KEY,
        NODE_STATUS_KEY,
        OUTPUTS_KEY,
        SNAPSHOTS_KEY,
    )

    for k, v in update.items():
        if k == DATA_KEY and isinstance(v, dict):
            state.setdefault(DATA_KEY, {}).update(v)
        elif k == NODE_STATUS_KEY and isinstance(v, dict):
            state.setdefault(NODE_STATUS_KEY, {}).update(v)
        elif k == OUTPUTS_KEY and isinstance(v, dict):
            state.setdefault(OUTPUTS_KEY, {}).update(v)
        elif k == SNAPSHOTS_KEY and isinstance(v, list):
            state.setdefault(SNAPSHOTS_KEY, []).extend(v)
        else:
            state[k] = v


def build_graph(schema: dict[str, Any] | str, checkpointer: Any = None):
    """Parse + validate + compile a workflow schema into a runnable LangGraph.

    If ``checkpointer`` is provided, the compiled graph persists every step's
    State (enables resume-on-crash via thread_id). If None, runs in-memory only.
    """
    ir = load_ir(schema)
    builder = GraphBuilder(ir)
    graph = builder.build(checkpointer=checkpointer)
    _log.info("graph built", node_count=len(ir.nodes), edge_count=len(ir.edges), has_checkpointer=checkpointer is not None)
    return graph
