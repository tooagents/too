from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class ToolCallRequest(BaseModel):
    name: str | None = Field(default=None, description="Tool name")
    tool_choice: str | None = Field(default=None, description="Alias for tool name")
    arguments: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_tool_name(self) -> "ToolCallRequest":
        if not self.name and not self.tool_choice:
            raise ValueError("Either 'name' or 'tool_choice' is required")
        return self

    @property
    def tool_name(self) -> str:
        return str(self.name or self.tool_choice)
