from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """
    This is what flows through your agent
    
    Messages is a list that keeps growing:
    - User questions
    - Agent responses
    - Tool results
    """
    messages: Annotated[Sequence[BaseMessage], "The conversation history"]

class FancierState(TypedDict):
    messages: Sequence[BaseMessage]
    user_id: str
    retry_count: int
    last_tool_used: str | None