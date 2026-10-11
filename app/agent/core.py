import os
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import get_rider_details, get_trip_details, check_payout_history
from app.agent.policy import check_refund_policy

# Initialize Groq LLM
llm = ChatGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
    model_name="llama3-70b-8192", 
    temperature=0
)

# List of all tools our agent can use
tools = [
    get_rider_details, 
    get_trip_details, 
    check_payout_history, 
    check_refund_policy
]

# Create the LangGraph ReAct Agent (Reasoning + Acting Loop)
agent_executor = create_react_agent(
    model=llm, 
    tools=tools, 
    state_modifier=SYSTEM_PROMPT
)

def process_dispute_message(rider_id: str, message: str) -> str:
    """
    Takes a rider's message, runs it through the LangGraph agent,
    and returns the final AI response.
    """
    # Create the input format LangGraph expects
    inputs = {"messages": [("human", f"[Rider ID: {rider_id}] {message}")]}
    
    # Run the agent loop (this is where the AI thinks and uses tools)
    result = agent_executor.invoke(inputs)
    
    # The result contains the whole chat history, we return the last AI message
    return result["messages"][-1].content