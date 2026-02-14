# LlmEval AWS Lambda Deployment

Deploy LlmEval as a serverless function on AWS Lambda with EventBridge scheduling.

## 🎯 Overview

This deployment option provides:
- ✅ **Serverless** - No servers to manage
- ✅ **Cost-effective** - Pay only per execution (~$2-3/month AWS costs)
- ✅ **Automatic scaling** - Scales automatically
- ✅ **Persistent storage** - Database stored in S3
- ✅ **Scheduled execution** - Runs automatically every 12 hours
- ✅ **CloudWatch monitoring** - Built-in logging and alarms

## 📋 Prerequisites

### 1. AWS Account
- Active AWS account with permissions to create Lambda, S3, ECR, CloudWatch, EventBridge

### 2. AWS CLI
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (e.g., us-east-1), Output format (json)
```

### 3. Docker
```bash
# Install Docker (Ubuntu)
sudo apt update
sudo apt install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

### 4. AWS SAM CLI
```bash
pip install aws-sam-cli
```

## 🚀 Quick Deployment

### Option A: Automated Deployment (Recommended)

```bash
cd lambda-deploy
./deploy.sh
```

The script will:
1. ✅ Check prerequisites
2. ✅ Create ECR repository
3. ✅ Build Docker image
4. ✅ Push to ECR
5. ✅ Deploy with SAM
6. ✅ Setup EventBridge schedules
7. ✅ Create S3 bucket for database
8. ✅ Setup CloudWatch alarms

**Follow the prompts to enter:**
- Discord Webhook URL
- OpenRouter API Key
- Optional: HuggingFace Token, Kaggle credentials, GitHub token

### Option B: Manual Deployment

#### Step 1: Prepare Files

```bash
cd lambda-deploy

# Copy necessary files
cp ../config.yaml .
cp ../requirements.txt .
cp -r ../src .
```

#### Step 2: Create ECR Repository

```bash
# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"  # Change to your region

# Create ECR repository
aws ecr create-repository \
    --repository-name llmeval \
    --region ${AWS_REGION} \
    --image-scanning-configuration scanOnPush=true
```

#### Step 3: Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build image
docker build -t llmeval:latest .

# Tag and push
docker tag llmeval:latest \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/llmeval:latest

docker push \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/llmeval:latest
```

#### Step 4: Deploy with SAM

```bash
sam deploy \
    --template-file template.yaml \
    --stack-name llmeval-stack \
    --region ${AWS_REGION} \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        DiscordWebhookUrl="YOUR_DISCORD_WEBHOOK" \
        OpenRouterApiKey="YOUR_OPENROUTER_KEY" \
        HuggingFaceToken="YOUR_HF_TOKEN" \
        KaggleUsername="YOUR_KAGGLE_USER" \
        KaggleKey="YOUR_KAGGLE_KEY" \
        GithubToken="YOUR_GITHUB_TOKEN" \
    --resolve-s3
```

## 📊 Verify Deployment

### Check Stack Status

```bash
aws cloudformation describe-stacks \
    --stack-name llmeval-stack \
    --query 'Stacks[0].StackStatus'
```

### Test Lambda Function

```bash
# Invoke manually
aws lambda invoke \
    --function-name llmeval-monitor \
    --payload '{}' \
    response.json

# Check response
cat response.json
```

### View Logs

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/llmeval-monitor --follow

# Or view in AWS Console
# CloudWatch → Log groups → /aws/lambda/llmeval-monitor
```

### Check S3 Database

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# List files in S3 bucket
aws s3 ls s3://llmeval-database-${AWS_ACCOUNT_ID}/

# Download database
aws s3 cp s3://llmeval-database-${AWS_ACCOUNT_ID}/releases.db ./

# View backups
aws s3 ls s3://llmeval-database-${AWS_ACCOUNT_ID}/backups/
```

## ⚙️ Configuration

### Environment Variables

Set via SAM template parameters:

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_WEBHOOK_URL` | Yes | Discord webhook for notifications |
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key for LLM |
| `S3_BUCKET_NAME` | Auto | Created automatically by CloudFormation |
| `HUGGINGFACE_TOKEN` | No | HuggingFace API token |
| `KAGGLE_USERNAME` | No | Kaggle username |
| `KAGGLE_KEY` | No | Kaggle API key |
| `GITHUB_TOKEN` | No | GitHub API token |

### Update Environment Variables

```bash
aws lambda update-function-configuration \
    --function-name llmeval-monitor \
    --environment "Variables={
        DISCORD_WEBHOOK_URL=new_webhook_url,
        OPENROUTER_API_KEY=new_api_key
    }"
```

### Change Schedule

Edit `template.yaml` and update:

```yaml
Schedule1:
  Default: "cron(0 9 * * ? *)"  # Morning (9 AM UTC)

Schedule2:
  Default: "cron(0 21 * * ? *)"  # Evening (9 PM UTC)
```

Then redeploy:

```bash
sam deploy --template-file template.yaml --stack-name llmeval-stack
```

## 📈 Monitoring

### CloudWatch Dashboards

1. Go to **CloudWatch → Dashboards**
2. View Lambda metrics:
   - Invocations
   - Duration
   - Errors
   - Throttles

### CloudWatch Alarms

Automatically created:
- ✅ **Function Errors** - Alerts on any errors
- ✅ **Function Duration** - Alerts if approaching 15min timeout

### View Metrics

```bash
# Get invocation count
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Invocations \
    --dimensions Name=FunctionName,Value=llmeval-monitor \
    --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 3600 \
    --statistics Sum

# Get error count
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Errors \
    --dimensions Name=FunctionName,Value=llmeval-monitor \
    --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 3600 \
    --statistics Sum
```

## 💰 Cost Breakdown

### AWS Costs (Monthly)

**Lambda:**
- 2 executions/day × 30 days = 60 executions
- ~10 minutes per execution = 600 minutes
- 2048 MB memory
- Cost: ~$1.50/month

**S3:**
- Database storage: ~10MB
- Backups: ~100MB (30 days)
- Cost: ~$0.50/month

**CloudWatch Logs:**
- ~500MB logs/month
- Cost: ~$0.50/month

**EventBridge:**
- 60 scheduled events/month
- Cost: $0 (free tier)

**Total AWS: ~$2.50-3/month**

Plus LLM API costs: ~$2-5/month

**Grand Total: $4.50-8/month**

## 🔧 Troubleshooting

### Issue: Lambda timeout (15 minutes)

**Solution 1:** Reduce releases processed per run
```yaml
# In config.yaml
filtering:
  max_items_per_run: 10  # Reduce from 15
```

**Solution 2:** Increase memory (faster processing)
```yaml
# In template.yaml
Globals:
  Function:
    MemorySize: 3008  # Increase from 2048
```

**Solution 3:** Split into two functions (morning/evening separate)

### Issue: Out of memory

**Increase Lambda memory:**
```bash
aws lambda update-function-configuration \
    --function-name llmeval-monitor \
    --memory-size 3008
```

### Issue: Database not persisting

**Check S3 bucket:**
```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 ls s3://llmeval-database-${AWS_ACCOUNT_ID}/

# Should see: releases.db
```

**Check Lambda logs for S3 errors:**
```bash
aws logs tail /aws/lambda/llmeval-monitor --since 1h | grep S3
```

### Issue: Function not running on schedule

**Check EventBridge rules:**
```bash
aws events list-rules --name-prefix llmeval

# Enable rules if disabled
aws events enable-rule --name llmeval-morning-schedule
aws events enable-rule --name llmeval-evening-schedule
```

### Issue: Permission errors

**Update Lambda execution role:**
```bash
# Check current role
aws lambda get-function --function-name llmeval-monitor \
    --query 'Configuration.Role'

# Attach additional policies if needed
aws iam attach-role-policy \
    --role-name llmeval-stack-LlmEvalFunctionRole-XXXXX \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

## 🔄 Update Deployment

### Update Code Only

```bash
cd lambda-deploy

# Rebuild and push image
docker build -t llmeval:latest .
docker tag llmeval:latest \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/llmeval:latest
docker push \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/llmeval:latest

# Update function
aws lambda update-function-code \
    --function-name llmeval-monitor \
    --image-uri ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/llmeval:latest
```

### Update Configuration

```bash
# Redeploy stack
sam deploy --template-file template.yaml --stack-name llmeval-stack
```

## 🗑️ Cleanup/Deletion

### Delete Stack

```bash
aws cloudformation delete-stack --stack-name llmeval-stack

# Wait for deletion
aws cloudformation wait stack-delete-complete --stack-name llmeval-stack
```

### Delete S3 Bucket

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Empty bucket first
aws s3 rm s3://llmeval-database-${AWS_ACCOUNT_ID}/ --recursive

# Delete bucket
aws s3 rb s3://llmeval-database-${AWS_ACCOUNT_ID}/
```

### Delete ECR Repository

```bash
aws ecr delete-repository \
    --repository-name llmeval \
    --force
```

## 📝 Notes

### Lambda Limitations

- ⚠️ **15-minute timeout** - Maximum execution time
- ⚠️ **/tmp storage** - Only 512MB available
- ⚠️ **Database persistence** - Requires S3 for storage
- ⚠️ **Cold starts** - First invocation may be slower

### Best Practices

- ✅ Use S3 for database storage
- ✅ Enable CloudWatch alarms
- ✅ Monitor execution duration
- ✅ Keep database backups in S3
- ✅ Use secrets for API keys (consider AWS Secrets Manager)
- ✅ Tag resources for cost tracking

## 🆘 Support

### View Lambda Insights

```bash
# Get function configuration
aws lambda get-function --function-name llmeval-monitor

# Get function metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Duration \
    --dimensions Name=FunctionName,Value=llmeval-monitor \
    --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 86400 \
    --statistics Average,Maximum
```

### Useful Commands

```bash
# List all Lambda functions
aws lambda list-functions

# Get specific function info
aws lambda get-function --function-name llmeval-monitor

# View recent logs
aws logs tail /aws/lambda/llmeval-monitor --since 30m

# Invoke function synchronously
aws lambda invoke \
    --function-name llmeval-monitor \
    --invocation-type RequestResponse \
    --payload '{}' \
    --log-type Tail \
    response.json

# View invocation result
cat response.json | jq .
```

## 🎯 Next Steps

1. ✅ Deploy using `./deploy.sh`
2. ✅ Test with manual invocation
3. ✅ Check Discord for output
4. ✅ Monitor CloudWatch logs
5. ✅ Wait for scheduled runs (9 AM & 9 PM UTC)
6. ✅ Review S3 database backups

---

**Deployment Status:** Ready for production ✅
**Estimated Setup Time:** 10-15 minutes
**AWS Cost:** ~$2-3/month
**Maintenance:** Zero (fully automated)
