# Design — UI/UX Direction
## QuickDrop — Ops Dashboard

---

## 1. Purpose

A simple internal ops page for QuickDrop executives to:
- **Monitor** ongoing rider conversations
- **Inspect** what the agent did (tool calls, decisions, replies)
- **Approve or reject** pending payments
- **View** escalated cases needing human judgment

This is an **internal ops tool** — prioritize clarity and function over visual flair.

---

## 2. Pages / Views

### 2.1 Dashboard Home (`/`)

| Section | Content |
|---|---|
| **Stats Bar** | Total pending approvals, Total escalations, Conversations today |
| **Pending Approvals** | List of items from `GET /ops/pending` with type=`approval` |
| **Escalations** | List of items with type=`escalation` |

### 2.2 Pending Approvals Table

Columns:
- Rider ID + Name
- Amount (₹)
- Reason (summary)
- Created At
- **Approve** button
- **Reject** button

On **Approve**:
- Call your backend endpoint (e.g., `POST /ops/pending/{id}/approve`)
- Show success toast, remove from list

On **Reject**:
- Prompt for optional rejection note
- Call `POST /ops/pending/{id}/reject`
- Show confirmation

### 2.3 Rider Conversation View (`/rider/{rider_id}`)

Shows the full conversation + agent trace:

```
─────────────────────────────────────────────
[09:00] RIDER: bhai payout galat aaya hai
─────────────────────────────────────────────
         AGENT TOOL: get_trips(rider_id=R003, date=2026-09-20)
         AGENT TOOL: get_payout_lines(rider_id=R003, date=2026-09-20)
         AGENT DECISION: surge missing on T926334, owed ₹25
         AGENT TOOL: initiate_payment(rider_id=R003, amount=25)
─────────────────────────────────────────────
[09:02] AGENT: ₹25 ka payment PaySwift pe process ho gaya hai.
─────────────────────────────────────────────
```

Trace step types and colors:
- `message_in` → Blue (rider message)
- `tool_call` → Gray (agent action)
- `decision` → Orange (agent reasoning)
- `reply` → Green (agent reply to rider)
- `error` → Red (something went wrong)

### 2.4 All Conversations List (`/conversations`)

Table:
- Rider ID
- Last message preview
- Last activity time
- Status badge (resolved / pending / escalated)
- Click to open Rider Conversation View

---

## 3. UI Stack

- **HTML + Vanilla CSS + Vanilla JS** (no framework required — keep it simple)
- OR minimal React/Vue if preferred
- Served by your app at `/` or a separate port
- No external UI libraries required, but Bootstrap or Pico.css is fine

---

## 4. Key Design Principles

| Principle | Implementation |
|---|---|
| **Clarity** | Every pending item shows all info needed to approve/reject without clicking through |
| **Safety** | Approval requires a deliberate click (no accidental approvals) |
| **Traceability** | Every decision the agent made is visible, in order |
| **Responsiveness** | Must work on a laptop screen (1366×768 minimum) |
| **No auth required** | This is a take-home; authentication is out of scope |

---

## 5. API Endpoints the UI Needs

| Action | Endpoint |
|---|---|
| Load pending items | `GET /ops/pending` |
| Load rider trace | `GET /trace/{rider_id}` |
| Approve item | `POST /ops/pending/{id}/approve` *(you design this)* |
| Reject item | `POST /ops/pending/{id}/reject` *(you design this)* |
| List all conversations | `GET /conversations` *(optional, you design this)* |

---

## 6. Mockup — Ops Dashboard

```
┌─────────────────────────────────────────────────────┐
│  QuickDrop Ops Dashboard                            │
│  ─────────────────────────────────────────────────  │
│  [ 3 Pending Approvals ]  [ 2 Escalations ]         │
│                                                     │
│  PENDING APPROVALS                                  │
│  ┌──────────┬──────┬─────────────────┬─────────────┐│
│  │ Rider    │ ₹    │ Reason          │ Actions     ││
│  ├──────────┼──────┼─────────────────┼─────────────┤│
│  │ R016     │ 425  │ 5 trips missing │ ✓ Approve   ││
│  │          │      │ 19 Sep          │ ✗ Reject    ││
│  ├──────────┼──────┼─────────────────┼─────────────┤│
│  │ R034     │ 249  │ 3 trips missing │ ✓ Approve   ││
│  │          │      │ 19 Sep          │ ✗ Reject    ││
│  └──────────┴──────┴─────────────────┴─────────────┘│
│                                                     │
│  ESCALATIONS                                        │
│  ┌──────────┬──────────────────────────────────────┐│
│  │ Rider    │ Reason                               ││
│  ├──────────┼──────────────────────────────────────┤│
│  │ R036     │ Rider disputes distance record        ││
│  │ R028     │ Cancel penalty — accident claim       ││
│  └──────────┴──────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```
