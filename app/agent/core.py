import os
from dotenv import load_dotenv

# Load environment variables from .env file automatically
load_dotenv()

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import get_rider_details, get_trip_details, check_payout_history
from app.agent.policy import check_refund_policy

# Initialize Groq LLM with the latest supported stable model
llm = ChatGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
    model_name="llama-3.1-70b-versatile",  # Fixed: Replaced decommissioned model
    temperature=0
)

# List of all tools our agent can use
tools = [
    get_rider_details, 
    get_trip_details, 
    check_payout_history, 
    check_refund_policy
]

# Create the LangGraph ReAct Agent
agent_executor = create_react_agent(
    model=llm, 
    tools=tools
)

def process_dispute_message(rider_id: str, message: str) -> str:
    """
    Takes a rider's message, runs it through the LangGraph agent,
    and returns the final AI response strictly grounded in data.
    """
    # Inject the SYSTEM_PROMPT directly as the first message to ensure framework compatibility
    inputs = {
        "messages": [
            ("system", SYSTEM_PROMPT),
            ("human", f"[Rider ID: {rider_id}] {message}")
        ]
    }
    
    # Run the agent reasoning and tool execution loop
    result = agent_executor.invoke(inputs)
    
    # Return the content of the last AI message
    return result["messages"][-1].content