# ADR-003: Autoscaling Policy

**Date:** 2026-03-23
**Status:** Accepted
**Author:** Your Full Name

> **Context**: This is a portfolio project demonstrating production-grade
> architectural thinking. ADRs document the reasoning behind each technical
> decision as a real engineering team would.

## Decision

Use Kubernetes HorizontalPodAutoscaler (HPA) for all services.

## Configuration

| Service | Min Replicas | Max Replicas | Scale Up Trigger |
|---------|-------------|-------------|-----------------|
| auth-service | 1 | 5 | CPU > 70% |
| product-service | 1 | 5 | CPU > 70% |
| order-service | 1 | 5 | CPU > 70% |
| notification-service | 1 | 3 | CPU > 70% |

## Why CPU-based scaling

Auth and product services are CPU-bound (JWT operations, DB queries).
CPU > 70% is a reliable signal that a service needs more capacity.

## Scale-down behavior

Default 5-minute stabilization window prevents thrashing — avoids
scaling down immediately after a traffic spike, which would cause
another scale-up seconds later.

## Portfolio Note

HPA requires the Kubernetes metrics-server to be installed. On EKS,
metrics-server is available as an add-on. HPAs are configured in the
Kubernetes manifests but show `<unknown>` for targets until metrics-server
is installed and collecting data.