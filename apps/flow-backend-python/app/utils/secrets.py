"""Secret traversal for workflow documents — mirrors Node lib/secrets.ts.

Secrets live inside MCP/Agent node configs at
``data.server.headersValues.{*}.content`` (only ``constant``-type entries hold a
literal secret; ref/template entries reference upstream variables and carry no
plaintext). This module walks the document, encrypting those constant contents
on write (before persistence) and decrypting them on read.

Cross-backend invariant: applies the same traversal as Node's
encryptDocumentSecrets / decryptDocumentSecrets, so a document encrypted by
Node decrypts here and vice versa.
"""

from __future__ import annotations

import copy
from typing import Any

from app.utils.crypto import decrypt, encrypt

# Node types whose data.server.headersValues carry secrets.
SECRET_NODE_TYPES = frozenset({"mcp", "agent"})


def _iter_nodes(doc: dict[str, Any]):
    """Yield each node in the document.

    Document shape (matches Node's FlowDocument):
      - top-level ``nodes`` list
      - free-layout nests child nodes under ``blocks[].nodes``
    """
    for node in doc.get("nodes") or []:
        yield node
    for block in doc.get("blocks") or []:
        for node in block.get("nodes") or []:
            yield node


def _get_headers_values(node: dict[str, Any]) -> dict[str, Any] | None:
    """Return the node's ``data.server.headersValues`` if it's a secret-bearing node."""
    if node.get("type") not in SECRET_NODE_TYPES:
        return None
    data = node.get("data") or {}
    server = data.get("server") or {}
    return server.get("headersValues")


def _transform_values(headers_values: dict[str, Any], fn) -> None:
    """Apply ``fn`` (encrypt or decrypt) to each constant string content in-place."""
    for value in headers_values.values():
        if (
            isinstance(value, dict)
            and value.get("type") == "constant"
            and isinstance(value.get("content"), str)
            and value["content"]  # skip empty — matches Node's `&& value.content`
        ):
            value["content"] = fn(value["content"])


def encrypt_document_secrets(doc: dict[str, Any]) -> dict[str, Any]:
    """Encrypt every constant header value in the document. Returns a deep copy.

    Call before persisting to the DB. ref/template entries are skipped.
    Mirrors Node's encryptDocumentSecrets.
    """
    next_doc = copy.deepcopy(doc)
    for node in _iter_nodes(next_doc):
        headers_values = _get_headers_values(node)
        if headers_values:
            _transform_values(headers_values, encrypt)
    return next_doc


def decrypt_document_secrets(doc: dict[str, Any]) -> dict[str, Any]:
    """Decrypt every constant header value in the document. Returns a deep copy.

    Call before returning a document to the editor or handing it to the executor.
    Mirrors Node's decryptDocumentSecrets.
    """
    next_doc = copy.deepcopy(doc)
    for node in _iter_nodes(next_doc):
        headers_values = _get_headers_values(node)
        if headers_values:
            _transform_values(headers_values, decrypt)
    return next_doc
