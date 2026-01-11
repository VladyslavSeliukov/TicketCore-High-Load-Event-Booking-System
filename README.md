# 🎫 TicketCore: High-Consistency Event Booking API

**A production-grade ticketing system engineered to handle high concurrency, prevent race conditions (overselling), and ensure eventual consistency.**

---

## 🚀 Project Overview

TicketCore is not just a CRUD application. It is a simulation of a high-load environment (like Ticketmaster or flash sales) designed to solve specific distributed system challenges: **Race Conditions, Double Spending, and Data Consistency.**

The goal was to move beyond "Junior" implementation patterns and apply industry-standard architectural solutions for reliability and scale.

### Key Engineering Features

* **Concurrency Safe:** Prevents ticket overselling during flash sales using pessimistic locking (`SELECT ... FOR UPDATE`) and Redis distributed locks.
* **Idempotency:** Implements `Idempotency-Key` middleware to guarantee safe retries for payment transactions.
* **Reliability:** Uses the **Transactional Outbox Pattern** to ensure "at-least-once" delivery of email confirmations, decoupling the database transaction from the message broker.
* **Performance:** Optimized database queries (Index tuning, solving N+1) and stress-tested with **Locust** to simulate 10k RPS,.

---

## 🛠 Tech Stack

* **Backend:** Python 3.11, FastAPI, Pydantic V2 (Strict typing).
* **Database:** PostgreSQL 16 (Asyncpg driver + SQLAlchemy 2.0).
* **Concurrency & Caching:** Redis 7.
* **Message Broker:** RabbitMQ / Arq (Worker queues).
* **Infrastructure:** Docker Compose, GitHub Actions (CI/CD).
* **Testing:** Pytest (Unit/Integration), Locust (Load Testing).

---

## 🏗 Architecture & Design Decisions

### 1. Solving the "Overselling" Problem (Race Conditions)

**The Challenge:** In a naive implementation, if 2 users request the last ticket simultaneously, the check `if tickets > 0` passes for both, resulting in `tickets = -1`.

**My Solution:**
I implemented two strategies to handle concurrency:

1. **Pessimistic Locking (DB Level):** Utilizing PostgreSQL's `SELECT ... FOR UPDATE SKIP LOCKED`. This locks the specific row until the transaction commits, forcing other requests to wait or skip,.
2. **Distributed Locking (Redis):** Implemented the **Redlock** algorithm for scenarios where database locking is too expensive.

### 2. Ensuring Consistency (Transactional Outbox)

**The Challenge:** If the system crashes *after* saving the booking but *before* sending the confirmation email, the system is in an inconsistent state.

**My Solution:**
Instead of sending emails directly in the API handler:

1. The API saves the `Booking` AND a `Message` (Outbox) in the **same atomic database transaction**.
2. A background worker (Arq) reads the `Message` table asynchronously and processes the email sending.

### 3. Idempotency Implementation

**The Challenge:** In unstable networks, a client might retry a POST request (Payment), potentially charging the user twice.

**My Solution:**
Created a custom Middleware that caches the hash of the request body + `Idempotency-Key` header in Redis. Replayed requests return the cached response instantly without hitting the database.

---

## 📊 Performance Testing

The system was stress-tested using **Locust** to identify bottlenecks.

* **Scenario:** 1000 concurrent users attempting to buy 100 tickets.
* **Result:** Zero overselling. 99th percentile latency < 200ms.
* **Optimizations:** Added composite indexes on `(event_id, status)` and implemented connection pooling with `asyncpg`,.

---

## 💻 Getting Started

### Prerequisites

* Docker & Docker Compose

### Run Locally

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ticket-core.git
cd ticket-core

```


2. **Start Services (App, DB, Redis, Worker)**
```bash
docker-compose up --build -d

```


3. **Run Migrations**
```bash
docker-compose exec app alembic upgrade head

```


4. **Access Docs**
Open `http://localhost:8000/docs` to interact with the Swagger UI.

### Run Tests

```bash
docker-compose exec app pytest

```

---

## 📬 Contact

**Vlad Seliukov** - Backend Python Engineer

* [GitHub Profile Link]
* [LinkedIn Profile Link]
* seliukovvladyslav@gmail.com 

> *Built as a capstone engineering project to demonstrate proficiency in Distributed Systems and Backend Architecture.*