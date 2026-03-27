# ADR-006: Istio Service Mesh — Configuration vs Runtime

**Date:** 2026-03-27
**Status:** Accepted
**Author:** Your Full Name

> **Context**: This is a portfolio project demonstrating production-grade
> architectural thinking. ADRs document the reasoning behind each technical
> decision as a real engineering team would.

## Context

Istio was selected as the service mesh for mTLS, canary deployments, and
circuit breaking. All configuration files are written and present in
`service-mesh/`. However, running Istio on this cluster was not feasible.

## Constraint

The cluster uses t3.small spot instances with an 11 pod per node hard limit
(AWS ENI restriction). Node 2 runs at full capacity with kube-system and
application pods. Istiod requires approximately 300MB RAM and 2-3 pod slots
which are not available without evicting running application pods.

## Decision

Ship Istio configuration files without running the control plane on this
portfolio cluster.

| File | Demonstrates |
|------|-------------|
| `service-mesh/peer-authentication.yaml` | mTLS STRICT mode between all services |
| `service-mesh/product-canary.yaml` | Traffic splitting for canary deployments |
| `service-mesh/circuit-breaker.yaml` | Outlier detection, connection pooling |

In production these would be applied with:
```bash
istioctl install --set profile=minimal -y
kubectl label namespace production istio-injection=enabled
kubectl apply -f service-mesh/
```

## In Production

On a production cluster (m5.large nodes, 29+ pods per node), these configs
apply directly with no application code changes — Istio works at the
infrastructure level via Envoy sidecar injection.

## Alternatives Considered

- **Linkerd**: Lighter than Istio (~200MB), could run on this cluster.
  Rejected — Istio is more widely adopted and better demonstrates
  production-grade service mesh knowledge.

- **Upgrade to larger nodes**: Would cost ~$40-60/month.
  Rejected — portfolio project must stay within zero-cost budget.