from fastapi import FastAPI
from pydantic import BaseModel
from app.agent.core import process_dispute_message

app = FastAPI(title="QuickDrop Support API")

class MessageRequest(BaseModel):
    rider_id: str
    text: str
    received_at: str

@app.get("/health")
async def health_check():
    """Check if the server is running normally."""
    return {"status": "ok"}

@app.post("/messages")
async def receive_message(msg: MessageRequest):
    """
    Receives dispute messages from the frontend.
    Passes the rider_id and message text to the LangGraph AI Agent for processing.
    """
    try:
        # Pass the incoming rider ID and message to the AI agent
        ai_reply = process_dispute_message(msg.rider_id, msg.text)
        return {"reply": ai_reply}
    except Exception as e:
        # Fallback mechanism in case the agent execution fails
        return {"reply": f"Internal System Error: {str(e)}"}

@app.get("/trace/{rider_id}")
async def get_trace(rider_id: str):
    """Returns the LangGraph execution trace logs for a specific rider."""
    return []

@app.get("/ops/pending")
async def get_ops_pending():
    """Returns the list of pending manual operations."""
    return []