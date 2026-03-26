# ADR-001b: Why Dockerizing a Monolith Is Not Enough

**Date:** 2026-03-21
**Status:** Accepted
**Author:** Anubhav Singh

> **Context**: This is a portfolio project demonstrating production-grade
> architectural thinking. ADRs document the reasoning behind each technical
> decision as a real engineering team would.

---

## Context

After containerizing the Flask monolith in Phase 2, it became clear that
putting a monolith in Docker solves the environment consistency problem
but does not solve the underlying architectural problems.

---

## Problems That Remain After Containerization

1. **Image size**: The monolith image contains ALL dependencies for auth,
   products, orders, and notifications combined. Each microservice image
   only needs its own dependencies — making them significantly smaller
   and faster to pull during deployments.

2. **Restart blast radius**: If the notification code crashes, Kubernetes
   restarts the ENTIRE monolith container, briefly taking down auth and
   products too. With separate containers, only the affected service restarts.

3. **Scaling inefficiency**: Kubernetes cannot be told to scale up only the
   product service — it is all one container. The entire monolith must scale
   even if only one feature is under load.

---

## Conclusion

Containerization is a necessary step but not a sufficient one. The monolith
must be decomposed into independent services before containerization delivers
its full benefits. This finding reinforces the decision in ADR-001.