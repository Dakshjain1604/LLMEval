# AWS Deployment Guide for LlmEval

## Overview

This guide covers **three AWS deployment options** for running LlmEval every 12 hours:

1. **AWS Lambda + EventBridge** ⭐ Recommended - Serverless, cost-effective
2. **AWS EC2 + Cron** - Traditi
onal VM, simple and reliable
3. **AWS ECS Fargate + EventBridge** - Containerized, scalable

---

## Option 1: AWS Lambda + EventBridge (Recommended) ⭐

**Best for:** Cost-effectiveness, zero maintenance, pay-per-execution
**Cost:** ~$2-5/month (mostly for LLM API calls, not AWS)
**Difficulty:** Medium

### Architecture
```
EventBridge (Cron: 0 9,21 * * ?) → Lambda Function → S3 (database storage)
```

### Prerequisites
- AWS Account with CLI configured
- Docker installed locally

### Step 1: Prepare Lambda Package

```bash
# Install AWS SAM CLI (if not installed)
pip install aws-sam-cli

# Create deployment directory
cd /root/LlmEval
mkdir lambda-deploy
cd lambda-deploy

# Copy application files
cp -r ../src .
cp -r ../data .
cp ../run.py .
cp ../config.yaml .
cp ../requirements.txt .
```

### Step 2: Create Lambda Handler

Create `lambda_handler.py`:

```python
"""AWS Lambda handler for LlmEval."""
import os
import sys
import logging

# Set up paths
sys.path.insert(0, '/tmp')
sys.path.insert(0, os.path.dirname(__file__))

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Lambda entry point."""
    try:
        # Import and run
        from src.main import ReleaseMonitor

        # Use /tmp for writable storage (Lambda limitation)
        os.environ['DATABASE_PATH'] = '/tmp/releases.db'

        # Run monitor
        monitor = ReleaseMonitor('config.yaml')
        monitor.run()

        return {
            'statusCode': 200,
            'body': 'LlmEval completed successfully'
        }

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }
```

### Step 3: Create Dockerfile for Lambda

Create `Dockerfile`:

```dockerfile
FROM public.ecr.aws/lambda/python:3.12

# Copy requirements and install
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application code
COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY config.yaml ${LAMBDA_TASK_ROOT}/
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Set handler
CMD ["lambda_handler.lambda_handler"]
```

### Step 4: Create AWS SAM Template

Create `template.yaml`:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: LlmEval Serverless Deployment

Globals:
  Function:
    Timeout: 900  # 15 minutes
    MemorySize: 1024
    Environment:
      Variables:
        DISCORD_WEBHOOK_URL: !Ref DiscordWebhookUrl
        OPENROUTER_API_KEY: !Ref OpenRouterApiKey
        HUGGINGFACE_TOKEN: !Ref HuggingFaceToken
        KAGGLE_USERNAME: !Ref KaggleUsername
        KAGGLE_KEY: !Ref KaggleKey

Parameters:
  DiscordWebhookUrl:
    Type: String
    Description: Discord webhook URL
  OpenRouterApiKey:
    Type: String
    Description: OpenRouter API key
    NoEcho: true
  HuggingFaceToken:
    Type: String
    Description: HuggingFace token
    NoEcho: true
  KaggleUsername:
    Type: String
    Description: Kaggle username
  KaggleKey:
    Type: String
    Description: Kaggle API key
    NoEcho: true

Resources:
  LlmEvalFunction:
    Type: AWS::Serverless::Function
    Properties:
      PackageType: Image
      ImageUri: !Sub ${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/llmeval:latest
      Events:
        MorningSchedule:
          Type: Schedule
          Properties:
            Schedule: cron(0 9 * * ? *)  # 9 AM UTC
        EveningSchedule:
          Type: Schedule
          Properties:
            Schedule: cron(0 21 * * ? *)  # 9 PM UTC

Outputs:
  LlmEvalFunction:
    Description: Lambda Function ARN
    Value: !GetAtt LlmEvalFunction.Arn
```

### Step 5: Deploy to AWS

```bash
# 1. Build Docker image
docker build -t llmeval:latest .

# 2. Create ECR repository
aws ecr create-repository --repository-name llmeval --region us-east-1

# 3. Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# 4. Tag and push image
docker tag llmeval:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/llmeval:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/llmeval:latest

# 5. Deploy with SAM
sam deploy --guided \
  --parameter-overrides \
    DiscordWebhookUrl="YOUR_WEBHOOK_URL" \
    OpenRouterApiKey="YOUR_API_KEY" \
    HuggingFaceToken="YOUR_HF_TOKEN" \
    KaggleUsername="YOUR_KAGGLE_USER" \
    KaggleKey="YOUR_KAGGLE_KEY"
```

### Step 6: Monitor

```bash
# View logs
aws logs tail /aws/lambda/llmeval-LlmEvalFunction --follow

# Test manually
aws lambda invoke \
  --function-name llmeval-LlmEvalFunction \
  --payload '{}' \
  response.json
```

### Lambda Limitations & Solutions

**⚠️ Issues:**
- `/tmp` only 512MB (database growth)
- 15-minute timeout (might not be enough for 100+ releases)

**✅ Solutions:**
1. Use **S3** for database storage:
   ```python
   # Download DB from S3 at start
   # Upload DB to S3 at end
   ```

2. If timeout occurs, switch to **Option 2 (EC2)** or **Option 3 (ECS)**

---

## Option 2: AWS EC2 + Cron (Simple & Reliable) 🚀

**Best for:** Reliability, no timeout limits, easy debugging
**Cost:** ~$3-5/month (t3.micro instance)
**Difficulty:** Easy

### Step 1: Launch EC2 Instance

```bash
# Via AWS Console:
# 1. Go to EC2 → Launch Instance
# 2. Choose: Ubuntu 22.04 LTS (Free tier eligible)
# 3. Instance type: t3.micro or t3.small
# 4. Storage: 10-20 GB
# 5. Security group: Allow SSH (port 22) from your IP
# 6. Create/select key pair
# 7. Launch

# Or via AWS CLI:
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.micro \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxx \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=LlmEval}]'
```

### Step 2: Connect and Setup

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@YOUR_INSTANCE_IP

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12
sudo apt install python3.12 python3.12-venv python3-pip git -y

# Clone your repository (or upload files)
git clone https://github.com/YOUR_USERNAME/LlmEval.git
# OR: scp -r /root/LlmEval ubuntu@YOUR_INSTANCE_IP:~/

cd LlmEval
```

### Step 3: Setup Application

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
nano .env
# Paste your API keys, save (Ctrl+O, Ctrl+X)

# Test run
python run.py
```

### Step 4: Setup Cron Job

```bash
# Create run script
cat > /home/ubuntu/LlmEval/run_monitor.sh << 'EOF'
#!/bin/bash
cd /home/ubuntu/LlmEval
source venv/bin/activate
python run.py >> /home/ubuntu/LlmEval/data/cron.log 2>&1
EOF

chmod +x /home/ubuntu/LlmEval/run_monitor.sh

# Add to crontab
crontab -e

# Add these lines (runs at 9 AM and 9 PM UTC):
0 9 * * * /home/ubuntu/LlmEval/run_monitor.sh
0 21 * * * /home/ubuntu/LlmEval/run_monitor.sh
```

### Step 5: Verify Cron Setup

```bash
# Check crontab
crontab -l

# Test script manually
./run_monitor.sh

# Monitor logs
tail -f data/cron.log
tail -f data/monitor.log
```

### Step 6: Setup Log Rotation (Optional)

```bash
sudo nano /etc/logrotate.d/llmeval

# Add:
/home/ubuntu/LlmEval/data/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

### EC2 Advantages ✅

- ✅ No timeout limits
- ✅ Easy debugging (SSH access)
- ✅ Persistent storage
- ✅ Can install any dependencies
- ✅ Full control

### EC2 Management

```bash
# Check if running
sudo systemctl status cron

# View cron logs
grep CRON /var/log/syslog

# Stop instance when not needed (save money)
aws ec2 stop-instances --instance-ids i-xxxxxxxxx

# Start when needed
aws ec2 start-instances --instance-ids i-xxxxxxxxx

# Auto-start on schedule (optional)
# Use AWS Instance Scheduler: https://aws.amazon.com/solutions/implementations/instance-scheduler/
```

---

## Option 3: AWS ECS Fargate + EventBridge (Containerized)

**Best for:** Scalability, modern DevOps, CI/CD integration
**Cost:** ~$5-10/month
**Difficulty:** Advanced

### Step 1: Create Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY run.py config.yaml ./
COPY .env .

# Run
CMD ["python", "run.py"]
```

### Step 2: Build and Push to ECR

```bash
# Build
docker build -t llmeval:latest .

# Create ECR repo
aws ecr create-repository --repository-name llmeval

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag llmeval:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/llmeval:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/llmeval:latest
```

### Step 3: Create ECS Task Definition

Create `ecs-task-definition.json`:

```json
{
  "family": "llmeval",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "llmeval",
      "image": "YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/llmeval:latest",
      "essential": true,
      "environment": [
        {"name": "DISCORD_WEBHOOK_URL", "value": "YOUR_WEBHOOK"},
        {"name": "OPENROUTER_API_KEY", "value": "YOUR_KEY"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/llmeval",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Step 4: Register Task and Create EventBridge Rule

```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Create EventBridge rule (9 AM)
aws events put-rule \
  --name llmeval-morning \
  --schedule-expression "cron(0 9 * * ? *)"

# Create EventBridge rule (9 PM)
aws events put-rule \
  --name llmeval-evening \
  --schedule-expression "cron(0 21 * * ? *)"

# Add ECS as target
aws events put-targets \
  --rule llmeval-morning \
  --targets "Id"="1","Arn"="arn:aws:ecs:us-east-1:YOUR_ACCOUNT:cluster/default","RoleArn"="arn:aws:iam::YOUR_ACCOUNT:role/ecsEventsRole","EcsParameters"="{"TaskDefinitionArn":"arn:aws:ecs:us-east-1:YOUR_ACCOUNT:task-definition/llmeval:1","LaunchType":"FARGATE","NetworkConfiguration"={"awsvpcConfiguration"={"Subnets"=["subnet-xxxxx"],"SecurityGroups"=["sg-xxxxx"],"AssignPublicIp"="ENABLED"}}}"
```

---

## Comparison Table

| Feature | Lambda | EC2 | ECS Fargate |
|---------|--------|-----|-------------|
| **Cost/month** | $2-5 | $3-5 | $5-10 |
| **Setup Difficulty** | Medium | Easy | Advanced |
| **Timeout** | 15 min | Unlimited | Unlimited |
| **Maintenance** | Zero | Low | Low |
| **Debugging** | Harder | Easy | Medium |
| **Scalability** | Auto | Manual | Auto |
| **Best For** | Low volume | Reliability | Production |

---

## Recommended Approach by Use Case

### For Quick Start & Low Cost → EC2 ✅
1. Launch t3.micro EC2 instance ($3/month)
2. Install Python and dependencies
3. Setup cron job
4. Done in 15 minutes!

### For Production & Scale → ECS Fargate
1. Containerize application
2. Push to ECR
3. Setup ECS + EventBridge
4. Professional, scalable solution

### For Minimal Cost (existing AWS usage) → Lambda
1. Package as Lambda container
2. Deploy with SAM
3. Pay only per execution
4. Best if processing <100 releases

---

## Cost Breakdown

### Lambda Option
- Lambda execution: ~$0.20/month (2 runs/day × 10 min × $0.0000166667/GB-second)
- CloudWatch logs: ~$0.50/month
- **Total AWS: ~$1/month**
- LLM API: ~$2-5/month
- **Grand Total: $3-6/month**

### EC2 Option (t3.micro)
- EC2 instance: ~$3.50/month
- EBS storage: ~$1/month
- **Total AWS: ~$4.50/month**
- LLM API: ~$2-5/month
- **Grand Total: $6.50-9.50/month**

### ECS Fargate Option
- Fargate tasks: ~$5/month (2 runs/day × 10 min)
- CloudWatch logs: ~$0.50/month
- **Total AWS: ~$5.50/month**
- LLM API: ~$2-5/month
- **Grand Total: $7.50-10.50/month**

---

## Quick Start: Deploy to EC2 in 10 Minutes

```bash
# 1. Launch EC2 t3.micro with Ubuntu 22.04
# 2. SSH in
ssh -i your-key.pem ubuntu@YOUR_IP

# 3. Quick setup
curl -O https://raw.githubusercontent.com/YOUR_REPO/LlmEval/main/deploy/ec2-setup.sh
chmod +x ec2-setup.sh
./ec2-setup.sh

# 4. Configure .env
nano ~/LlmEval/.env

# 5. Test
cd ~/LlmEval && ./run_monitor.sh

# 6. Done! Cron will run automatically
```

---

## Monitoring & Maintenance

### Check Logs (All Options)

**Lambda:**
```bash
aws logs tail /aws/lambda/llmeval-function --follow
```

**EC2:**
```bash
ssh ubuntu@YOUR_IP
tail -f ~/LlmEval/data/monitor.log
```

**ECS:**
```bash
aws logs tail /ecs/llmeval --follow
```

### Database Backup

```bash
# EC2: Setup daily backup
echo "0 3 * * * cp /home/ubuntu/LlmEval/data/releases.db /home/ubuntu/backups/releases-\$(date +\%Y\%m\%d).db" | crontab -a

# Lambda/ECS: Backup to S3
aws s3 cp data/releases.db s3://your-bucket/backups/releases-$(date +%Y%m%d).db
```

### Alerts Setup

Create CloudWatch alarm for failures:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name llmeval-failures \
  --alarm-description "Alert on LlmEval failures" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 3600 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

---

## Troubleshooting

### Lambda timeout?
→ Switch to EC2 or increase Lambda timeout to 15 min

### Out of memory?
→ Increase Lambda memory or use EC2 with more RAM

### Database too large?
→ Use S3 for storage with SQLite over S3

### API rate limits?
→ Add exponential backoff in code

### High costs?
→ Use EC2 t3.micro with spot instances

---

## Security Best Practices

1. **Store secrets in AWS Secrets Manager:**
```bash
aws secretsmanager create-secret \
  --name llmeval/api-keys \
  --secret-string '{"OPENROUTER_API_KEY":"xxx","DISCORD_WEBHOOK_URL":"yyy"}'
```

2. **Use IAM roles** (not hardcoded credentials)

3. **Enable encryption:**
   - S3: Server-side encryption
   - EBS: Encrypted volumes
   - Lambda: Environment variable encryption

4. **Network security:**
   - EC2: Security group with minimal ports
   - Lambda/ECS: VPC with private subnets

---

## Next Steps

1. Choose your deployment option (recommend: EC2 for simplicity)
2. Follow the step-by-step guide
3. Test manually first
4. Setup monitoring
5. Configure backups

**Need help?** Check logs and verify:
- API keys are correct
- Security groups allow outbound traffic
- IAM permissions are set

---

**Ready to deploy?** Start with EC2 option - it's the easiest and most reliable! 🚀
