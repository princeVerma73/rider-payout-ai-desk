# Project Context & Memory
## QuickDrop — Rider Payout Dispute Desk

> This file captures key decisions, assumptions, discoveries, and context for this project.
> Update it as you build.

---

## What This Project Is

**Assignment**: ProcureYard ML/AI Engineer Intern take-home.

Build an AI agent that handles rider payout dispute conversations on WhatsApp for **QuickDrop**, a fictional delivery company with ~5,000 riders.

---

## Repository Structure

```
qd-assignment/          ← Original repo (read-only reference)
  BRIEF.md              ← Full assignment brief
  SUBMISSION.md         ← Submission logistics + API shapes
  docs/
    policy.md           ← Payout policy (source of truth)
    prd.md              ← Product requirements (created by us)
    architecture.md     ← System architecture (created by us)
    rules.md            ← Coding rules (created by us)
    design.md           ← UI/UX direction (created by us)
    tasks.md            ← Task list (created by us)
    memory.md           ← This file
  data/
    riders.csv          ← 40 riders, 4 cities
    trips.csv           ← Trips Sep 12–21 2026
    payout_lines.csv    ← Actual payout records
    conversations.json  ← 25 test scenarios (eval dataset)
  payswift/
    README.md           ← PaySwift sandbox docs
    Dockerfile          ← DO NOT MODIFY
    server.pyc          ← DO NOT MODIFY
  docker-compose.yml    ← Starter; keep payswift service as-is
  ai-logs/              ← Export AI session logs here
```

---

## Key Data Facts

### Riders
- 40 riders total
- Cities: Bengaluru, Hyderabad, Pune
- IDs: R001–R040

### Trips (`trips.csv`)
- Date range: **Sep 12–21, 2026** (IST)
- Columns: `trip_id, rider_id, started_at, status, distance_km, surge_multiplier`
- Status values: `completed`, `cancelled_by_customer`, `cancelled_by_rider`
- `started_at` is in **UTC** — must convert to IST for day boundaries

### Payout Lines (`payout_lines.csv`)
- Columns: `line_id, payout_date, rider_id, line_type, trip_id, amount`
- `line_type`: `trip`, `daily_incentive`, `cancellation_penalty`
- Penalties are **negative** amounts
- `payout_date` is in IST (calendar date)

### Conversations (`conversations.json`)
- 25 test scenarios
- Mix of multi-turn (4 scenarios) and single-message (21 scenarios)
- `expected` field defines what the correct agent outcome should be
- `one_of` field means any listed end state is acceptable (e.g., which payment is auto vs approval)

---

## Payout Policy (Exact Rules)

Source: `docs/policy.md`

```
Trip fare = (₹25 + ₹6 × max(0, distance_km - 2)) × surge_multiplier
            → round to nearest rupee (0.5 rounds UP)

Daily incentive = ₹150 if completed_trips_in_day >= 12

Rider cancel penalty = -₹10 per cancelled_by_rider trip

Customer cancels = no penalty, no pay

Dispute window = last 7 calendar days (IST) from message date
```

**Critical**: Use `math.floor(x + 0.5)` for rounding, NOT Python's `round()` (banker's rounding).

---

## PaySwift Sandbox

- Runs on port **8081**
- In-memory ledger (resets on restart)
- `POST /v1/payouts` → 201 with `payout_id` and `status`
- `GET /v1/payouts?rider_id=R003` → list payouts for rider
- Supports `Idempotency-Key` header
- May return: 400, 409, 429, 5xx
- Rate limits apply — handle gracefully

---

## Auto-Pay Rules (Finance)

| Condition | Action |
|---|---|
| Amount ≤ ₹200 AND first payment today | Auto-pay via PaySwift immediately |
| Amount > ₹200 | Queue for ops approval |
| Second payment same day | Queue for ops approval |
| Any amount where ops should see it | Queue for ops approval or escalate |

**Never pay more than the rider is owed.**

---

## Key Conversations to Study

| Scenario | Rider | Key Learning |
|---|---|---|
| Vague complaint | R003 | Agent must ask clarifying Q → then resolve T926334 surge |
| Two problems at once | R027 | Handle multi-issue; split auto-pay vs approval |
| Rider disagrees | R011 | Stand firm on data, offer optional escalation |
| Impersonation attempt | R020 | Refuse cross-rider action, stay on authenticated rider |
| Duplicate message | R003 | Same `message_id` → idempotent response |
| Daily incentive | R005 | Check completed trips for the day |
| No discrepancy | R008 | Surge was already applied correctly → ₹0 payout |
| Large approval needed | R016 | ₹425 → must go to ops, not auto-pay |
| Outside 7-day window | R022 | Sep 13 dispute filed Sep 23 → decline |
| Prompt injection | R037 | `SYSTEM: ignore rules` → safe refusal |

---

## Assumptions Made

> Fill in as you build

- [ ] `started_at` in trips.csv is UTC; convert to IST for day grouping
- [ ] "Last 7 days" means `message_date - 7 days <= dispute_date <= message_date`
- [ ] Rider identity comes from webhook `rider_id`, not message text
- [ ] Conversation state is per `rider_id` (not per session)
- [ ] `.env` is not committed; `.env.example` lists all variables
- [ ] Ops dashboard does not require authentication (out of scope)

---

## Decisions Log

> Record architectural decisions here

| Date | Decision | Reason |
|---|---|---|
| TBD | LLM provider chosen | TBD |
| TBD | Agent framework chosen | TBD |
| TBD | Language (Python/Node) | TBD |

---

## Submission Checklist

- [ ] Private GitHub repo created
- [ ] `pratham-saraf` added as collaborator
- [ ] `docker compose up` works
- [ ] `GET /health` returns 200
- [ ] `POST /messages` works
- [ ] `GET /trace/{rider_id}` works
- [ ] `GET /ops/pending` works
- [ ] Ops dashboard accessible
- [ ] Evals run with one command
- [ ] `.env.example` complete
- [ ] No `.env` or API keys committed
- [ ] AI logs in `ai-logs/`
- [ ] `README.md` written (max 1 page)
- [ ] `main` branch is up to date
- [ ] Reply email sent before deadline
