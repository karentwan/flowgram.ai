"""Secrets traversal tests — mirrors Node lib/secrets.ts behavior."""

from __future__ import annotations

import pytest

from app.utils.secrets import decrypt_document_secrets, encrypt_document_secrets

# A minimal document matching FlowDocument shape: top-level nodes + a nested
# block (free-layout structure). Only mcp/agent nodes with constant
# headersValues get transformed; everything else is untouched.
SAMPLE_DOC: dict = {
    "nodes": [
        # mcp node with 3 header values: constant (plaintext), ref, template.
        {
            "id": "mcp_0",
            "type": "mcp",
            "data": {
                "server": {
                    "headersValues": {
                        "auth_token": {"type": "constant", "content": "sk-secret-123"},
                        "dynamic_ref": {"type": "ref", "content": ["start_0", "token"]},
                        "tmpl": {"type": "template", "content": "Bearer {{x}}"},
                        "empty_const": {"type": "constant", "content": ""},
                    }
                }
            },
        },
        # non-secret node type — must be untouched.
        {"id": "llm_0", "type": "llm", "data": {"server": {"headersValues": {"k": {"type": "constant", "content": "nope"}}}}},
    ],
    "blocks": [
        # nested agent node inside a block (free-layout nesting).
        {
            "nodes": [
                {
                    "id": "agent_0",
                    "type": "agent",
                    "data": {
                        "server": {
                            "headersValues": {
                                "nested_secret": {"type": "constant", "content": "nested-plain"}
                            }
                        }
                    },
                }
            ]
        }
    ],
}


@pytest.fixture(autouse=True)
def _key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a fixed key so encrypt/decrypt actually run."""
    import base64

    monkeypatch.setenv("FLOWGRAM_ENCRYPTION_KEY", base64.b64encode(b"K" * 32).decode())
    from app.core import config

    config.get_settings.cache_clear()


class TestEncryptDocumentSecrets:
    def test_encrypts_constant_string_headers(self) -> None:
        out = encrypt_document_secrets(SAMPLE_DOC)
        mcp = out["nodes"][0]
        hv = mcp["data"]["server"]["headersValues"]
        assert hv["auth_token"]["content"].startswith("enc::")
        assert hv["auth_token"]["content"] != "sk-secret-123"

    def test_skips_non_constant_headers(self) -> None:
        out = encrypt_document_secrets(SAMPLE_DOC)
        hv = out["nodes"][0]["data"]["server"]["headersValues"]
        # ref/template untouched
        assert hv["dynamic_ref"] == {"type": "ref", "content": ["start_0", "token"]}
        assert hv["tmpl"] == {"type": "template", "content": "Bearer {{x}}"}

    def test_skips_empty_constant(self) -> None:
        out = encrypt_document_secrets(SAMPLE_DOC)
        hv = out["nodes"][0]["data"]["server"]["headersValues"]
        assert hv["empty_const"]["content"] == ""  # empty → passthrough

    def test_skips_non_secret_node_types(self) -> None:
        out = encrypt_document_secrets(SAMPLE_DOC)
        llm_hv = out["nodes"][1]["data"]["server"]["headersValues"]
        assert llm_hv["k"]["content"] == "nope"  # llm is not a secret node

    def test_traverses_nested_blocks(self) -> None:
        out = encrypt_document_secrets(SAMPLE_DOC)
        agent_hv = out["blocks"][0]["nodes"][0]["data"]["server"]["headersValues"]
        assert agent_hv["nested_secret"]["content"].startswith("enc::")

    def test_does_not_mutate_input(self) -> None:
        original_content = SAMPLE_DOC["nodes"][0]["data"]["server"]["headersValues"]["auth_token"]["content"]
        encrypt_document_secrets(SAMPLE_DOC)
        assert SAMPLE_DOC["nodes"][0]["data"]["server"]["headersValues"]["auth_token"]["content"] == original_content


class TestDecryptDocumentSecrets:
    def test_roundtrip(self) -> None:
        encrypted = encrypt_document_secrets(SAMPLE_DOC)
        decrypted = decrypt_document_secrets(encrypted)
        # The constant secret values return to plaintext.
        assert decrypted["nodes"][0]["data"]["server"]["headersValues"]["auth_token"]["content"] == "sk-secret-123"
        assert decrypted["blocks"][0]["nodes"][0]["data"]["server"]["headersValues"]["nested_secret"]["content"] == "nested-plain"

    def test_decrypt_is_idempotent_on_plaintext(self) -> None:
        """decrypt() on already-plaintext values passes through."""
        out = decrypt_document_secrets(SAMPLE_DOC)
        assert out["nodes"][0]["data"]["server"]["headersValues"]["auth_token"]["content"] == "sk-secret-123"
