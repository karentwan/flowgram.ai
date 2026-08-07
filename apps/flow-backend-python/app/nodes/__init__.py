"""Node executors (LangGraph node functions).

Semantic authority is LangGraph (stance A). One module per FlowGram node type:
  - start.py / end.py:    graph entry/exit
  - llm.py:               langchain-openai ChatOpenAI
  - http.py:              httpx (replaces Node global fetch)
  - condition.py:         LangGraph conditional edge
  - loop.py:              serial (for-loop) / parallel (Send + Semaphore)
  - code.py:              Python only (exec, prod sandbox TBD)
  - mcp.py:               langchain-mcp-adapters
  - agent.py:             create_react_agent / subgraph
"""
