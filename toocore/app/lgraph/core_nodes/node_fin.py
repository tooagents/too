from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

llm = ChatOpenAI(model="gpt-4", temperature=0)

tools = [
    create_search_transactions_tool(search_space_id, db_session)
]

llm_with_tools=llm.bind_tools(tools)

# Create the system prompt
system_prompt = """You are a helpful AI financial assistant.

Your capabilities:
- Search transactions by merchant, category, or date
- Analyze portfolio performance
- Find tax optimization opportunities

Guidelines:
- Be concise and cite specific data
- Format currency as $X,XXX.XX
- Remind users to consult professionals for tax/investment advice"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="messages"),
])

async def call_agent(state: AgentState):
    """
    The agent node calls the LLM to decide the next action.
    
    The LLM can:
    1. Call one or more tools
    2. Generate a text response
    3. Both
    """
    messages = state["messages"]
    formatted = prompt.format_messages(messages=messages)
    
    return {"messages":[response]}

