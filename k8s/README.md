# Kubernetes Deployment

## Quick Deploy (3 steps)

### 1. Build & Push Image
```bash
docker build -t your-registry/llmeval:latest .
docker push your-registry/llmeval:latest
```

### 2. Edit `all-in-one.yaml`
Replace these values:
- Line 12: `YOUR_DISCORD_WEBHOOK_URL`
- Line 13: `YOUR_OPENROUTER_API_KEY`
- Line 49: `YOUR_REGISTRY/llmeval:latest`

### 3. Deploy
```bash
kubectl apply -f k8s/all-in-one.yaml
```

Done! ✅

---

## Management

**View status:**
```bash
kubectl get cronjob -n llmeval
kubectl get jobs -n llmeval
```

**View logs:**
```bash
# Get latest job name
kubectl get jobs -n llmeval

# View logs
kubectl logs -n llmeval job/JOB-NAME -f
```

**Manual run:**
```bash
kubectl create job --from=cronjob/llmeval-monitor test-run -n llmeval
```

**Update secrets:**
```bash
kubectl edit secret llmeval-secrets -n llmeval
```

**Update config:**
```bash
kubectl edit configmap llmeval-config -n llmeval
```

**Delete everything:**
```bash
kubectl delete namespace llmeval
```

---

## Schedule Options

Edit line 38 in `all-in-one.yaml`:

- Every 6 hours: `0 */6 * * *`
- Every 12 hours: `0 */12 * * *`
- Daily at 9 AM: `0 9 * * *`
- Current (9 AM & 9 PM): `0 9,21 * * *`

---

## Troubleshooting

**Pod won't start:**
```bash
kubectl describe pod POD-NAME -n llmeval
```

**Check secrets:**
```bash
kubectl get secret llmeval-secrets -n llmeval -o yaml
```

**Check storage:**
```bash
kubectl get pvc -n llmeval
```

**Access database:**
```bash
POD=$(kubectl get pods -n llmeval -l job-name=JOB-NAME -o name | head -1)
kubectl exec -n llmeval $POD -- sqlite3 /app/data/releases.db ".tables"
```

---

## Production Tips

**Better secrets management:**
```bash
# Don't store secrets in YAML!
kubectl create secret generic llmeval-secrets \
  --from-literal=DISCORD_WEBHOOK_URL="your-webhook" \
  --from-literal=OPENROUTER_API_KEY="your-key" \
  -n llmeval

# Then remove the Secret section from all-in-one.yaml before applying
```

**Backup database:**
```bash
POD=$(kubectl get pods -n llmeval -l job-name=JOB-NAME -o name | head -1)
kubectl cp llmeval/$POD:/app/data/releases.db ./backup-$(date +%Y%m%d).db
```

**Monitor with Prometheus:**
Add monitoring labels to CronJob in all-in-one.yaml

**Use external database:**
Replace SQLite with PostgreSQL for production
