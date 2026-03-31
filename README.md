# Cloud-Native Architecture Migration
### Flask Monolith → FastAPI Microservices on AWS EKS

[![CI Pipeline](https://github.com/anubhav-singhx/cloud-native-migration/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/cloud-native-migration/actions/workflows/ci.yml)
[![CD Pipeline](https://github.com/anubhav-singhx/cloud-native-migration/actions/workflows/cd.yml/badge.svg)](https://github.com/YOUR_USERNAME/cloud-native-migration/actions/workflows/cd.yml)

> A production-grade migration from a Python Flask monolith to FastAPI
> microservices deployed on AWS EKS with full observability, CI/CD,
> and disaster recovery.

---

## What This Project Demonstrates

| Skill | Implementation |
|-------|---------------|
| System Design | Monolith decomposition into 4 domain-driven microservices |
| Cloud Infrastructure | AWS EKS, VPC, ALB, ECR with Terraform IaC |
| Container Orchestration | Kubernetes with HPA, PDB, multi-AZ deployment |
| Service Mesh | Istio configs for mTLS, canary deployments, circuit breaking |
| Observability | Prometheus + Grafana + Jaeger tracing + Loki logging |
| CI/CD | GitHub Actions with Trivy security scanning + EKS deployment |
| Disaster Recovery | Velero + S3 with tested RTO < 5 minutes |
| Cost Engineering | ~$12-15/month using spot instances (vs ~$300 naive) |

---

## Architecture

### Before — Flask Monolith
```
[Client] → [Single Flask App] → [Single SQLite DB]

Problems: Single point of failure, cannot scale independently,
tight coupling, full redeployment for any change
```

### After — Microservices on EKS
```
[Client]
    ↓
[AWS ALB — API Gateway]
    ↓
┌─────────────────────────────────────────┐
│  AWS EKS (us-east-1a + us-east-1b)     │
│                                          │
│  auth-service    product-service        │
│  order-service   notification-service   │
│                                          │
│  PostgreSQL (persistent EBS volume)     │
│                                          │
│  Prometheus + Grafana (monitoring)      │
│  Jaeger (distributed tracing)           │
│  Loki + Promtail (log aggregation)      │
└─────────────────────────────────────────┘
    ↓
[S3 — Velero backups]
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| App (Before) | Python Flask (monolith) |
| App (After) | Python FastAPI (microservices) |
| Database | PostgreSQL 15 |
| Containers | Docker (multi-stage builds, non-root users) |
| Orchestration | AWS EKS 1.29 |
| IaC | Terraform |
| Registry | Amazon ECR |
| Service Mesh | Istio (configs written, see service-mesh/) |
| API Gateway | AWS ALB Ingress Controller |
| Metrics | Prometheus + Grafana |
| Tracing | Jaeger + OpenTelemetry |
| Logging | Loki + Promtail |
| CI/CD | GitHub Actions |
| Security Scanning | Trivy + TruffleHog |
| Backup/DR | Velero + S3 |

---

## Live Endpoints

**Base URL:** `http://k8s-producti-apigatew-841093a919-854161971.us-east-1.elb.amazonaws.com`

| Method | Endpoint | Auth | Description |
|--------|---------|------|-------------|
| POST | /auth/register | No | Register user |
| POST | /auth/login | No | Login, get JWT |
| GET | /auth/health | No | Health check |
| GET | /products | No | List products |
| POST | /products | Bearer | Create product |
| GET | /products/health | No | Health check |
| POST | /orders | Bearer | Create order |
| GET | /orders | Bearer | Get orders |
| GET | /orders/health | No | Health check |
| GET | /notifications/health | No | Health check |

---

## Cost Analysis

| Resource | Strategy | Cost |
|---------|---------|------|
| EKS nodes (t3.small spot x3) | Spot instances | ~$8-10/month |
| AWS ALB | Shared ingress | ~$2-3/month |
| ECR + S3 | Minimal storage | ~$1-2/month |
| **Total** | | **~$12-15/month** |

vs naive on-demand architecture: ~$200-300/month

---

## Disaster Recovery

| Metric | Target | Measured |
|--------|--------|---------|
| RTO | < 5 min | [your time] |
| RPO | < 1 hour | < 1 hour |

---

## Architectural Decision Records

| ADR | Decision |
|-----|---------|
| [ADR-001](docs/adr/ADR-001-why-microservices.md) | Why migrate to microservices |
| [ADR-002](docs/adr/ADR-002-service-boundaries.md) | Service boundary definitions |
| [ADR-003](docs/adr/ADR-003-autoscaling-policy.md) | HPA autoscaling policy |
| [ADR-004](docs/adr/ADR-004-api-gateway.md) | ALB as API gateway |
| [ADR-005](docs/adr/ADR-005-canary-strategy.md) | Canary deployment strategy |
| [ADR-006](docs/adr/ADR-006-istio-resource-constraints.md) | Istio resource decision |
| [ADR-007](docs/adr/ADR-007-spot-instances.md) | Spot instance cost savings |
| [ADR-008](docs/adr/ADR-008-disaster-recovery.md) | Velero DR strategy |
| [ADR-009](docs/adr/ADR-009-right-sizing.md) | Resource right-sizing |

---

## Quick Start (Local)
```bash
git clone https://github.com/YOUR_USERNAME/cloud-native-migration.git
cd cloud-native-migration

# Run the monolith (the before)
cd monolith
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
python app.py
# → http://localhost:5000

# Run all microservices locally
cd ..
docker-compose up --build
# auth-service        → http://localhost:8001/docs
# product-service     → http://localhost:8002/docs
# order-service       → http://localhost:8003/docs
# notification-service→ http://localhost:8004/docs
# jaeger UI           → http://localhost:16686
```

---

## Security

- All containers run as non-root users
- Multi-stage Docker builds minimize attack surface
- Trivy scans every image on push
- TruffleHog scans for secret leaks on every commit
- JWT tokens expire after 60 minutes
- All secrets via GitHub Secrets (never in code)
- Istio mTLS configs ready for production deployment

---

## What I Would Do Differently in Production

- Use AWS RDS instead of in-cluster PostgreSQL
- Use SQS/Kafka for notification events (async messaging)
- Use AWS Secrets Manager instead of environment variables
- Add WAF to the ALB for DDoS protection
- Deploy across 3 AZs instead of 2
- Use m5.large nodes to run full Istio service mesh
