# ADR-005: Canary Deployment Strategy

**Date:** 2026-03-27
**Status:** Accepted
**Author:** Anubhav Singh

> **Context**: This is a portfolio project demonstrating production-grade
> architectural thinking. ADRs document the reasoning behind each technical
> decision as a real engineering team would.

## Context

Releasing new versions with zero downtime requires a strategy for gradually
shifting traffic to the new version while monitoring for errors.

## Decision

Use Istio VirtualService traffic splitting for canary deployments.

### Process
1. Deploy v2 alongside v1 (both running simultaneously)
2. Route 10% of traffic to v2, 90% to v1
3. Monitor error rates in Grafana for 60 seconds
4. If healthy: shift 10% → 30% → 50% → 70% → 100%
5. If unhealthy at any step: immediately shift 100% back to v1

### Why Istio over Kubernetes Rolling Updates?

| Feature | Rolling Update | Istio Canary |
|---------|---------------|--------------|
| Traffic control | By replica count | By exact percentage |
| Rollback speed | Slow (new rollout) | Instant (change weights) |
| Both versions live | Briefly | As long as needed |
| Monitoring window | Fixed | Configurable |

Rolling updates shift traffic by replacing pods — you cannot say
"send exactly 10% to v2." Istio splits traffic independently of
replica count, giving precise control.