# Architecture
## QuickDrop — Rider Payout Dispute Desk

---

## 1. High-Level Overview

```
WhatsApp (Rider)
       │
       │  POST /messages (vendor webhook)
       ▼
┌─────────────────────────────────────────────────┐
│               Your Service (port 8000)          │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │           FastAPI / Express Router         │  │
│  │  POST /messages                           │  │
│  │  GET  /trace/{rider_id}                   │  │
│  │  GET  /ops/pending                        │  │
│  │  GET  /health                             │  │
│  └────────────────┬──────────────────────────┘  │
│                   │                             │
│  ┌────────────────▼──────────────────────────┐  │
│  │              AI Agent Core                │  │
│  │  - Conversation memory (per rider)        │  │
│  │  - Tool orchestration                     │  │
│  │  - Decision engine (auto-pay vs approve)  │  │
│  └──┬─────────┬──────────┬───────────────────┘  │
│     │         │          │                      │
│  ┌──▼──┐  ┌──▼──┐  ┌────▼────┐                │
│  │Trip │  │Pay  │  │PaySwift │                │
│  │Tool │  │out  │  │Tool     │                │
│  │     │  │Tool │  │(payout) │                │
│  └──┬──┘  └──┬──┘  └────┬────┘                │
│     └────────┴──────────┘                      │
│               │                                │
│  ┌────────────▼────────────┐                   │
│  │       PostgreSQL DB      │                   │
│  │  - riders               │                   │
│  │  - trips                │                   │
│  │  - payout_lines         │                   │
│  │  - conversations        │                   │
│  │  - trace_steps          │                   │
│  │  - ops_pending          │                   │
│  └─────────────────────────┘                   │
└─────────────────────────────────────────────────┘
       │
       │  POST /v1/payouts
       ▼
┌──────────────────────┐
│  PaySwift (port 8081) │
│  In-memory ledger    │
└──────────────────────┘
```

---

## 2. Component Breakdown

### 2.1 API Layer

Exposed endpoints:

| Method | Path | Description |
|---|---|---|
| `POST` | `/messages` | Receives rider WhatsApp message from vendor |
| `GET` | `/trace/{rider_id}` | Full agent trace for a rider |
| `GET` | `/ops/pending` | All items pending human review |
| `GET` | `/health` | Liveness check (returns 200) |

### 2.2 AI Agent Core

The agent is the central decision engine. It:

1. **Receives** a rider message with context
2. **Recalls** conversation history from the DB
3. **Calls tools** to look up trips and payout data
4. **Calculates** expected payout using the policy
5. **Decides** to auto-pay, queue for approval, or escalate
6. **Logs every step** to `trace_steps` table
7. **Returns** a human-readable reply in Hindi/English

**What the model decides:**
- Which trips/dates are relevant to the complaint
- Whether the complaint is valid
- What to say to the rider

**What the code decides:**
- Whether auto-pay threshold is met (≤ ₹200)
- Whether it's the first payment today (once-per-day rule)
- Deduplication of message IDs
- Actual PaySwift API call

### 2.3 Tools

| Tool | Input | Output |
|---|---|---|
| `get_trips` | `rider_id`, `date` | List of trips with distance, surge, status |
| `get_payout_lines` | `rider_id`, `date` | Actual payout lines from the DB |
| `calculate_expected_payout` | trip data | Expected ₹ per policy |
| `initiate_payment` | `rider_id`, `amount`, `reason` | Triggers PaySwift or queues for ops |
| `escalate_to_ops` | `rider_id`, `reason` | Creates an escalation entry |

### 2.4 Database Schema (PostgreSQL)

```sql
-- Seeded from CSV exports
riders          (rider_id, name, city, joined_on)
trips           (trip_id, rider_id, started_at, status, distance_km, surge_multiplier)
payout_lines    (line_id, payout_date, rider_id, line_type, trip_id, amount)

-- Runtime
conversations   (id, rider_id, message_id, role, text, received_at, created_at)
trace_steps     (id, rider_id, at, type, name, input_json, output_json)
ops_pending     (id, rider_id, type, amount, reason, status, created_at, resolved_at)
payswift_log    (id, rider_id, amount, reference, payswift_payout_id, created_at)
```

### 2.5 PaySwift Integration

```
POST /v1/payouts
  { "rider_id": "R003", "amount": 25, "reference": "dispute-T926334" }
→ 201 { "payout_id": "...", "status": "success" }
```

- **Idempotency-Key** header used to prevent double payments on retries
- Runs on port `8081` in sandbox mode
- In-memory ledger; resets on restart

---

## 3. Infrastructure

### 3.1 Docker Compose

```yaml
services:
  payswift:          # port 8081 — pre-built, do not modify
  app:               # port 8000 — your service
  postgres:          # port 5432 — persistent storage
```

### 3.2 Startup Flow

```
docker compose up
  → postgres starts, runs migrations
  → payswift starts
  → app starts, seeds data from CSVs, waits for /health 200
```

### 3.3 GitHub Actions (CI)

On every push to `main`:
1. Build Docker images
2. Run `docker compose up`
3. Wait for `/health` 200
4. Run eval suite: `python evals/run.py http://localhost:8000`
5. Report pass/fail

---

## 4. Conversation Flow (State Machine)

```
[New Message]
     │
     ▼
[Dedup check: message_id seen?] → YES → return cached reply
     │ NO
     ▼
[Load conversation history]
     │
     ▼
[Agent: classify intent]
     ├── Vague ("payout galat aaya") → ask clarifying question
     ├── Specific (trip/date) → lookup tools → calculate
     └── Irrelevant / injection → safe refusal
     │
     ▼
[Compute dispute amount]
     │
     ├── amount = 0 → explain to rider (no discrepancy)
     │
     ├── 0 < amount ≤ 200 AND first payment today
     │       → auto-pay via PaySwift → confirm to rider
     │
     ├── amount > 200 OR repeat payment today
     │       → queue ops_pending (approval) → tell rider
     │
     └── Ambiguous/shady → ops_pending (escalation) → tell rider
     │
     ▼
[Log all steps to trace_steps]
     │
     ▼
[Return reply]
```

---

## 5. Security Considerations

| Threat | Mitigation |
|---|---|
| Rider impersonation | `rider_id` derived from phone number (vendor-controlled), not from message text |
| Prompt injection | Model told to ignore SYSTEM overrides; code validates all tool outputs |
| Overpayment | Code-enforced cap: never pay > calculated owed |
| Double payment | Idempotency-Key on PaySwift + DB dedup |
| Data leakage | Agent only queries DB for the `rider_id` from the webhook |
