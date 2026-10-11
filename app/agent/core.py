from dotenv import load_dotenv
load_dotenv(override=True)

import os
import time
import logging

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import (
    get_rider_details,
    get_trip_details,
    get_trips_by_date,
    check_payout_history,
    initiate_payout,
    escalate_to_ops
)
from app.agent.policy import check_refund_policy
from app.agent.services import record_trace
from app.db.session import SessionLocal
from app.db.models import ConversationMessage

logger = logging.getLogger(__name__)

# Initialize Groq LLM with fallback chain across available models
primary_model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
candidate_models = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
model_order = [primary_model] + [m for m in candidate_models if m != primary_model]

primary_llm = ChatGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
    model_name=model_order[0],
    temperature=0,
    max_retries=1
)
fallback_llms = [
    ChatGroq(api_key=os.environ.get("GROQ_API_KEY"), model_name=m, temperature=0, max_retries=1)
    for m in model_order[1:]
]
llm = primary_llm.with_fallbacks(fallback_llms)

# Full tool suite for the autonomous dispute agent
tools = [
    get_rider_details,
    get_trip_details,
    get_trips_by_date,
    check_payout_history,
    check_refund_policy,
    initiate_payout,
    escalate_to_ops
]

# Create the LangGraph ReAct Agent
agent_executor = create_react_agent(
    model=llm,
    tools=tools
)

def get_recent_history(rider_id: str, limit: int = 4) -> list:
    """Fetches recent conversation turns from the database for multi-turn context without duplication."""
    db = SessionLocal()
    history = []
    try:
        msgs = db.query(ConversationMessage).filter(
            ConversationMessage.rider_id == rider_id,
            ConversationMessage.sender == "rider"
        ).order_by(ConversationMessage.id.desc()).limit(limit).all()
        
        # Order chronologically
        msgs.reverse()
        for m in msgs:
            history.append(("human", m.text))
            if m.reply_text:
                history.append(("ai", m.reply_text))
    except Exception as e:
        logger.warning(f"Could not load conversation history for {rider_id}: {e}")
    finally:
        db.close()
    return history

def process_dispute_message(rider_id: str, message: str, message_id: str = None, received_at: str = None) -> str:
    """
    Takes a rider's message, incorporates multi-turn memory, runs it through the
    LangGraph ReAct agent, records audit trace steps, and returns the AI reply.
    """
    # 1. Record incoming message in trace audit log
    record_trace(
        rider_id=rider_id,
        step_type="message_in",
        name="incoming_message",
        input_data={"message_id": message_id, "text": message, "received_at": received_at},
        output_data=None
    )

    # 2. Build conversational message sequence with history
    messages = [("system", SYSTEM_PROMPT)]
    past_turns = get_recent_history(rider_id)
    messages.extend(past_turns)
    
    # Append current message with explicit rider identity grounding
    messages.append(("human", f"[Rider ID: {rider_id}] {message}"))
    
    inputs = {"messages": messages}

    reply_content = None
    for attempt in range(3):
        try:
            # 3. Execute agent loop
            result = agent_executor.invoke(inputs)
            reply_content = result["messages"][-1].content
            break
        except Exception as e:
            err_msg = str(e)
            print(f"ACTUAL CRASH REASON (attempt {attempt+1}/3): {err_msg}")
            if ("429" in err_msg or "rate_limit" in err_msg.lower() or "too large" in err_msg.lower()) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            logger.error(f"Error during agent execution: {e}", exc_info=True)
            record_trace(
                rider_id=rider_id,
                step_type="error",
                name="agent_execution_failure",
                input_data={"message": message},
                output_data=err_msg
            )
            reply_content = "Bhai, humare system mein thodi takneeki samasya aayi hai. Kripya thodi der baad dobara message karein."
            break

    # 4. Record agent reply in trace log
    record_trace(
        rider_id=rider_id,
        step_type="reply",
        name="agent_reply",
        input_data=None,
        output_data=reply_content
    )

    return reply_content