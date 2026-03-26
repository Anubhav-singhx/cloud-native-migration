# ADR-007: Using Spot Instances for Worker Nodes

**Date:** 2024-01-15  
**Status:** Accepted
**Author:** Anubhav Singh

> **Context**: This is a portfolio project demonstrating production-grade
> architectural thinking. ADRs document the reasoning behind each technical
> decision as a real engineering team would.

## Decision

Use AWS Spot instances (capacity_type = "SPOT") for EKS worker nodes.

## Cost Analysis

| Instance Type | Pricing Model | Cost (t3.micro) |
|--------------|---------------|-----------------|
| On-Demand    | Fixed price   | ~$0.0104/hour   |
| Spot         | Market price  | ~$0.003/hour    |

**Savings: ~70% vs on-demand**

For our 2-node cluster running 24/7:
- On-demand: ~$15/month
- Spot:       ~$4.50/month

## Risk Mitigation

Spot instances can be reclaimed by AWS with 2-minute notice.

Mitigations implemented:
1. **Multiple instance types** in node group (t3.micro + t3.small) — 
   AWS is less likely to reclaim all types simultaneously
2. **2 AZs** — if spot capacity runs out in us-east-1a, us-east-1b still runs
3. **PodDisruptionBudgets** — always keeps minimum replicas running during interruption
4. **Node group min_size=1** — cluster never goes to zero nodes
5. **Kubernetes automatic rescheduling** — pods move to surviving nodes within ~30s

## Conclusion

For a portfolio project and non-critical workloads, spot instances provide 
exceptional cost savings with acceptable reliability risk.