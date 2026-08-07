"""Workflow CRUD + auth end-to-end tests via FastAPI TestClient.

Business logic (optimistic concurrency, secret encryption on write / decryption
on read, auth scoping) must match Node routers/workflow.ts.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


def _doc_with_secret(token: str = "sk-plain") -> dict[str, Any]:
    """A minimal document containing an mcp secret-bearing node."""
    return {
        "nodes": [
            {
                "id": "mcp_0",
                "type": "mcp",
                "data": {
                    "server": {
                        "headersValues": {"auth": {"type": "constant", "content": token}}
                    }
                },
            }
        ],
        "edges": [],
    }


class TestAuth:
    def test_whoami_unauthenticated_returns_null(self, client: TestClient) -> None:
        resp = client.get("/api/auth/whoami")
        assert resp.status_code == 200
        assert resp.json() is None

    def test_whoami_authenticated_returns_user(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        resp = client.get("/api/auth/whoami", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "u_test"
        assert body["name"] == "tester"

    def test_whoami_invalid_token_returns_null(self, client: TestClient) -> None:
        resp = client.get("/api/auth/whoami", headers={"Authorization": "Bearer wrong"})
        assert resp.status_code == 200
        assert resp.json() is None


class TestWorkflowCrud:
    def test_unauthenticated_list_returns_401(self, client: TestClient) -> None:
        resp = client.get("/api/workflow/list")
        assert resp.status_code == 401

    def test_create_then_get_roundtrip(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        # create
        resp = client.post(
            "/api/workflow/create",
            json={"name": "My Flow", "document": _doc_with_secret()},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        wf = resp.json()
        wf_id, version = wf["id"], wf["version"]
        assert version == 1

        # get — document comes back with secrets DECRYPTED
        resp = client.get("/api/workflow/get", params={"id": wf_id}, headers=auth_headers)
        assert resp.status_code == 200
        got = resp.json()
        assert got["name"] == "My Flow"
        assert got["document"]["nodes"][0]["data"]["server"]["headersValues"]["auth"]["content"] == "sk-plain"

    def test_list_omits_document(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        client.post(
            "/api/workflow/create",
            json={"name": "Flow A", "document": _doc_with_secret()},
            headers=auth_headers,
        )
        resp = client.get("/api/workflow/list", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert "document" not in items[0]
        assert items[0]["name"] == "Flow A"

    def test_update_with_correct_version_succeeds(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        created = client.post(
            "/api/workflow/create",
            json={"name": "V1", "document": _doc_with_secret()},
            headers=auth_headers,
        ).json()
        resp = client.post(
            "/api/workflow/update",
            json={
                "id": created["id"],
                "name": "V2",
                "version": 1,  # current version
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        out = resp.json()
        assert out["version"] == 2

    def test_update_with_stale_version_returns_409(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        created = client.post(
            "/api/workflow/create",
            json={"name": "V1", "document": _doc_with_secret()},
            headers=auth_headers,
        ).json()
        # bump to v2
        client.post(
            "/api/workflow/update",
            json={"id": created["id"], "name": "V2", "version": 1},
            headers=auth_headers,
        )
        # now try to update with the stale v1 → 409
        resp = client.post(
            "/api/workflow/update",
            json={"id": created["id"], "name": "V3", "version": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 409
        assert "Stale version" in resp.json()["detail"]

    def test_delete_removes_workflow(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        created = client.post(
            "/api/workflow/create",
            json={"name": "ToDelete", "document": _doc_with_secret()},
            headers=auth_headers,
        ).json()
        resp = client.post(
            "/api/workflow/delete", json={"id": created["id"]}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        # subsequent get → 404
        resp = client.get(
            "/api/workflow/get", params={"id": created["id"]}, headers=auth_headers
        )
        assert resp.status_code == 404

    def test_get_unknown_returns_404(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        resp = client.get(
            "/api/workflow/get", params={"id": "nonexistent"}, headers=auth_headers
        )
        assert resp.status_code == 404


class TestSecretsAtRest:
    """Secrets are encrypted in the DB but decrypted on read."""

    def test_document_is_encrypted_in_db(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db_session,
    ) -> None:
        from app.models import Workflow

        client.post(
            "/api/workflow/create",
            json={"name": "Encrypted", "document": _doc_with_secret("my-plain-secret")},
            headers=auth_headers,
        )
        # Read raw from DB (bypassing the API's decrypt step).
        wf = db_session.query(Workflow).first()
        assert wf is not None
        stored_content = wf.document["nodes"][0]["data"]["server"]["headersValues"]["auth"]["content"]
        assert stored_content.startswith("enc::")
        assert stored_content != "my-plain-secret"
