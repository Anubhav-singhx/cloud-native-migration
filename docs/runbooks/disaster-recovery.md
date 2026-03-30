# Disaster Recovery Runbook

**Author:** Your Full Name  
**Last Updated:** 2026-03-30

## Recovery Metrics

| Metric | Target | Measured |
|--------|--------|---------|
| RTO (Recovery Time) | < 5 min | [fill in your time] |
| RPO (Data Loss Window) | < 1 hour | < 1 hour (hourly backups) |

## When to Use This Runbook

- Production namespace deleted or corrupted
- Cluster nodes all fail simultaneously
- Accidental deletion of deployments or services

## Step-by-Step Recovery

### Step 1 — Verify the disaster
```
kubectl get namespace production
kubectl get pods -n production
```

### Step 2 — List available backups
```
velero backup get
```
Pick the most recent backup with `Phase: Completed`.

### Step 3 — Restore
```
velero restore create --from-backup BACKUP_NAME
```

### Step 4 — Monitor restoration
```
kubectl get pods -n production -w
```

### Step 5 — Verify all services healthy
```
curl.exe http://YOUR_ALB_URL/auth/health
curl.exe http://YOUR_ALB_URL/products/health
curl.exe http://YOUR_ALB_URL/orders/health
curl.exe http://YOUR_ALB_URL/notifications/health
```

### Step 6 — Verify database has data
```
kubectl exec -it deployment/postgres -n production -- psql -U postgres -c "\l"
```

## Backup Verification Checklist (run weekly)
- [ ] Latest backup exists in S3
- [ ] Backup phase is Completed not Failed
- [ ] Velero schedule is still active
- [ ] Test restore in staging environment