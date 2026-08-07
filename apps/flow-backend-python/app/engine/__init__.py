"""LangGraph execution engine.

IR (from canvas) -> StateGraph -> run. Replaces js-core's engine/container.
Planned modules:
  - loader.py: IR JSON -> langgraph.StateGraph (薄 loader, option 1C)
  - state.py:  flat State ({nodeId}__{fieldName}, option V1)
  - runner.py: task lifecycle (in-memory task map + polling protocol)
"""
