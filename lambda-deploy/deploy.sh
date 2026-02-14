#!/bin/bash
# LlmEval Lambda Deployment Script

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         LlmEval AWS Lambda Deployment Script                     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo -e "${GREEN}[1/8] Checking prerequisites...${NC}"

if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ AWS CLI not found. Please install it first.${NC}"
    echo "Install: https://aws.amazon.com/cli/"
    exit 1
fi
echo -e "  ✓ AWS CLI found"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found. Please install it first.${NC}"
    echo "Install: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "  ✓ Docker found"

if ! command -v sam &> /dev/null; then
    echo -e "${YELLOW}⚠  AWS SAM CLI not found. Installing...${NC}"
    pip install aws-sam-cli || {
        echo -e "${RED}✗ Failed to install AWS SAM CLI${NC}"
        exit 1
    }
fi
echo -e "  ✓ AWS SAM CLI found"

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}✗ Unable to get AWS Account ID. Please configure AWS credentials.${NC}"
    echo "Run: aws configure"
    exit 1
fi

AWS_REGION=$(aws configure get region || echo "us-east-1")
echo -e "  ✓ AWS Account ID: ${AWS_ACCOUNT_ID}"
echo -e "  ✓ AWS Region: ${AWS_REGION}"

# Prepare files
echo ""
echo -e "${GREEN}[2/8] Preparing deployment files...${NC}"

# Copy necessary files to lambda-deploy
cd "$(dirname "$0")"

if [ ! -f "../config.yaml" ]; then
    echo -e "${RED}✗ config.yaml not found in parent directory${NC}"
    exit 1
fi

echo -e "  ✓ Copying files..."
cp ../config.yaml .
cp ../requirements.txt .
cp -r ../src .

# Create ECR repository
echo ""
echo -e "${GREEN}[3/8] Creating ECR repository...${NC}"

if ! aws ecr describe-repositories --repository-names llmeval --region ${AWS_REGION} &>/dev/null; then
    aws ecr create-repository \
        --repository-name llmeval \
        --region ${AWS_REGION} \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256
    echo -e "  ✓ ECR repository created"
else
    echo -e "  ✓ ECR repository already exists"
fi

# Login to ECR
echo ""
echo -e "${GREEN}[4/8] Logging in to ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
echo -e "  ✓ Logged in to ECR"

# Build Docker image
echo ""
echo -e "${GREEN}[5/8] Building Docker image...${NC}"
docker build -t llmeval:latest .
echo -e "  ✓ Docker image built"

# Tag and push image
echo ""
echo -e "${GREEN}[6/8] Pushing image to ECR...${NC}"
docker tag llmeval:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/llmeval:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/llmeval:latest
echo -e "  ✓ Image pushed to ECR"

# Collect parameters
echo ""
echo -e "${GREEN}[7/8] Setting up parameters...${NC}"

# Check if .env file exists in parent directory
if [ -f "../.env" ]; then
    echo -e "  ${YELLOW}Loading parameters from .env file...${NC}"
    source ../.env
fi

# Prompt for required parameters
echo ""
echo -e "${YELLOW}Please provide deployment parameters:${NC}"
echo ""

read -p "Discord Webhook URL [$DISCORD_WEBHOOK_URL]: " input
DISCORD_WEBHOOK_URL="${input:-$DISCORD_WEBHOOK_URL}"

read -sp "OpenRouter API Key [$OPENROUTER_API_KEY]: " input
echo ""
OPENROUTER_API_KEY="${input:-$OPENROUTER_API_KEY}"

read -p "HuggingFace Token (optional) [$HUGGINGFACE_TOKEN]: " input
HUGGINGFACE_TOKEN="${input:-$HUGGINGFACE_TOKEN}"

read -p "Kaggle Username (optional) [$KAGGLE_USERNAME]: " input
KAGGLE_USERNAME="${input:-$KAGGLE_USERNAME}"

read -sp "Kaggle API Key (optional) [$KAGGLE_KEY]: " input
echo ""
KAGGLE_KEY="${input:-$KAGGLE_KEY}"

read -sp "GitHub Token (optional) [$GITHUB_TOKEN]: " input
echo ""
GITHUB_TOKEN="${input:-$GITHUB_TOKEN}"

# Validate required parameters
if [ -z "$DISCORD_WEBHOOK_URL" ] || [ -z "$OPENROUTER_API_KEY" ]; then
    echo -e "${RED}✗ Required parameters missing!${NC}"
    echo "Discord Webhook URL and OpenRouter API Key are required."
    exit 1
fi

# Deploy with SAM
echo ""
echo -e "${GREEN}[8/8] Deploying Lambda function with SAM...${NC}"

sam deploy \
    --template-file template.yaml \
    --stack-name llmeval-stack \
    --region ${AWS_REGION} \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        DiscordWebhookUrl="${DISCORD_WEBHOOK_URL}" \
        OpenRouterApiKey="${OPENROUTER_API_KEY}" \
        HuggingFaceToken="${HUGGINGFACE_TOKEN}" \
        KaggleUsername="${KAGGLE_USERNAME}" \
        KaggleKey="${KAGGLE_KEY}" \
        GithubToken="${GITHUB_TOKEN}" \
    --no-confirm-changeset \
    --resolve-s3 \
    || {
        echo -e "${RED}✗ SAM deployment failed${NC}"
        exit 1
    }

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   Deployment Successful! 🎉                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get stack outputs
echo -e "${GREEN}Stack Outputs:${NC}"
aws cloudformation describe-stacks \
    --stack-name llmeval-stack \
    --region ${AWS_REGION} \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo ""
echo -e "1. ${YELLOW}Test the function manually:${NC}"
echo "   aws lambda invoke --function-name llmeval-monitor --payload '{}' response.json"
echo ""
echo -e "2. ${YELLOW}View logs:${NC}"
echo "   aws logs tail /aws/lambda/llmeval-monitor --follow"
echo ""
echo -e "3. ${YELLOW}Check S3 bucket for database:${NC}"
echo "   aws s3 ls s3://llmeval-database-${AWS_ACCOUNT_ID}/"
echo ""
echo -e "4. ${YELLOW}Schedule:${NC}"
echo "   - Morning: 9:00 AM UTC (every day)"
echo "   - Evening: 9:00 PM UTC (every day)"
echo ""
echo -e "${GREEN}Cost Estimate:${NC}"
echo "  - Lambda: ~\$1-2/month (2 runs/day × 10 min)"
echo "  - S3: ~\$0.50/month (database storage)"
echo "  - CloudWatch: ~\$0.50/month (logs)"
echo "  - Total AWS: ~\$2-3/month"
echo "  - Plus LLM API costs: ~\$2-5/month"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
