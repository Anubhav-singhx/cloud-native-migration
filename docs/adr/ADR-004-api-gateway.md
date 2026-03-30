# ADR-004: API Gateway Strategy

**Date:** 2026-03-24
**Status:** Accepted
**Author:** Your Full Name

> **Context**: This is a portfolio project demonstrating production-grade
> architectural thinking. ADRs document the reasoning behind each technical
> decision as a real engineering team would.

## Decision

Use AWS ALB (Application Load Balancer) via the AWS Load Balancer Controller
as the API gateway / ingress for all external traffic.

## Routing Rules

| Path Prefix | Routes To | Port |
|------------|-----------|------|
| /auth | auth-service | 8001 |
| /products | product-service | 8002 |
| /orders | order-service | 8003 |
| /notifications | notification-service | 8004 |

## Why ALB over Nginx Ingress

- ALB is a managed AWS service — no ingress controller pods to manage
- Native integration with AWS WAF for rate limiting and DDoS protection
- Automatic SSL termination with ACM certificates
- No additional cost beyond standard ALB pricing

## Why Not API Gateway (AWS)

- AWS API Gateway adds ~10ms latency per request
- Costs more at scale
- ALB provides sufficient routing and security for this use case