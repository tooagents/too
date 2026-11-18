from langgraph.graph import END


def should_continue(state: AgentState):
    """
    Router function that determines the next step.
    
    Returns:
        "tools" - if the LLM wants to use tools
        END - if the LLM is done (just text response)
    """
    last_message = state["messages"][-1]
    
    # Check if the LLM included tool calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # No tool calls means we're done
    return END