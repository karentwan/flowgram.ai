"""Task API HTTP tests via TestClient.

Covers the validate endpoint fully (synchronous) and the run endpoint's
response shape. Full run→result polling is exercised in test_engine_e2e.py
at the TaskManager level (avoids TestClient event-loop timing complexity).
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient


def _echo_schema() -> dict:
    return {
        "nodes": [
            {
                "id": "start_0",
                "type": "start",
                "meta": {"position": {"x": 0, "y": 0}},
                "data": {
                    "outputs": {
                        "type": "object",
                        "properties": {"message": {"type": "string"}},
                    }
                },
            },
            {
                "id": "end_0",
                "type": "end",
                "meta": {"position": {"x": 100, "y": 0}},
                "data": {
                    "inputs": {"type": "object"},
                    "inputsValues": {
                        "echo": {"type": "ref", "content": ["start_0", "message"]}
                    },
                },
            },
        ],
        "edges": [{"sourceNodeID": "start_0", "targetNodeID": "end_0"}],
    }


class TestTaskValidate:
    def test_validate_accepts_valid_schema(self, client: TestClient) -> None:
        resp = client.post(
            "/api/task/validate",
            json={"schema": json.dumps(_echo_schema()), "inputs": {"message": "hi"}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is True
        assert body.get("errors") is None

    def test_validate_rejects_continue_node(self, client: TestClient) -> None:
        bad = {
            "nodes": [
                {"id": "s", "type": "start", "meta": {"position": {"x": 0, "y": 0}}, "data": {}},
                {"id": "c", "type": "continue", "meta": {"position": {"x": 0, "y": 0}}, "data": {}},
            ],
            "edges": [{"sourceNodeID": "s", "targetNodeID": "c"}],
        }
        resp = client.post(
            "/api/task/validate", json={"schema": json.dumps(bad), "inputs": {}}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False
        assert body["errors"] is not None
        assert any("removed" in e for e in body["errors"])

    def test_validate_rejects_invalid_json(self, client: TestClient) -> None:
        resp = client.post(
            "/api/task/validate", json={"schema": "not json{", "inputs": {}}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False


class TestTaskRunShape:
    def test_run_returns_task_id(self, client: TestClient) -> None:
        resp = client.post(
            "/api/task/run",
            json={"schema": json.dumps(_echo_schema()), "inputs": {"message": "hi"}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "taskID" in body
        assert body["taskID"].startswith("task_")

    def test_result_unknown_returns_null(self, client: TestClient) -> None:
        # Use GET with query param (Node uses ?taskID=).
        resp = client.get("/api/task/result", params={"taskID": "nonexistent"})
        # Node returns undefined → JSON null; status 200.
        assert resp.status_code == 200
        assert resp.json() is None

    def test_report_unknown_returns_null(self, client: TestClient) -> None:
        resp = client.get("/api/task/report", params={"taskID": "nonexistent"})
        assert resp.status_code == 200
        assert resp.json() is None

    def test_cancel_unknown_returns_success_false(self, client: TestClient) -> None:
        resp = client.put("/api/task/cancel", json={"taskID": "nonexistent"})
        assert resp.status_code == 200
        assert resp.json() == {"success": False}
