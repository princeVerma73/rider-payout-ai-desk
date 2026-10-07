# Product Requirements Document (PRD)
## QuickDrop — Rider Payout Dispute Desk

---

## 1. Problem Statement

QuickDrop is a fictional delivery company with ~5,000 riders. Every morning, ops executives handle hundreds of WhatsApp complaints from riders about incorrect payouts:

> *"bhai kal ka payout 120 kam aaya"*
> *"order T88213 ka surge nahi mila"*

Currently:
- 3 ops executives manually check every trip, recalculate payout, and compare with actual payment
- ~2 days per reply turnaround
- Riders are angry, some have quit

---

## 2. Goals

Build an AI agent that:
1. Handles rider payout dispute conversations **end to end** via WhatsApp
2. Verifies complaints by checking trip data and payouts against policy
3. Pays riders automatically for valid small disputes (≤ ₹200)
4. Routes larger or repeat disputes to ops for approval
5. Provides a **simple ops dashboard** to review, approve, or reject pending items
6. Is fully **dockerized** and CI-ready

---

## 3. Stakeholders

| Stakeholder | Role |
|---|---|
| Meera (Head of Ops) | Primary requester; needs trust in the system before money moves |
| Finance | Defined auto-pay rules; concerned about overpayments |
| Ops Executives | Will use the approval dashboard |
| Riders (~5,000) | End users sending WhatsApp disputes |

---

## 4. Functional Requirements

### 4.1 Core Agent

| ID | Requirement |
|---|---|
| F1 | Accept POST `/messages` with `message_id`, `rider_id`, `text`, `received_at` |
| F2 | Return `{ "reply": "..." }` within ~10 seconds (vendor timeout) |
| F3 | Handle multi-turn conversations (riders send multiple messages) |
| F4 | Deduplicate messages by `message_id` (vendor may retry) |
| F5 | Handle complaints about: missing surge, wrong base pay, double penalties, missing incentives |
| F6 | Verify disputes using actual trip + payout data |
| F7 | Compute correct payout using the policy formula |
| F8 | Only serve data for the authenticated rider (no cross-rider access) |

### 4.2 Payment Rules

| ID | Requirement |
|---|---|
| P1 | Auto-pay valid disputes ≤ ₹200 via PaySwift |
| P2 | Auto-pay limited to once per rider per day |
| P3 | Disputes > ₹200 or repeat same-day → queue for ops approval |
| P4 | Never pay more than the rider is actually owed |
| P5 | Reconcile against PaySwift, not internal DB |

### 4.3 Ops API

| Endpoint | Description |
|---|---|
| `GET /trace/{rider_id}` | All agent actions for a rider, in order |
| `GET /ops/pending` | Items waiting for ops: approvals + escalations |

### 4.4 Ops Dashboard (UI)

- View all rider conversations
- See what the agent did (tool calls, decisions, replies)
- Approve or reject pending payments
- View escalated conversations

### 4.5 Evals

- Single command: `python evals/run.py http://localhost:8000`
- Runs all test conversations from `data/conversations.json`
- Prints a pass/fail report
- Uses only the public API (`/messages`, PaySwift)

---

## 5. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Response Time | Reply within ~10s (vendor retry window) |
| Idempotency | Duplicate `message_id` must not double-process |
| Security | Agent must not accept rider impersonation attempts |
| Prompt Injection | Agent must ignore `SYSTEM:` override attempts in rider messages |
| Auditability | Every agent step logged in `/trace/{rider_id}` |
| Infrastructure | `docker compose up` starts all services |
| CI | GitHub Actions on every push |

---

## 6. Out of Scope

- Handling complaints older than 7 days
- Disputes about `cancelled_by_customer` trips (no penalty earned)
- Distance record corrections (escalate to ops)
- Changing rider account information

---

## 7. Success Metrics

- Eval pass rate on `conversations.json`
- No overpayments (amount paid ≤ amount owed)
- Idempotency: duplicate messages produce identical results
- Prompt injection attempts result in 0 payout, optional escalation
