# ADR-001: Migration from Monolith to Microservices

**Date:** 2026-03-20
**Status:** Accepted
**Author:** Anubhav Singh

> **Context**: This is a portfolio project demonstrating production-grade
> architectural thinking. ADRs document the reasoning behind each technical
> decision as a real engineering team would.

---

## Context

This project starts with a Flask monolith (`monolith/app.py`) that handles
authentication, product management, order processing, and notifications in a
single application with a single SQLite database.

The following critical problems were identified with this approach:

### Problems with the Monolith

1. **Tight Coupling**: The order logic directly imports and queries the Product
   database model. Any change to the Product schema breaks Order logic.

2. **Single Point of Failure**: If the monolith crashes, ALL functionality goes
   down — auth, products, orders, and notifications simultaneously.

3. **Cannot Scale Independently**: If product browsing gets 10x traffic during
   a sale, the ENTIRE app must be scaled including auth and order processing,
   wasting resources.

4. **Technology Lock-in**: The entire app is Flask. No component can adopt a
   different framework even if it would benefit from one.

5. **Deployment Risk**: Any change to any part of the app requires a full
   redeployment. A bug in the notification code can take down the entire
   e-commerce platform.

6. **No Ownership Boundaries**: All logic lives in one file, making it hard to
   reason about what belongs where as the codebase grows.

---

## Decision

Decompose the monolith into 4 independent microservices:

| Service | Responsibility | Port |
|---------|---------------|------|
| auth-service | JWT authentication, user management | 8001 |
| product-service | Product catalog, inventory | 8002 |
| order-service | Order lifecycle, payment orchestration | 8003 |
| notification-service | Async notifications via events | 8004 |

Each service:
- Has its **own PostgreSQL schema** (no shared database)
- Is deployed as an **independent Docker container**
- Communicates via **HTTP REST APIs** (not direct DB queries)
- Can be **scaled independently** based on its own load

---

## Consequences

### Positive
- Independent deployment and scaling per service
- Fault isolation: one service down does not affect others
- Clear ownership boundaries per service
- Each service can evolve its technology independently

### Negative
- Increased operational complexity (more things to monitor)
- Network latency between services (vs direct function calls in a monolith)
- Distributed transactions are harder than local DB transactions
- More infrastructure to manage

### Mitigation
- Istio service mesh handles mTLS, retries, and circuit breaking
- Jaeger distributed tracing makes cross-service debugging possible
- Kubernetes handles deployment complexity
- Prometheus + Grafana make monitoring manageable at scale

---

## Alternatives Considered

1. **Modular Monolith**: Split into Python modules but keep one deployment.
   Rejected — still scales as one unit and remains a single point of failure.

2. **Serverless (AWS Lambda)**: Each endpoint as a Lambda function.
   Rejected — cold start latency is unacceptable for e-commerce, and
   vendor lock-in is too high for a portable architecture.