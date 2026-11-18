from langgraph.prebuilt import ToolNode

# This node automatically executes any tools the LLM requested
tool_node = ToolNode(tools)