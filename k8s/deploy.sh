#!/bin/bash
set -e

echo "🚀 LlmEval K8s Deploy"
echo ""

# Get inputs
read -p "Container registry (e.g., docker.io/username): " REGISTRY
read -p "Discord webhook URL: " DISCORD_WEBHOOK
read -sp "OpenRouter API key: " OPENROUTER_KEY
echo ""

IMAGE="${REGISTRY}/llmeval:latest"

# Build and push
echo "📦 Building image..."
docker build -t "$IMAGE" .
docker push "$IMAGE"

# Update YAML
echo "📝 Updating manifest..."
sed "s|YOUR_REGISTRY/llmeval:latest|${IMAGE}|g; s|YOUR_DISCORD_WEBHOOK_URL|${DISCORD_WEBHOOK}|g; s|YOUR_OPENROUTER_API_KEY|${OPENROUTER_KEY}|g" k8s/all-in-one.yaml > /tmp/llmeval-deploy.yaml

# Deploy
echo "☸️  Deploying to Kubernetes..."
kubectl apply -f /tmp/llmeval-deploy.yaml
rm /tmp/llmeval-deploy.yaml

echo ""
echo "✅ Deployed successfully!"
echo ""
echo "View status:"
echo "  kubectl get cronjob -n llmeval"
echo "  kubectl get jobs -n llmeval"
echo ""
echo "Manual run:"
echo "  kubectl create job --from=cronjob/llmeval-monitor test-run -n llmeval"
echo ""
echo "View logs:"
echo "  kubectl logs -n llmeval job/JOB-NAME -f"
