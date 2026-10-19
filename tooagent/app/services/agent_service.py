from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import HTTPException

from app.clients.mcp_client import MCPClient


class AgentService:
    def __init__(self, mcp_client: MCPClient) -> None:
        self.mcp_client = mcp_client

    def plan_tool_from_message(self, message: str) -> tuple[str | None, dict[str, Any] | None]:
        text = message.strip()
        low = text.lower()
        if "vendor" in low:
            return "lookup_vendor", {"name": text.split(":", 1)[1].strip() if ":" in text else "acme supplies"}
        if "bank" in low or "account" in low:
            return "query_bank", {"account_name": text.split(":", 1)[1].strip() if ":" in text else "ops-checking"}
        if "ocr" in low:
            return "ocr_extract", {"text": text.split(":", 1)[1].strip() if ":" in text else "Invoice 1001 paid"}
        if "tool1" in low:
            return "tool1", {"message": text.split(":", 1)[1].strip() if ":" in text else "hello from production flow"}
        if "tool2" in low:
            return "tool2", {}
        return None, None

    def build_plain_answer(self, message: str) -> str:
        if message.strip():
            return f"No tool call requested for: {message.strip()}"
        return "No tool call requested."

    def message_from_arguments(self, arguments: dict[str, Any]) -> str:
        value = arguments.get("message", "")
        return str(value) if value is not None else ""

    def build_answer(self, tool_name: str, result: dict[str, Any]) -> str:
        if tool_name == "tool_transaction2je":
            transaction_id = result.get("transaction_id")
            if transaction_id:
                return f"Transaction posted: {transaction_id}"
            return "Transaction tool completed."
        if tool_name == "lookup_vendor":
            return f"Vendor {result['name']} is {result['status']} ({result['risk_level']} risk)."
        if tool_name == "query_bank":
            return f"Account {result['account_name']} has {len(result['recent_transactions'])} recent txns."
        if tool_name == "ocr_extract":
            return f"OCR extracted {result['word_count']} words."
        if tool_name == "tool1":
            return f"tool1 echo: {result['echo']}"
        return f"tool2 backend status: {result.get('upstream', {}).get('status', 'unknown')}"

    async def run_tool(self, tool: str, arguments: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        started = time.perf_counter()

        def mark(step: str, **meta: Any) -> dict[str, Any]:
            return {
                "source": "tooagent",
                "step": step,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                **meta,
            }

        trace: list[dict[str, Any]] = [mark("request_received", tool=tool, arguments=arguments)]
        try:
            async with httpx.AsyncClient(timeout=210.0) as client:
                trace.append(mark("mcp_list_tools_start"))
                tools = await self.mcp_client.list_tools(client, headers=headers)
                trace.append(mark("mcp_list_tools_response", tools=[t["name"] for t in tools]))
                trace.append(mark("mcp_call_tool_start", tool=tool))
                result = await self.mcp_client.call_tool(client, tool, arguments, headers=headers)
                trace.append(
                    mark(
                        "mcp_call_tool_response",
                        result_keys=sorted(result.keys()) if isinstance(result, dict) else [],
                        result=result,
                    )
                )
        except Exception as exc:
            trace.append(mark("mcp_error", error=f"{type(exc).__name__}: {exc}"))
            raise HTTPException(status_code=502, detail={"error": "MCP call failed", "trace": trace}) from exc

        return {"answer": self.build_answer(tool, result), "tool": tool, "arguments": arguments, "result": result, "trace": trace}

    async def chat(
        self,
        tool_choice: str,
        arguments: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        choice = (tool_choice.strip() or "auto").lower()
        request_message = self.message_from_arguments(arguments)
        started = time.perf_counter()

        def mark(step: str, **meta: Any) -> dict[str, Any]:
            return {
                "source": "tooagent",
                "step": step,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                **meta,
            }

        trace: list[dict[str, Any]] = [
            mark("chat_request_received", tool_choice=choice, message=request_message)
        ]

        if choice == "plain":
            trace.append(mark("tool_choice_plain"))
            return {"answer": self.build_plain_answer(request_message), "trace": trace}

        if choice == "auto":
            tool_name, planned_arguments = self.plan_tool_from_message(request_message)
            trace.append(mark("tool_choice_auto_planned", tool=tool_name, arguments=planned_arguments))
            if tool_name is None or planned_arguments is None:
                trace.append(mark("final_answer_without_tool"))
                return {
                    "answer": "No tool call needed. Try vendor/bank/ocr/tool1/tool2 patterns.",
                    "trace": trace,
                }
            result = await self.run_tool(tool_name, planned_arguments, headers=headers)
            result["trace"] = trace + result["trace"]
            return result

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                trace.append(mark("mcp_list_tools_start"))
                tools = await self.mcp_client.list_tools(client, headers=headers)
        except Exception as exc:
            trace.append(mark("mcp_error", error=f"{type(exc).__name__}: {exc}"))
            raise HTTPException(status_code=502, detail={"error": "MCP tool lookup failed", "trace": trace}) from exc

        available_tool_names = {tool["name"] for tool in tools}
        trace.append(mark("mcp_list_tools_response", tools=sorted(available_tool_names)))

        if choice in available_tool_names:
            trace.append(mark("direct_tool_choice", tool=choice, arguments=arguments))
            result = await self.run_tool(choice, arguments, headers=headers)
            result["trace"] = trace + result["trace"]
            return result

        trace.append(mark("unknown_tool_choice_fallback_to_auto", unknown_tool_choice=choice))
        tool_name, planned_arguments = self.plan_tool_from_message(request_message)
        trace.append(mark("tool_choice_auto_planned", tool=tool_name, arguments=planned_arguments))
        if tool_name is None or planned_arguments is None:
            trace.append(mark("final_answer_without_tool"))
            return {
                "answer": f"Unknown tool_choice '{choice}', and auto planning did not select a tool.",
                "trace": trace,
            }
        result = await self.run_tool(tool_name, planned_arguments, headers=headers)
        result["trace"] = trace + result["trace"]
        return result
