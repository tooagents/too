from app.lgraph.core_nodes.node_fin import call_agent
from app.lgraph.core_nodes.node_toolnode import tool_node
from app.lgraph.core_states.state_fin import AgentState
from langgraph.graph import StateGraph

# Create the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("agent", call_agent)
workflow.add_node("tools", tool_node)

# Set entry point
workflow.set_entry_point("agent")

# Add conditional edge from agent
workflow.add_conditional_edges(
    "agent",           # From this node
    should_continue,   # Use this function to decide
    {
        "tools": "tools",  # If "tools" is returned, go to tools node
        END: END           # If END is returned, finish
    }
)

# After tools execute, go back to agent
workflow.add_edge("tools", "agent")

# Compile into a runnable agent
agent = workflow.compile()