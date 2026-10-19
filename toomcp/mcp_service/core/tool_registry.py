from __future__ import annotations

from typing import Any

TOOLS: dict[str, dict[str, Any]] = {
    "lookup_vendor": {
        "description": "Lookup vendor by exact name.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    "query_bank": {
        "description": "Get recent transactions for an account.",
        "input_schema": {
            "type": "object",
            "properties": {"account_name": {"type": "string"}},
            "required": ["account_name"],
        },
    },
    "ocr_extract": {
        "description": "Extract basic fields from OCR text input.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    "tool1": {
        "description": "MCP-native demo tool that echoes a message with metadata.",
        "input_schema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    },
    "tool2": {
        "description": "Backend-forwarded demo tool that checks backend health.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    "tool_transaction2je": {
        "description": (
            "Forward a natural language transaction message to the backend, "
            "where it can be posted or drafted as accounting transaction and journal entry data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    },
}


def has_tool(name: str) -> bool:
    return name in TOOLS


def list_tool_descriptors() -> list[dict[str, Any]]:
    return [{"name": name, **meta} for name, meta in TOOLS.items()]
