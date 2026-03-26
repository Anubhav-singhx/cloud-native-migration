# ADR-002: Microservice Boundary Definitions

**Date:** 2026-03-22
**Status:** Accepted
**Author:** Anubhav Singh

> **Context**: This is a portfolio project demonstrating production-grade
> architectural thinking. ADRs document the reasoning behind each technical
> decision as a real engineering team would.

---

## Context

Once the decision to decompose the monolith was made (ADR-001), the next
question was: where exactly do the boundaries go? This ADR documents the
reasoning behind each service boundary.

---

## Decision

Service boundaries are defined by **business domain ownership**, not by
technical layers (not "all controllers in one service, all models in another").

### Why These 4 Boundaries?

**auth-service** owns authentication because:
- User identity is a cross-cutting concern that all other services depend on
- Centralizing JWT logic means a change to token expiry or algorithm only
  happens in one place, not across four services
- User data (passwords, profiles) is sensitive — fewer services touching it
  means a smaller attack surface

**product-service** owns the product catalog because:
- Products have a clear lifecycle: create → update → archive
- Stock management is a product concern, not an order concern — the order
  service should ask the product service "do you have stock?" rather than
  querying the products table directly
- Product browsing gets significantly more traffic than order creation,
  so independent scaling is valuable here

**order-service** owns order lifecycle because:
- Orders have a complex state machine: pending → confirmed → shipped → delivered
- Order logic orchestrates across products and notifications (saga pattern)
- Order data has different retention and compliance requirements than
  product or user data

**notification-service** owns notifications because:
- Decoupling notifications means adding a new channel (SMS, push notification)
  does not require touching order or auth code
- Notifications are fire-and-forget — if this service is down, orders still
  succeed. The order is not blocked waiting for a notification to send.
- This service can be replaced with a managed queue (SQS + Lambda) in
  production without changing any other service

---

## Communication Pattern

**Synchronous HTTP** is used for:
- Token validation (auth-service called by product and order services)
- Stock checks (order-service calls product-service before confirming an order)

**Fire-and-forget HTTP** is used for:
- Notifications (order-service calls notification-service but does not wait
  for the response — if it fails, the order is still confirmed)

### Future Improvement
In a production system, notifications would use **async messaging (SQS or Kafka)**
instead of fire-and-forget HTTP. This provides durability — if the notification
service is down, the message sits in the queue and is processed when it recovers.
This was not implemented here to keep the architecture focused on the core
microservices patterns being demonstrated.