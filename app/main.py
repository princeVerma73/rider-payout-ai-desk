from fastapi import FastAPI
from pydantic import BaseModel
from app.db.seed import seed_database

app = FastAPI(title="QuickDrop Rider Payout Dispute Desk")

# Jaise hi FastAPI start hoga, ye sabse pehle database banayega aur CSV load karega
@app.on_event("startup")
async def startup_event():
    seed_database()

class MessageRequest(BaseModel):
    message_id: str
    rider_id: str
    text: str
    received_at: str

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/messages")
async def receive_message(msg: MessageRequest):
    return {"reply": "Agent is under construction"}

@app.get("/trace/{rider_id}")
async def get_trace(rider_id: str):
    return []

@app.get("/ops/pending")
async def get_ops_pending():
    return []