from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_choice: str = Field(
        default="auto",
        description="Use 'auto' for backend planning, 'plain' for no tool call, or a tool name to call directly.",
    )
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolRunRequest(BaseModel):
    tool: str = Field(..., description="Tool name")
    arguments: dict[str, Any] = Field(default_factory=dict)
