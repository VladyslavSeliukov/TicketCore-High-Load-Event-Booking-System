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

### 3. Idempotency

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

### 4. Distributed State Machine (The Booking Pattern)

**Context:** Unpaid tickets cannot be blocked forever. They must return to the pool if
the user drops off at the payment screen.  
**Decision:** Implemented a dual-layered garbage collection strategy using **Arq**.

* **Primary:** `release_unpaid_ticket` background task is deferred (delayed) upon ticket
  creation.
* **Fallback:** A `garbage_collector` cron job runs periodically, utilizing PostgreSQL's
  `UPDATE ... RETURNING` to sweep bulk 'hung' reservations and execute Redis `safe_incr`
  Lua scripts to restore inventory. This guarantees eventual consistency even if a
  specific worker pod dies mid-execution.

---

## 🏗 Architecture & Core Patterns

* **Concurrency & Race Condition Prevention (Overselling)**
    * **Pessimistic DB Locking:** Applied `SELECT ... FOR UPDATE SKIP LOCKED` to prevent
      simultaneous transactions from overselling the last available tickets.
    * **Distributed Locks:** Implemented Redlock algorithm via Redis for high-contention
      endpoints where DB locking is sub-optimal.
* **Eventual Consistency (Transactional Outbox Pattern)**
    * Solved the "Dual Write" problem. Ticket creation and external message logging (
      Outbox) are committed in a single atomic PostgreSQL transaction.
    * Background worker (`Arq`) asynchronously processes the Outbox table to guarantee "
      at-least-once" delivery for integrations (e.g., email notifications) without
      blocking the API response.
* **Fault Tolerance & Idempotency**
    * Custom middleware caching the `Idempotency-Key` header and request payload hash in
      Redis.
    * Safely handles network drops and client retries on payment transactions by
      returning cached responses, guaranteeing **zero double-spending**.
* **Read-Heavy Optimization**
    * Implemented Read-Aside caching via Redis for `GET /events` to offload PostgreSQL
      during extreme traffic spikes.

---

## 📊 Performance Testing (Locust)

Stress-tested simulating a "Flash Sale" event to validate data consistency and
transaction isolation under load.

### 🧪 Test Environment & Parameters

The test was executed locally

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
```

* **API Docs (Swagger):** `http://localhost/docs`
* **Run Tests:** `uv run pytest `

---

## 📬 Contact

**Vladyslav Seliukov** - Backend Python Engineer

* [GitHub Profile](https://github.com/VladyslavSeliukov)
* [LinkedIn Profile](https://www.linkedin.com/in/vladyslav-seliukov/)
* seliukovvladyslav@gmail.com