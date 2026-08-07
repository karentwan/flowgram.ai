# LangGraph IR Contract

This document defines how a FlowGram `WorkflowSchema` (the canvas product) is
**interpreted by the Python LangGraph backend** as an execution IR.

**Design decision (grill, option 1C + V1):** We do NOT invent a new IR format.
`WorkflowSchema` is already a declarative graph description (nodes + edges +
nested subgraphs + path-based variable refs). Instead we publish a precise
**interpretation contract** so the Python loader can consume `WorkflowSchema`
JSON directly and build a LangGraph `StateGraph` from it.

## 1. Fields consumed vs ignored

### Consumed (execution-relevant)
| Field | Path | Meaning |
|---|---|---|
| node id | `node.id` | Stable node identity; becomes State field prefix |
| node type | `node.type` | Dispatches to a Python node executor (see §2) |
| node data | `node.data` | Node-specific config (loopFor, prompt, etc.) |
| node inputs | `node.data.inputs` | JSON Schema declaring expected input fields |
| node outputs | `node.data.outputs` | JSON Schema declaring produced output fields → State |
| node inputsValues | `node.data.inputsValues` | Bound input values (constant/ref/template) |
| edges | `workflow.edges` / `node.edges` | Control flow; branch via `sourcePortID` |
| nested subgraph | `node.blocks` + `node.edges` | Loop body (recursive WorkflowNodeSchema[]) |
| globalVariable | `workflow.globalVariable` | Global inputs JSON Schema |

### Ignored (canvas-only, not executed)
| Field | Why |
|---|---|
| `node.meta.position` / `canvasPosition` | Visual layout only |
| `node.meta` other keys | Visual only |
| `workflow.groups` | Visual grouping only |
| `block-start` / `block-end` nodes | Subgraph boundary markers; Python infers entry/exit from edges |
| `comment` / `group` node types | Non-execution |

## 2. Node type → Python executor mapping

| FlowGramNode | Python module | LangGraph primitive |
|---|---|---|
| `start` | `nodes.start` | Graph ENTRY; reads `data.outputs` to seed State |
| `end` | `nodes.end` | Graph EXIT; collects `inputsValues` as final outputs |
| `llm` | `nodes.llm` | Node fn: `langchain_openai.ChatOpenAI`.invoke |
| `http` | `nodes.http` | Node fn: `httpx` request |
| `code` | `nodes.code` | Node fn: `exec` Python (dev; prod sandbox TBD) |
| `condition` | `nodes.condition` | Conditional edge: each `conditions[].key` → branch |
| `loop` | `nodes.loop` | Subgraph; serial=for-loop, parallel=Send+reducer |
| `break` | `nodes.break` | Loop control: serial→stop, parallel→reducer stops fan-out |
| `mcp` | `nodes.mcp` | `langchain_mcp_adapters` |
| `agent` | `nodes.agent` | `create_react_agent` / subgraph |
| `block-start`/`block-end` | (none) | Ignored; subgraph entry/exit inferred from edges |
| `continue` | (none) | **Removed** (grill decision) — if present in legacy JSON, loader rejects |

## 3. Variable reference resolution (V1: node-centric → flat State)

`IFlowRefValue.content: string[]` is a path. Resolution rules:

| Path shape | Resolves to | Example |
|---|---|---|
| `[nodeId, field]` | State field `{nodeId}__{field}` | `['llm_0','result']` → `llm_0__result` |
| `[nodeId, field, sub]` | Nested: `State[{nodeId}__{field}][sub]` | `['http_0','body','name']` → `http_0__body['name']` |
| `[loopId_locals, 'item']` | Loop iteration item (subgraph-local) | `['loop_0_locals','item']` → current item |
| `[loopId_locals, 'index']` | Loop iteration index (subgraph-local) | `['loop_0_locals','index']` → current index |

**Non-ref value types** (`IFlowValue` union):
- `constant`: literal value (`{type:'constant', content: <val>}`)
- `template`: string interpolation (`{type:'template', content:'hi {{llm_0__name}}'}`) — `{{path}}` resolved against State
- `expression`: NOT exported by interface; loader rejects if encountered

**State field naming convention (hard invariant):**
- Format: `{nodeId}__{fieldName}` (double underscore separator)
- Every declared output (`node.data.outputs.properties[*]`) becomes a State field
- Loop aggregated outputs: `{loopId}__{outputName}` (array-typed, post-reducer)
- This convention is the contract between TS canvas and Python State.

## 4. Control flow → LangGraph edges

| FlowGram edge | LangGraph |
|---|---|
| `{source, target}` (no port) | `graph.add_edge(source, target)` |
| `{source, target, sourcePortID}` from a condition node | `graph.add_conditional_edges(source, fn, {portID: target})` where `fn` evaluates `conditions` and returns the matching `key` |
| Nested `node.edges` inside a loop | Edges within the loop subgraph |

## 5. Loop semantics (grill decisions)

| Canvas field | Value | Python behavior |
|---|---|---|
| `data.mode` | `'serial'` (default) | for-loop subgraph invocation, sequential |
| `data.mode` | `'parallel'` | LangGraph `Send` fan-out + reducer |
| `data.semaphore` | number (optional, parallel only) | `asyncio.Semaphore(n)` worker limit; actual concurrency = `min(n, len(loopFor))` |
| (none) | — | `mode` defaults to `'serial'` (backward compatible) |

`mode`/`semaphore` are **performance hints only** — they do NOT affect output order, error propagation, or break semantics (all follow LangGraph).

## 6. Versioning

The IR is `WorkflowSchema` itself. Schema evolution follows the existing
`packages/runtime/interface` versioning. The Python loader MUST be tolerant of
unknown node `data` fields (forward compat) but MUST reject unknown `node.type`
values and removed features (`continue` node).
