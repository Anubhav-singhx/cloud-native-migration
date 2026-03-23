# ADR-001: Migration from Monolith to Microservices

**Date:** 2024-01-15  
**Status:** Accepted  
**Deciders:** Engineering Team

---

## Context

We have a Flask monolith (`monolith/app.py`) that handles authentication, 
product management, order processing, and notifications in a single application 
with a single SQLite database.

As the application grows, we identified the following critical problems:

### Problems with the Monolith

1. **Tight Coupling**: The order service directly imports and queries the Product 
   database model. Any change to the Product schema breaks Order logic.

2. **Single Point of Failure**: If the monolith crashes, ALL functionality goes 
   down — auth, products, orders, and notifications simultaneously.

3. **Cannot Scale Independently**: If product browsing gets 10x traffic during 
   a sale, we have to scale the ENTIRE app including auth and order processing, 
   wasting resources.

4. **Technology Lock-in**: The entire app is Flask. We cannot use a different 
   framework for a component that would benefit from it.

5. **Deployment Risk**: Any change to any part of the app requires a full 
   redeployment. A bug in the notification service can take down the entire 
   e-commerce platform.

6. **Team Scalability**: Multiple engineers editing the same `app.py` file causes 
   constant merge conflicts.

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
- Fault isolation: one service down doesn't affect others
- Teams can own individual services
- Each service can choose the best technology

### Negative
- Increased operational complexity (more things to monitor)
- Network latency between services (vs direct function calls)
- Distributed transactions are harder than local DB transactions
- More infrastructure to manage

### Mitigation
- Istio service mesh handles mTLS, retries, circuit breaking
- Jaeger distributed tracing makes cross-service debugging possible
- Kubernetes handles deployment complexity
- Prometheus + Grafana make monitoring manageable

---

## Alternatives Considered

1. **Modular Monolith**: Split into Python modules but keep one deployment. 
   Rejected: still scales as one unit, still single point of failure.

2. **Serverless (Lambda)**: Each endpoint as a Lambda function. 
   Rejected: cold start latency unacceptable for e-commerce, vendor lock-in too high.