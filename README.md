# 🎫 TicketCore: High-Load Event Booking API

A backend system built to solve specific distributed system challenges: Race Conditions,
Double Spending, and Data Consistency under heavy load.

---

## 🛠 Tech Stack

* **Backend:** Python 3.12, FastAPI, Pydantic V2
* **Database:** PostgreSQL 16 (Asyncpg, SQLAlchemy 2.0)
* **Caching & Locks:** Redis 7
* **Background Jobs:** Arq (Redis-based worker)
* **Infra:** Docker Compose, GitHub Actions (CI/CD pipelines for linting & testing)
* **Testing:** Pytest (Unit/Integration), Locust (Stress testing)

--- 

## 🧠 Deep Dive: Engineering Challenges & Architecture Decision Records

### 1. The Paginated Cache Invalidation Problem

**Context:** Caching `GET /events` with an offset/limit is trivial until an event is
updated. Deleting all paginated cache keys using Redis `KEYS *` is an $O(N)$ operation
that blocks the Redis single thread, causing cascading timeouts in production.  
**Decision:** Implemented **O(1) Cache Invalidation using Versioned Keys**.

* The `CachedEventRepository` appends a global `list_version` integer to all paginated
  Redis keys.
* On any `update` or `delete` operation, the system simply runs an atomic `INCR` on the
  global version key.
* All old paginated caches instantly become logically orphaned (and naturally expire via
  TTL), guaranteeing zero dirty reads with $O(1)$ complexity.

### 2. Flash Sale Bottlenecks & Atomic Inventory (Race Conditions)

**Context:** During a flash sale (e.g., 10,000 users competing for 100 tickets), relying
solely on PostgreSQL `SELECT ... FOR UPDATE` causes massive lock contention and
connection pool exhaustion.  
**Decision:** Implemented **Redis Lua-Script Gatekeeping**.

* Inventory decrements are executed atomically inside Redis via custom Lua scripts
  *before* the request is allowed to reach PostgreSQL.
* This acts as a shock absorber: if Redis returns `0` available tickets, the API
  instantly returns a `TicketsSoldOutError` without ever opening a database connection,
  preserving DB CPU for actual successful transactions.

### 3. Network Instability & Double Spending (Idempotency)

**Context:** In unstable mobile networks, clients often retry `POST /tickets/`
requests (Payment/Booking). Without idempotency, this results in double-charging the
user.  
**Decision:** Created a custom `@idempotent` FastAPI decorator backed by Redis.

* Generates a deterministic `SHA-256` hash of the request payload combined with the
  client-provided `Idempotency-Key` header.
* Uses Redis distributed locks (`NX` flag) to prevent concurrent execution of the same
  request.
* Returns the cached JSON response of the original successful request, ensuring
  side-effects (DB commits, background jobs) occur strictly once.

### 4. The Dual Write Problem & Hung Reservations

**Context:** The system utilizes Redis for fast inventory locking and PostgreSQL for
persistent booking. If the Postgres transaction rolls back (e.g., due to a network
drop), or if a user abandons the payment screen, ghost locks remain in Redis,
permanently blocking inventory.  
**Decision:** Implemented a **Dual-Layered Garbage Collection Strategy** via Arq.

* **Primary:** A `release_unpaid_ticket` background task is deferred upon ticket
  creation to clear unpaid DB reservations.
* **Reconciliation (Redis GC):** A cron job sweeps the `active_reservations_hash` in
  Redis. Utilizing a 60-second Grace Period to prevent race conditions with in-flight
  transactions, it compares Redis locks against PostgreSQL states. If a lock has no
  corresponding committed DB record, the system idempotently restores the Redis
  inventory, guaranteeing **Eventual Consistency**.

### 5. Concurrency & Race Condition Prevention (Overselling)

**Context:** Even with Redis acting as a gatekeeper, concurrent database transactions
can theoretically overwrite each other's state, leading to oversold events.  
**Decision:** Strict **Pessimistic Locking**.

* Applied `SELECT ... FOR UPDATE SKIP LOCKED` inside PostgreSQL payment and booking
  flows.
* This ensures complete row-level isolation during concurrent transaction attempts,
  preventing any possibility of overselling the last available tickets at the
  persistence layer.

### 6. Read-Heavy Optimization

**Context:** Event catalogs experience massive spikes in read traffic, threatening to
overwhelm the relational database.  
**Decision:** **Read-Aside Caching Architecture**.

* Implemented caching via Redis for all heavily accessed endpoints (`GET /events`).
* Offloads over 90% of read operations from PostgreSQL during traffic spikes, keeping
  the database available for critical write (booking/payment) operations.

---

## 📊 Performance Testing (Locust)

Stress-tested simulating a "Flash Sale" event to validate data consistency and
transaction isolation under load.

### 🧪 Test Environment & Parameters

The test was executed locally:

* **Hardware:** MacBook Air M1
* **Application Server:** Uvicorn running `8` workers (`--workers 8`)
* **Load Profile:**
    * **Concurrent Users:** 1,000
    * **Spawn Rate:** 100 users / second
    * **Task Wait Time:** 0.1s - 0.5s
    * **Traffic Mix:** Heavy read traffic on `GET /events` (Cache testing) mixed with
      concurrent `POST /tickets` (Transaction/Lock testing).

### 📈 Benchmark Results

| Metric                   | Result     | 
|:-------------------------|:-----------|
| **Peak Throughput**      | ~2,500 RPS | 
| **Average Throughput**   | ~1,500 RPS | 
| **Error Rate**           | 0.00%      | 
| **Overselling Index**    | 0          | 
| **Idempotency Failures** | 0          | 

*(Results of the Locust test runs are available in the `/load_tests` directory).*

---

## 💻 Getting Started

### Run Locally

```bash
git clone https://github.com/VladyslavSeliukov/TicketCore-High-Load-Event-Booking-System.git
cd ticket-core

# Start infrastructure and app
docker compose up --build -d

# Run DB Migrations  
docker compose exec backend alembic upgrade head