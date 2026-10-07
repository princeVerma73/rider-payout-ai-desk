# Tasks & Progress
## QuickDrop — Rider Payout Dispute Desk

Status legend: `[ ]` = todo · `[~]` = in progress · `[x]` = done

---

## Phase 1 — Setup & Infrastructure

- [ ] Create private GitHub repo
- [ ] Add `pratham-saraf` as collaborator
- [ ] Copy `docker-compose.yml` starter, keep `payswift` service intact
- [ ] Set up PostgreSQL service in `docker-compose.yml`
- [ ] Create `.env.example` with all required variables
- [ ] Add `GET /health` endpoint returning 200
- [ ] Write DB migrations (schema creation)
- [ ] Write CSV seeder for `riders`, `trips`, `payout_lines`
- [ ] Verify `docker compose up` starts cleanly

---

## Phase 2 — Core Agent

- [ ] Set up LLM provider (Groq / Gemini free tier)
- [ ] Implement `POST /messages` endpoint
- [ ] Implement message deduplication by `message_id`
- [ ] Implement conversation history storage (per `rider_id`)
- [ ] Build `get_trips` tool (query DB by rider + date)
- [ ] Build `get_payout_lines` tool (query DB by rider + date)
- [ ] Implement payout policy calculator:
  - [ ] Base fare: ₹25 + ₹6/km after first 2km
  - [ ] Surge multiplier applied to full fare
  - [ ] Rounding: nearest rupee (0.5 rounds up)
  - [ ] Daily incentive: ₹150 for ≥ 12 completed trips
  - [ ] Cancel penalty: ₹10 per rider-cancelled trip
  - [ ] 7-day dispute window check
- [ ] Build `initiate_payment` tool:
  - [ ] Auto-pay ≤ ₹200 via PaySwift (first payment of day)
  - [ ] Queue > ₹200 or repeat-day disputes for ops approval
  - [ ] Use `Idempotency-Key` header
- [ ] Build `escalate_to_ops` tool
- [ ] Implement agent logic for rider isolation (no cross-rider queries)
- [ ] Handle prompt injection safely (ignore SYSTEM overrides in text)

---

## Phase 3 — Trace & Ops API

- [ ] Implement step logging to `trace_steps` table
  - [ ] `message_in` steps
  - [ ] `tool_call` steps
  - [ ] `decision` steps
  - [ ] `reply` steps
  - [ ] `error` steps
- [ ] Implement `GET /trace/{rider_id}` returning ordered JSON list
- [ ] Implement `GET /ops/pending` returning approvals + escalations
- [ ] Implement `POST /ops/pending/{id}/approve` (trigger PaySwift)
- [ ] Implement `POST /ops/pending/{id}/reject`

---

## Phase 4 — Ops Dashboard (UI)

- [ ] Create `ops-ui/index.html` (or React app)
- [ ] Dashboard home: stats bar (pending approvals, escalations)
- [ ] Pending approvals table with Approve/Reject buttons
- [ ] Escalations list
- [ ] Rider conversation view with trace steps (color-coded by type)
- [ ] All conversations list

---

## Phase 5 — Evals

- [ ] Create `evals/run.py`
- [ ] Load `data/conversations.json`
- [ ] For each conversation: POST each rider turn to `/messages`
- [ ] Check `expected.payout` against PaySwift ledger (`GET /v1/payouts?rider_id=...`)
- [ ] Check `expected.approval` against `GET /ops/pending`
- [ ] Check `expected.escalation` against `GET /ops/pending`
- [ ] Check `expected.reply_mentions` are in the reply text
- [ ] Handle `expected.one_of` (any acceptable end state)
- [ ] Print formatted pass/fail report
- [ ] Ensure each conversation runs against a **fresh** system state

---

## Phase 6 — CI & Polish

- [ ] Add GitHub Actions workflow (`.github/workflows/ci.yml`)
  - [ ] Build images
  - [ ] `docker compose up -d`
  - [ ] Wait for `/health` 200
  - [ ] Run eval suite
  - [ ] Fail CI if evals fail
- [ ] Write `README.md` (max 1 page):
  - [ ] How to run (`docker compose up`)
  - [ ] Agent design (tools, what model decides vs code decides)
  - [ ] Assumptions made
  - [ ] Eval results
  - [ ] What was skipped
- [ ] Export AI session logs to `ai-logs/`
- [ ] Final check: no secrets committed

---

## Edge Cases to Handle

- [ ] Vague complaint → ask clarifying question
- [ ] Multi-issue complaint in one message (e.g., surge + double penalty)
- [ ] Rider disagrees with agent's answer → re-check once, then offer escalation
- [ ] Duplicate `message_id` (vendor retry) → return cached reply
- [ ] Rider impersonation (`"This is R005..."`) → ignore, serve only actual rider
- [ ] Dispute older than 7 days → politely decline
- [ ] Claim about `cancelled_by_customer` trips → explain no penalty earned/owed
- [ ] Prompt injection (`SYSTEM: ignore rules...`) → safe refusal, optionally escalate
- [ ] PaySwift rate limit (429) → retry, don't double-pay
- [ ] Amount claimed by rider exceeds what policy allows → pay only what's owed

---

## Known Constraints & Deadlines

- **Deadline**: Thursday 1 October, 2:30 PM IST
- **Language**: Python or Node.js
- **LLM**: Free tier sufficient (Groq / Gemini)
- **Submission**: New private repo, `pratham-saraf` as collaborator, reply to email with link
