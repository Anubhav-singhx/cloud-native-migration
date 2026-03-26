# ADR-002: Microservice Boundary Definitions

**Date:** 2024-01-15  
**Status:** Accepted

## Decision

Service boundaries are defined by **business domain ownership**, not by technical layers.

### Why These 4 Boundaries?

**auth-service** owns authentication because:
- User identity is a cross-cutting concern that all services need
- JWT validation should be centralized so logic changes don't cascade
- User data (passwords, profiles) is sensitive — minimize services touching it

**product-service** owns product catalog because:
- Products have a clear lifecycle: create → update → archive
- Stock management is a product concern, not an order concern
- Independent scaling: product browsing gets 10x the traffic of order creation

**order-service** owns order lifecycle because:
- Orders have a complex state machine: pending → confirmed → shipped → delivered
- Order logic orchestrates across products and notifications (saga pattern)
- Order data has different retention requirements (legal compliance)

**notification-service** owns notifications because:
- Decoupling notifications means adding a new channel (SMS, push) doesn't touch order code
- Notifications are fire-and-forget — if down, orders still work
- Can be replaced with a queue (SQS/Kafka) without touching other services

## Communication Pattern

Services communicate via **synchronous HTTP** for:
- Stock checks (order needs to know current stock)
- Auth validation (all services verify tokens)

Services communicate via **fire-and-forget HTTP** for:
- Notifications (order doesn't wait for notification delivery)

In production we would add **async messaging (SQS/Kafka)** for notifications 
to provide better durability.