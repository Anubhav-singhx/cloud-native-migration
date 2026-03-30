# ADR-009: Resource Right-Sizing

**Date:** 2026-03-30
**Status:** Accepted
**Author:** Your Full Name

> **Context**: This is a portfolio project demonstrating production-grade
> architectural thinking. ADRs document the reasoning behind each technical
> decision as a real engineering team would.

## Resource Allocation

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|------------|-----------|----------------|-------------|
| auth-service | 100m | 200m | 128Mi | 256Mi |
| product-service | 100m | 200m | 128Mi | 256Mi |
| order-service | 100m | 200m | 128Mi | 256Mi |
| notification-service | 50m | 100m | 64Mi | 128Mi |
| postgres | 100m | 200m | 128Mi | 256Mi |

## Cost Analysis

| Cluster Config | Monthly Cost |
|---------------|-------------|
| This project (t3.small spot x3) | ~$12-15 |
| Naive on-demand (t3.medium x3) | ~$90 |
| Production-like (m5.large x3) | ~$300 |

## How to Verify Right-Sizing
```
kubectl top pods -n production
```

If actual CPU is consistently below 30% of request, reduce requests.
If actual memory is consistently above 80% of limit, increase limits.