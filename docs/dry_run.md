# Dry Run Documentation

> This file documents every major development task in the QuickDrop Rider Payout Dispute Desk project.
> Each entry traces HOW the code works and WHY each decision was made.

---

## Dry Run 1 - FastAPI Backend with SQLAlchemy Models, Database Seeding & Docker Configuration

### File/Folder Restructuring (Post-Commit Refactor)

The initial commit created `app/db.py` and `app/seed.py` as flat files inside `app/`. After the commit, these were **refactored into a proper package**:

| Original Path (committed) | New Path (current) | Reason |
|---|---|---|
| `app/db.py` | `app/db/session.py` + `app/db/models.py` | Split monolithic db file into separation-of-concerns modules |
| `app/seed.py` | `app/db/seed.py` | Moved seeding logic into the `db/` sub-package |

An `app/db/` directory was created, consolidating all database-related code under one sub-package. This is standard practice for scalable FastAPI projects.

---

### Section 1 of 3 — `app/db/session.py` & `app/db/models.py`

---

#### File 1: `app/db/session.py`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Docker container ke andar postgres se connect karne ke liye URL
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@postgres:5432/quickdrop")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### Dry Run & Explanation — `session.py`

**Purpose:** This file is the *single source of truth* for the database connection. Every other module that needs to talk to Postgres imports from here.

---

**Line-by-Line Walkthrough:**

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
```
- `os` is imported to read environment variables at runtime.
- `create_engine` — SQLAlchemy function that creates a connection pool to the database.
- `sessionmaker` — A factory that produces `Session` objects (used to run queries).
- `declarative_base` — Returns a base class from which all ORM model classes inherit.

```python
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@postgres:5432/quickdrop")
```
- **HOW:** `os.environ.get()` reads the `DATABASE_URL` environment variable at startup. If none is set, falls back to the default string pointing to `postgres` (Docker service name).
- **WHY:** Hardcoding credentials is a security risk. Using env vars allows the same codebase to point to different databases without code changes. The default hostname `postgres` only resolves inside Docker's internal network.

```python
engine = create_engine(DATABASE_URL)
```
- **HOW:** Creates a single `Engine` object. SQLAlchemy manages a *connection pool* behind this — it re-uses open connections rather than opening a new one per query.
- **WHY:** One engine per application is standard. It is module-level (created once on import), making it efficient and shared across all requests.

```python
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```
- **HOW:** `sessionmaker` returns a *class* (not an instance). Each call to `SessionLocal()` produces a fresh `Session`.
- `autocommit=False` — Changes are not sent to the DB until `.commit()` is explicitly called. Full transaction control.
- `autoflush=False` — SQLAlchemy won't auto-send pending changes to the DB before a query.
- **WHY:** Explicit commit/rollback control is critical in a financial system. We must never accidentally persist a partial payout update.

```python
Base = declarative_base()
```
- **HOW:** Creates the `Base` class. All ORM models in `models.py` inherit from this.
- **WHY:** Centralizing `Base` here means `models.py` imports it from one place — no circular imports, no duplication.

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```
- **HOW:** FastAPI **dependency generator** using `yield`. FastAPI injects the `db` session into route handlers and resumes the generator (running `db.close()`) after the response is sent.
- **WHY:** The `try/finally` guarantees the session is *always* closed even if the route raises an exception — prevents connection leaks.

---

#### File 2: `app/db/models.py`

```python
from sqlalchemy import Column, String, Float, Integer, Text
from app.db.session import Base, engine

class Rider(Base):
    __tablename__ = "riders"
    rider_id = Column(String, primary_key=True)
    name = Column(String)
    phone = Column(String)
    city = Column(String)

class Trip(Base):
    __tablename__ = "trips"
    trip_id = Column(String, primary_key=True)
    rider_id = Column(String)
    date = Column(String)
    distance_km = Column(Float)
    fare = Column(Float)
    status = Column(String)

class PayoutLine(Base):
    __tablename__ = "payout_lines"
    line_id = Column(String, primary_key=True)
    rider_id = Column(String)
    trip_id = Column(String, nullable=True)
    amount = Column(Float)
    category = Column(String)
    date = Column(String)

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String, unique=True)
    rider_id = Column(String)
    sender = Column(String)  # 'rider' or 'agent'
    text = Column(Text)
    created_at = Column(String)

class OpsDispute(Base):
    __tablename__ = "ops_disputes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    rider_id = Column(String)
    trip_id = Column(String, nullable=True)
    amount = Column(Float)
    reason = Column(Text)
    status = Column(String, default="PENDING")
    created_at = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)
```

#### Dry Run & Explanation — `models.py`

**Purpose:** Defines the database schema as Python classes. SQLAlchemy translates these into `CREATE TABLE` SQL statements.

---

**`class Rider(Base)` — Table: `riders`**

| Column | Type | Role |
|---|---|---|
| `rider_id` | `String` (PK) | Unique identifier from CSV (e.g., `R003`) |
| `name` | `String` | Display name |
| `phone` | `String` | WhatsApp phone used to identify the rider |
| `city` | `String` | Rider's operating city |

- **WHY `rider_id` as PK:** The source data already uses string IDs. Using the natural key avoids a surrogate int ID and makes lookups direct and fast.
- **WHY store phone:** The messaging vendor identifies riders by phone number. Storing phone enables reverse lookup from raw phone to rider record.

---

**`class Trip(Base)` — Table: `trips`**

| Column | Type | Role |
|---|---|---|
| `trip_id` | `String` (PK) | Unique trip identifier (e.g., `T88213`) |
| `rider_id` | `String` | Soft FK link to `riders` |
| `date` | `String` | Date of the trip |
| `distance_km` | `Float` | Distance traveled |
| `fare` | `Float` | Fare earned |
| `status` | `String` | Trip completion status |

- **WHY soft FK (no `ForeignKey()`):** Enforcing strict FK constraints would cause seed failures if CSV rows arrive out of order or contain orphan records.

---

**`class PayoutLine(Base)` — Table: `payout_lines`**

| Column | Type | Role |
|---|---|---|
| `line_id` | `String` (PK) | Unique payout line ID |
| `rider_id` | `String` | Rider who received this payout |
| `trip_id` | `String`, nullable | Optional link to a specific trip |
| `amount` | `Float` | Amount paid out |
| `category` | `String` | Type (base fare, surge, bonus, etc.) |
| `date` | `String` | Date of the payout |

- **WHY `trip_id` is nullable:** Not all payout lines are trip-specific (e.g., weekly bonuses, penalties). `nullable=True` allows standalone payout lines.
- **Data flow:** When a rider disputes "T88213 ka surge nahi mila", the agent queries `payout_lines` by `rider_id + trip_id + category='surge'` to verify.

---

**`class ConversationMessage(Base)` — Table: `conversation_messages`**

| Column | Type | Role |
|---|---|---|
| `id` | `Integer` (PK, auto) | Internal auto-increment row ID |
| `message_id` | `String`, unique | `wamid` from vendor — idempotency guard |
| `rider_id` | `String` | Which rider this message belongs to |
| `sender` | `String` | `'rider'` or `'agent'` |
| `text` | `Text` | Full message body |
| `created_at` | `String` | Timestamp from vendor payload |

- **WHY `message_id` is `unique`:** The vendor re-sends if no 2xx within ~10s. The `unique` constraint prevents duplicate rows on retries — this is the **idempotency guard**.
- **WHY `Text` for `text`:** Rider messages are informal and unbounded. `Text` won't truncate anything (unlike `VARCHAR`).
- **WHY store agent messages too:** `GET /trace/{rider_id}` must return the full back-and-forth. Storing both sides in one table makes the timeline query trivial.

---

**`class OpsDispute(Base)` — Table: `ops_disputes`**

| Column | Type | Role |
|---|---|---|
| `id` | `Integer` (PK, auto) | Internal ID |
| `rider_id` | `String` | Rider involved |
| `trip_id` | `String`, nullable | The specific trip (if applicable) |
| `amount` | `Float` | Disputed/requested payout amount |
| `reason` | `Text` | Agent's escalation explanation |
| `status` | `String`, default `PENDING` | `PENDING`, `APPROVED`, or `REJECTED` |
| `created_at` | `String` | When the dispute was raised |

- **WHY this table exists:** Finance rules say payouts over ₹200 or repeat disputes need ops approval. The agent inserts a row here and waits. `GET /ops/pending` reads from this table.
- **WHY `default="PENDING"`:** Every new dispute starts pending. The ops team changes it to `APPROVED` or `REJECTED`. Simple, auditable state machine.

---

**`def init_db()`:**
```python
def init_db():
    Base.metadata.create_all(bind=engine)
```
- **HOW:** `create_all()` issues `CREATE TABLE IF NOT EXISTS` for every class inheriting from `Base`.
- **WHY a function:** Calling this at import time would crash if Postgres isn't ready. Wrapping it lets `seed.py` call it only at the right moment (after app startup).

---

### Section 2 of 3 — `app/db/seed.py` & `app/main.py`

---

#### File 3: `app/db/seed.py`

```python
import os
import pandas as pd
from app.db.session import SessionLocal
from app.db.models import init_db, Rider, Trip, PayoutLine

def seed_database():
    # Pehle tables create karo agar nahi bani hain toh
    init_db()
    db = SessionLocal()

    # Agar data pehle se hai, toh wapas seed mat karo
    if db.query(Rider).first():
        print("Database already seeded. Skipping.")
        db.close()
        return

    # Data folder ka sahi path dhoondhna
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(base_dir, "data")

    # 1. Seed Riders
    riders_path = os.path.join(data_dir, "riders.csv")
    if os.path.exists(riders_path):
        df_riders = pd.read_csv(riders_path)
        df_riders.drop_duplicates(subset=['rider_id'], inplace=True)  # ADDED FIX
        for _, row in df_riders.iterrows():
            db.merge(Rider(
                rider_id=str(row.get("rider_id")),
                name=str(row.get("name", "")),
                phone=str(row.get("phone", "")),
                city=str(row.get("city", ""))
            ))

    # 2. Seed Trips
    trips_path = os.path.join(data_dir, "trips.csv")
    if os.path.exists(trips_path):
        df_trips = pd.read_csv(trips_path)
        df_trips.drop_duplicates(subset=['trip_id'], inplace=True)  # ADDED FIX
        for _, row in df_trips.iterrows():
            db.merge(Trip(
                trip_id=str(row.get("trip_id")),
                rider_id=str(row.get("rider_id")),
                date=str(row.get("date", "")),
                distance_km=float(row.get("distance_km", 0.0)),
                fare=float(row.get("fare", 0.0)),
                status=str(row.get("status", ""))
            ))

    # 3. Seed Payout Lines
    payout_path = os.path.join(data_dir, "payout_lines.csv")
    if os.path.exists(payout_path):
        df_payout = pd.read_csv(payout_path)
        df_payout.drop_duplicates(subset=['line_id'], inplace=True)  # ADDED FIX
        for _, row in df_payout.iterrows():
            db.merge(PayoutLine(
                line_id=str(row.get("line_id")),
                rider_id=str(row.get("rider_id")),
                trip_id=str(row.get("trip_id")) if pd.notna(row.get("trip_id")) else None,
                amount=float(row.get("amount", 0.0)),
                category=str(row.get("category", "")),
                date=str(row.get("date", ""))
            ))

    # Saara data save (commit) karo aur connection close karo
    db.commit()
    db.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_database()
```

#### Dry Run & Explanation — `seed.py`

**Purpose:** Reads real CSV data from `data/` and loads it into Postgres on startup. Idempotent — safe to call multiple times.

---

**Data Flow:**
```
App Startup
    -> seed_database()
        -> init_db()              [creates tables if not exist]
        -> check if Rider rows exist -> skip if yes
        -> read riders.csv  -> deduplicate -> db.merge() each row
        -> read trips.csv   -> deduplicate -> db.merge() each row
        -> read payout_lines.csv -> deduplicate -> db.merge() each row
        -> db.commit()            [write all to Postgres atomically]
        -> db.close()
```

---

**Line-by-Line Walkthrough:**

```python
from app.db.session import SessionLocal
from app.db.models import init_db, Rider, Trip, PayoutLine
```
- Only the three seeding-relevant models are imported. `ConversationMessage` and `OpsDispute` start empty — no seed data for them.

```python
    init_db()
    db = SessionLocal()
```
- **`init_db()` first:** Ensures all tables exist *before* inserting rows. If tables don't exist, every `db.merge()` would throw an error.

```python
    if db.query(Rider).first():
        print("Database already seeded. Skipping.")
        db.close()
        return
```
- **HOW:** Runs `SELECT * FROM riders LIMIT 1`. Returns immediately if any row exists.
- **WHY — Idempotency Guard:** Docker may restart the app container on crashes. Without this check, every restart would try to re-insert thousands of CSV rows, causing `UNIQUE constraint` violations.

```python
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(base_dir, "data")
```
- **HOW the path resolves inside Docker:**
  - `__file__` = `/app/app/db/seed.py`
  - Three `dirname()` calls: `db/` -> `app/` -> `/app` (project root)
  - Final path: `/app/data`
- **WHY three levels:** The file is 3 levels deep (`app/db/seed.py`). The original `app/seed.py` used only 2. Updated as part of the refactor.

```python
        df_riders.drop_duplicates(subset=['rider_id'], inplace=True)  # ADDED FIX
```
- **WHY:** The raw CSV from ops may contain duplicate exports. If the same `rider_id` appears twice in one batch, merging two objects with identical PKs causes unexpected behavior on commit. This fix removes duplicates *before* they reach the DB.

```python
        db.merge(Rider(...))
```
- **HOW:** SQLAlchemy's upsert. If a row with that PK exists → UPDATE. If not → INSERT. Makes the seed fully re-runnable.
- **`str(row.get("rider_id"))`:** Explicit `str()` cast ensures Pandas numeric inference doesn't cause type mismatches with the `String` PK column.

```python
            trip_id=str(row.get("trip_id")) if pd.notna(row.get("trip_id")) else None,
```
- **WHY:** Some payout lines have no trip (bonuses, deductions). The CSV stores these as `NaN`. Without this guard, `str(NaN)` would store the literal string `"nan"` — a data corruption bug. `pd.notna()` detects valid values.

```python
    db.commit()
    db.close()
```
- Single commit for the entire load — orders of magnitude faster than per-row commits, and ensures atomicity (all-or-nothing).

```python
if __name__ == "__main__":
    seed_database()
```
- Allows `python -m app.db.seed` for manual DB population during development without starting the full FastAPI server.

---

#### File 4: `app/main.py`

```python
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
```

#### Dry Run & Explanation — `main.py`

**Purpose:** The application entry point. Defines the FastAPI app and all HTTP routes. Wires the startup lifecycle to trigger DB seeding.

---

**Startup Hook:**

```python
@app.on_event("startup")
async def startup_event():
    seed_database()
```
- **HOW:** FastAPI calls all `startup` event handlers once, before the server begins accepting requests.
- **WHY here, not at module level:** If `seed_database()` were called at import time, it would attempt a Postgres connection immediately — before Docker's healthcheck guarantees Postgres is ready. The startup event fires *after* Uvicorn is initialized.
- **WHY sync inside async:** `seed_database()` uses synchronous SQLAlchemy (blocking I/O). Calling blocking code inside `async` is acceptable here because `startup` runs *once* before any concurrent requests exist.

---

**Request Model:**

```python
class MessageRequest(BaseModel):
    message_id: str
    rider_id: str
    text: str
    received_at: str
```
- **HOW:** Pydantic's `BaseModel` parses and validates the incoming JSON body. Missing fields or wrong types → automatic `422 Unprocessable Entity` before the route handler runs.
- **WHY match the spec exactly:** The BRIEF defines the exact payload. The model mirrors this contract precisely.
- **WHY `received_at` as `str`:** ISO 8601 timestamps with timezone offsets need careful parsing. Keeping it as `str` lets the agent layer handle it with full control.

---

**Routes:**

```python
@app.get("/health")
async def health_check():
    return {"status": "ok"}
```
- Standard liveness check. Docker Compose and load balancers ping this to verify the service is alive.

```python
@app.post("/messages")
async def receive_message(msg: MessageRequest):
    return {"reply": "Agent is under construction"}
```
- The core endpoint from the BRIEF. Currently a **placeholder stub**. The agent logic will replace the return value in a future task.
- **HOW data flows:** Vendor POSTs rider message -> FastAPI validates against `MessageRequest` -> handler receives clean Python object -> (future) passes to agent -> returns `{"reply": "..."}`.

```python
@app.get("/trace/{rider_id}")
async def get_trace(rider_id: str):
    return []
```
- Returns full conversation history for a rider. `{rider_id}` is a **path parameter** FastAPI extracts automatically. Will query `conversation_messages` filtered by `rider_id` in a future task.

```python
@app.get("/ops/pending")
async def get_ops_pending():
    return []
```
- Returns disputes waiting for ops approval. Will query `ops_disputes WHERE status = 'PENDING'` in a future task.

---

### Section 3 of 3 — `Dockerfile` & `docker-compose.yml`

---

#### File 5: `Dockerfile` (root)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Dry Run & Explanation — `Dockerfile`

**Purpose:** Defines how to build the Docker image for the FastAPI app.

---

**Line-by-Line:**

```dockerfile
FROM python:3.11-slim
```
- `slim` is a stripped-down Debian image (~50–70MB vs ~900MB full). Python 3.11 chosen for stability and performance.

```dockerfile
WORKDIR /app
```
- Sets `/app` as the working directory. All subsequent instructions are relative to this path.

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
- **WHY copy `requirements.txt` first:** Docker builds images in layers. If `requirements.txt` hasn't changed, Docker reuses the cached pip-install layer — rebuilds after code changes are **much faster** (no re-downloading packages).
- `--no-cache-dir`: Prevents pip from storing a download cache in the image layer (keeps image smaller).

```dockerfile
COPY . .
```
- Copies all project files into `/app` (including `app/`, `data/`, etc.). `venv/` and `__pycache__/` are excluded via `.gitignore`.

```dockerfile
EXPOSE 8000
```
- Documents the container listens on port 8000. Informational only — actual port publishing is in `docker-compose.yml`.

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
- `app.main:app` — find the Python module `app.main`, and within it, the object named `app`.
- `--host 0.0.0.0` — Binds to all network interfaces. Without this, the server would only be reachable from inside the container itself.
- **WHY `CMD` not `ENTRYPOINT`:** `CMD` can be overridden at `docker run` time (e.g., for `bash` debugging). More flexible.

---

#### File 6: `docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: quickdrop
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d quickdrop"]
      interval: 5s
      timeout: 5s
      retries: 5

  payswift:
    build: ./payswift
    ports:
      - "8081:8081"

  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/quickdrop
      - PAYSWIFT_BASE_URL=http://payswift:8081
      - GROQ_API_KEY=${GROQ_API_KEY}
```

#### Dry Run & Explanation — `docker-compose.yml`

**Purpose:** Orchestrates all three services as a single unit. `docker compose up` starts them all with correct networking and startup ordering.

---

**Service: `postgres`**

- `image: postgres:15` — Official Postgres 15 image, no custom build needed.
- `environment` — `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` are Postgres init vars. On first start, creates the `quickdrop` database. These match the credentials in `session.py`'s `DATABASE_URL`.
- `ports: "5432:5432"` — Exposes Postgres to the host for debugging. Would be removed in production.
- **`healthcheck`:**
  - Runs `pg_isready` every 5 seconds.
  - **WHY critical:** Without a healthcheck, `depends_on` only waits for the *container to start*, not for Postgres to be *ready to accept queries*. The app would crash on startup trying to connect to an initializing Postgres.

---

**Service: `payswift`**

- `build: ./payswift` — Builds from `payswift/Dockerfile`, which runs the pre-compiled `server.pyc` payment sandbox.
- **WHY a separate service:** The BRIEF says to reconcile against PaySwift, not the internal DB. Running it as a sidecar simulates a real payment provider integration.
- Inside Docker's network, the `app` calls it as `http://payswift:8081` (Docker DNS resolves service names automatically).

---

**Service: `app`**

- `build: .` — Builds using the root `Dockerfile`.
- **`depends_on: postgres: condition: service_healthy`** — The app container will NOT start until Postgres passes its healthcheck. This is the correct Docker Compose v3+ way to enforce startup ordering (the old `depends_on` without `condition` only waited for container start, not readiness).
- `DATABASE_URL` — Passed as env var. `session.py` picks it up via `os.environ.get()`. The hostname `postgres` is Docker's service name — resolves to the Postgres container's IP automatically.
- `PAYSWIFT_BASE_URL=http://payswift:8081` — Base URL for HTTP calls to the PaySwift sandbox. Agent code will use this for payout initiation.
- `GROQ_API_KEY=${GROQ_API_KEY}` — Substituted from host machine's `.env` file or shell env. The key is never hardcoded.

---

### Summary Table — All Files in Dry Run 1

| File | Role | Key Design Decision |
|---|---|---|
| `app/db/session.py` | DB connection factory | Single engine, env-var URL, `get_db()` generator for safe session lifecycle |
| `app/db/models.py` | ORM schema definitions | 5 tables covering full data domain; idempotency via unique `message_id`; soft FKs for seeding safety |
| `app/db/seed.py` | CSV -> Postgres data loader | Idempotency check, `drop_duplicates` fix, `db.merge()` upsert, single-transaction commit |
| `app/main.py` | FastAPI entrypoint & route stubs | Startup hook for seeding, Pydantic validation, placeholder stubs for future agent logic |
| `Dockerfile` | App container build recipe | Layer-caching via split COPY, `0.0.0.0` bind, `slim` base image |
| `docker-compose.yml` | Multi-service orchestration | `service_healthy` condition for safe startup ordering, Docker DNS for inter-service calls |
