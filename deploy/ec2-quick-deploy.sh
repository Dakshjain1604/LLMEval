#!/bin/bash
# LlmEval Quick Deployment Script for AWS EC2
# Run this on a fresh Ubuntu 22.04 EC2 instance

set -e

echo "========================================="
echo "LlmEval EC2 Deployment Script"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running as ubuntu user
if [ "$(whoami)" != "ubuntu" ]; then
    echo -e "${YELLOW}Warning: This script should be run as 'ubuntu' user${NC}"
    echo "Current user: $(whoami)"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Update system
echo -e "${GREEN}[1/8] Updating system...${NC}"
sudo apt update && sudo apt upgrade -y

# Step 2: Install dependencies
echo -e "${GREEN}[2/8] Installing Python and dependencies...${NC}"
sudo apt install -y python3.12 python3.12-venv python3-pip git curl wget

# Step 3: Setup application directory
echo -e "${GREEN}[3/8] Setting up application directory...${NC}"
cd /home/ubuntu

if [ -d "LlmEval" ]; then
    echo -e "${YELLOW}LlmEval directory already exists. Backing up...${NC}"
    mv LlmEval LlmEval.backup.$(date +%Y%m%d_%H%M%S)
fi

# Option 1: Clone from git (if repository exists)
# git clone https://github.com/YOUR_USERNAME/LlmEval.git

# Option 2: Upload files manually (recommended for now)
echo -e "${YELLOW}Please upload your LlmEval files to /home/ubuntu/LlmEval${NC}"
echo "You can use: scp -r /root/LlmEval ubuntu@YOUR_IP:~/"
echo ""
read -p "Press Enter when files are uploaded..."

if [ ! -d "LlmEval" ]; then
    echo -e "${RED}Error: LlmEval directory not found!${NC}"
    exit 1
fi

cd LlmEval

# Step 4: Create virtual environment
echo -e "${GREEN}[4/8] Creating virtual environment...${NC}"
python3.12 -m venv venv

# Step 5: Install Python packages
echo -e "${GREEN}[5/8] Installing Python packages...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Step 6: Setup environment variables
echo -e "${GREEN}[6/8] Setting up environment variables...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cat > .env << 'EOL'
# Discord Webhook
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID_HERE

# LLM API Keys
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE

# HuggingFace (optional)
HUGGINGFACE_TOKEN=hf_YOUR_TOKEN_HERE

# Kaggle (optional)
KAGGLE_USERNAME=your_username
KAGGLE_KEY=your_kaggle_key

# GitHub (optional - note: your account may be suspended)
GITHUB_TOKEN=github_pat_YOUR_TOKEN_HERE
EOL

    echo -e "${RED}IMPORTANT: Edit .env file with your actual API keys!${NC}"
    echo "Run: nano .env"
    echo ""
    read -p "Press Enter when .env is configured..."
fi

# Step 7: Create run script
echo -e "${GREEN}[7/8] Creating run script...${NC}"

cat > run_monitor.sh << 'EOF'
#!/bin/bash
# LlmEval execution script

# Set working directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Create logs directory
mkdir -p data

# Run monitor with logging
echo "=========================================" >> data/cron.log
echo "Started at: $(date)" >> data/cron.log
echo "=========================================" >> data/cron.log

python run.py >> data/cron.log 2>&1

EXIT_CODE=$?

echo "Finished at: $(date)" >> data/cron.log
echo "Exit code: $EXIT_CODE" >> data/cron.log
echo "" >> data/cron.log

exit $EXIT_CODE
EOF

chmod +x run_monitor.sh

# Step 8: Setup cron job
echo -e "${GREEN}[8/8] Setting up cron job...${NC}"

# Remove existing cron jobs for llmeval
crontab -l 2>/dev/null | grep -v "run_monitor.sh" | crontab - 2>/dev/null || true

# Add new cron jobs (9 AM and 9 PM UTC)
(crontab -l 2>/dev/null; echo "0 9 * * * /home/ubuntu/LlmEval/run_monitor.sh") | crontab -
(crontab -l 2>/dev/null; echo "0 21 * * * /home/ubuntu/LlmEval/run_monitor.sh") | crontab -

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "${YELLOW}Cron schedule:${NC}"
crontab -l | grep run_monitor
echo ""
echo -e "${YELLOW}Configuration files:${NC}"
echo "  • Application: /home/ubuntu/LlmEval"
echo "  • Environment: /home/ubuntu/LlmEval/.env"
echo "  • Config: /home/ubuntu/LlmEval/config.yaml"
echo "  • Run script: /home/ubuntu/LlmEval/run_monitor.sh"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Edit .env if not done already:"
echo "     nano .env"
echo ""
echo "  2. Test run manually:"
echo "     cd /home/ubuntu/LlmEval"
echo "     ./run_monitor.sh"
echo ""
echo "  3. Check logs:"
echo "     tail -f data/cron.log"
echo "     tail -f data/monitor.log"
echo ""
echo "  4. Monitor cron:"
echo "     grep CRON /var/log/syslog | tail -20"
echo ""
echo -e "${GREEN}System will run automatically at 9 AM and 9 PM UTC${NC}"
echo ""
