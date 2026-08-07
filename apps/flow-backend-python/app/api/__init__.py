"""HTTP API layer (FastAPI routers).

Mirrors the Node backend's tRPC procedures:
  - auth.whoami          -> routers/auth.py
  - workflow.{list,...}  -> routers/workflow.py
  - task.{run,...}       -> routers/task.py  (LangGraph execution)
"""
