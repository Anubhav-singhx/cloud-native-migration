# ADR-008: Disaster Recovery Strategy with Velero

**Date:** 2026-03-30
**Status:** Accepted
**Author:** Your Full Name

> **Context**: This is a portfolio project demonstrating production-grade
> architectural thinking. ADRs document the reasoning behind each technical
> decision as a real engineering team would.

## Decision

Use Velero with S3 backend for Kubernetes cluster backups.

## Why Velero

- Backs up entire Kubernetes state (deployments, services, configmaps, PVCs)
- Works natively with AWS S3 and EBS snapshots
- Single command restore
- Free and open source

## Backup Strategy

| Type | Schedule | Retention |
|------|---------|-----------|
| Full namespace backup | Every 1 hour | 72 hours |

## Measured Results

| Metric | Result |
|--------|--------|
| RTO | [your measured time] |
| RPO | Max 1 hour |

## Alternatives Considered

- **AWS Backup**: Managed service, easier but costs more and less flexible
- **Manual pg_dump**: Only backs up database, not Kubernetes state
- **Velero + Restic**: Adds file-level backup but too complex for this project