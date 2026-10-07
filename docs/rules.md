# Coding Rules
## QuickDrop — Rider Payout Dispute Desk

---

## 1. Language & Stack

- **Backend**: Python 3.11+ (preferred) or Node.js 20+
- **Web Framework**: FastAPI (Python) or Express (Node)
- **Database**: PostgreSQL via SQLAlchemy or Psycopg2 (Python) / Knex (Node)
- **AI/Agent**: Any framework — LangChain, LlamaIndex, raw SDK calls, or none
- **LLM**: Any provider — Groq, Gemini (free tiers sufficient)
- **Container**: Docker + docker compose

---

## 2. Project Structure (Recommended)

```
/
├── app/
│   ├── main.py            # FastAPI entry point
│   ├── agent/
│   │   ├── core.py        # Agent loop
│   │   └── tools.py       # Tool definitions
│   ├── api/
│   │   ├── messages.py    # POST /messages
│   │   ├── trace.py       # GET /trace/{rider_id}
│   │   └── ops.py         # GET /ops/pending
│   ├── db/
│   │   ├── models.py      # SQLAlchemy models
│   │   └── seed.py        # CSV seeder
│   └── payswift.py        # PaySwift client
├── evals/
│   └── run.py             # Eval runner
├── ops-ui/                # Ops dashboard (HTML/JS or React)
├── payswift/              # DO NOT MODIFY
├── data/                  # DO NOT MODIFY
├── docs/                  # This folder
├── ai-logs/               # Your AI session exports
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 3. API Contract Rules

These shapes are **fixed** and will be tested against other implementations:

### POST /messages
```json
// Request
{ "message_id": "wamid.XYZ", "rider_id": "R003", "text": "...", "received_at": "2026-09-22T09:00:00+05:30" }

// Response
{ "reply": "Text that goes back to rider" }
```
- You may add extra fields; only `reply` is required
- Must respond within ~10 seconds

### GET /trace/{rider_id}
```json
[
  { "at": "<ISO>", "type": "message_in", "name": "...", "input": {...}, "output": null },
  { "at": "<ISO>", "type": "tool_call",  "name": "...", "input": {...}, "output": {...} },
  { "at": "<ISO>", "type": "decision",   "name": "...", "input": {...}, "output": {...} },
  { "at": "<ISO>", "type": "reply",      "name": "...", "input": null,  "output": "<text>" }
]
```
- `type` must be one of: `message_in`, `tool_call`, `decision`, `reply`, `error`

### GET /ops/pending
```json
[
  { "id": "...", "rider_id": "...", "type": "approval",   "amount": 120, "reason": "...", "created_at": "<ISO>" },
  { "id": "...", "rider_id": "...", "type": "escalation", "amount": null,"reason": "...", "created_at": "<ISO>" }
]
```

---

## 4. Payout Policy Implementation

> Source of truth: `docs/policy.md`

```python
def calculate_trip_fare(distance_km: float, surge: float) -> int:
    base = 25
    extra_km = max(0, distance_km - 2)
    raw = (base + extra_km * 6) * surge
    return round(raw)  # Python round() uses banker's rounding — use math.floor(x + 0.5) instead

def is_incentive_earned(completed_trips_count: int) -> bool:
    return completed_trips_count >= 12  # 12+ completed trips in a calendar day (IST)

INCENTIVE_AMOUNT = 150
CANCEL_PENALTY = -10       # per rider-cancelled trip
DISPUTE_WINDOW_DAYS = 7    # only look at last 7 days from message date
AUTO_PAY_LIMIT = 200       # max auto-pay per dispute
AUTO_PAY_DAILY_LIMIT = 1   # max auto-pay events per rider per day
```

**Rounding rule**: `round(x + 0.5 - 0.5)` is NOT safe in Python — use `math.floor(x + 0.5)` or `Decimal` with `ROUND_HALF_UP`.

**IST timezone**: All day boundaries use `Asia/Kolkata` (UTC+5:30), not UTC.

---

## 5. Critical Rules

| Rule | Detail |
|---|---|
| **Idempotency** | Same `message_id` → return the same reply, no re-processing |
| **No overpayment** | Code must enforce: `payment_amount <= calculated_owed` |
| **Rider isolation** | Only query/act on the `rider_id` from the webhook, never from message text |
| **Once-per-day auto-pay** | Check `payswift_log` or DB for same-day auto-pays before calling PaySwift |
| **7-day window** | Reject disputes outside the 7-day window with a polite explanation |
| **PaySwift idempotency** | Use `Idempotency-Key` header (e.g., `dispute-{rider_id}-{trip_id}`) |
| **No secrets in code** | All keys in `.env`; list all in `.env.example` |

---

## 6. Environment Variables

```bash
# .env.example
DATABASE_URL=postgresql://user:password@postgres:5432/quickdrop
PAYSWIFT_BASE_URL=http://payswift:8081
LLM_API_KEY=your_key_here
LLM_PROVIDER=gemini           # or groq, openai, etc.
LLM_MODEL=gemini-2.0-flash    # or llama-3.1-8b-instant, etc.
PORT=8000
```

---

## 7. Error Handling

- All tool errors must be caught and logged as `type: "error"` steps in trace
- PaySwift 429 (rate limit) → retry with exponential backoff
- PaySwift 5xx → log, do not mark as paid, escalate if needed
- PaySwift 409 (conflict) → already paid, check and reconcile
- DB errors → return 500 with a safe message, do not leak stack traces

---

## 8. Testing & Evals

```bash
# Eval runner signature (fixed)
python evals/run.py http://localhost:8000

# It must:
# 1. Run each conversation in data/conversations.json against a FRESH system
# 2. Check: expected.payout matches actual PaySwift payout
# 3. Check: expected.approval matches ops/pending amount
# 4. Check: expected.escalation matches escalation status
# 5. Check: expected.reply_mentions are all present in the reply
# 6. Print a summary report
```

- Evals use **only** `POST /messages` and PaySwift API — no DB inspection
- Each conversation runs on a fresh system (clear state between runs)

---

## 9. AI Logs

Export your AI session logs to `ai-logs/`. One file per session.

| Tool | Export Command |
|---|---|
| Antigravity | Chat export, or `antigravity-history` tool |
| Claude Code | `~/.claude/projects/<project>/<session>.jsonl` |
| Gemini CLI | `/export jsonl --output <file>` |
| ChatGPT | Settings → Data controls → Export |
| Cursor | Chat menu (…) → Export Chat |
