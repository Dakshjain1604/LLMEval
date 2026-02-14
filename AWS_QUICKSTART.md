# AWS Quick Start Guide for LlmEval

## TL;DR - Deploy in 15 Minutes

**Easiest Method: EC2 with Ubuntu**

```bash
# 1. Launch EC2 instance (t3.micro, Ubuntu 22.04)
# 2. SSH into instance
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# 3. Upload your LlmEval folder
# On your local machine:
scp -r -i your-key.pem /root/LlmEval ubuntu@YOUR_EC2_IP:~/

# 4. SSH back in and run deployment script
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
chmod +x ~/LlmEval/deploy/ec2-quick-deploy.sh
~/LlmEval/deploy/ec2-quick-deploy.sh

# 5. Done! System will run every 12 hours
```

---

## Step-by-Step: EC2 Deployment

### 1. Launch EC2 Instance

**Via AWS Console:**
1. Go to [AWS EC2 Console](https://console.aws.amazon.com/ec2/)
2. Click "Launch Instance"
3. **Name**: LlmEval
4. **AMI**: Ubuntu Server 22.04 LTS (Free tier eligible)
5. **Instance type**: t3.micro (1 vCPU, 1 GB RAM) - $3.50/month
6. **Key pair**: Create new or select existing
7. **Security group**:
   - Allow SSH (port 22) from your IP
   - Allow HTTPS outbound (default)
8. **Storage**: 10-20 GB gp3
9. Click "Launch Instance"

### 2. Connect to Instance

```bash
# Make key private
chmod 400 your-key.pem

# Connect via SSH
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP

# You should see: ubuntu@ip-xxx-xxx-xxx-xxx:~$
```

### 3. Upload Application

**Option A: SCP (Recommended)**
```bash
# On your LOCAL machine (where LlmEval is):
scp -r -i your-key.pem /root/LlmEval ubuntu@YOUR_EC2_IP:~/
```

**Option B: Git**
```bash
# On EC2 instance:
git clone https://github.com/YOUR_USERNAME/LlmEval.git
```

### 4. Run Deployment Script

```bash
# On EC2 instance:
cd ~/LlmEval
chmod +x deploy/ec2-quick-deploy.sh
./deploy/ec2-quick-deploy.sh
```

The script will:
- ✅ Install Python 3.12
- ✅ Create virtual environment
- ✅ Install dependencies
- ✅ Create run script
- ✅ Setup cron jobs (9 AM & 9 PM UTC)

### 5. Configure API Keys

```bash
# Edit .env file
nano ~/.env

# Add your keys:
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
HUGGINGFACE_TOKEN=hf_YOUR_TOKEN_HERE
KAGGLE_USERNAME=your_username
KAGGLE_KEY=your_key_here

# Save: Ctrl+O, Enter, Ctrl+X
```

### 6. Test Run

```bash
cd ~/LlmEval
./run_monitor.sh

# Watch logs
tail -f data/cron.log
```

### 7. Verify Cron Setup

```bash
# Check cron schedule
crontab -l

# Should show:
# 0 9 * * * /home/ubuntu/LlmEval/run_monitor.sh
# 0 21 * * * /home/ubuntu/LlmEval/run_monitor.sh

# Check cron is running
sudo systemctl status cron
```

---

## Monitoring & Maintenance

### Check Logs

```bash
# Application logs
tail -f ~/LlmEval/data/monitor.log

# Cron execution logs
tail -f ~/LlmEval/data/cron.log

# System cron logs
grep CRON /var/log/syslog | tail -20
```

### Check Database

```bash
cd ~/LlmEval
source venv/bin/activate
python3 -c "from src.database import ReleaseDatabase; db = ReleaseDatabase('data/releases.db'); print(db.get_stats())"
```

### Manual Run

```bash
cd ~/LlmEval
./run_monitor.sh
```

### Update Application

```bash
cd ~/LlmEval
git pull  # If using git
# OR upload new files via scp
./run_monitor.sh  # Test new version
```

---

## Cost Breakdown

**Monthly Costs:**
- EC2 t3.micro: $3.50/month
- EBS 10GB storage: $1.00/month
- Data transfer: $0.50/month
- **AWS Total: ~$5/month**

Plus LLM API costs: ~$2-5/month

**Grand Total: $7-10/month**

---

## Troubleshooting

### Cron not running?
```bash
# Check cron service
sudo systemctl status cron

# Restart cron
sudo systemctl restart cron

# Check for errors
grep CRON /var/log/syslog | grep error
```

### Virtual environment issues?
```bash
cd ~/LlmEval
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### API errors?
```bash
# Verify environment variables
cat .env

# Test API keys
source venv/bin/activate
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Keys loaded:', bool(os.getenv('OPENROUTER_API_KEY')))"
```

### Out of disk space?
```bash
# Check usage
df -h

# Clean old logs
cd ~/LlmEval/data
rm -f *.log.1 *.log.2 *.log.3

# Clean old reports
find data/reports -name "*.json" -mtime +30 -delete
```

---

## Security Best Practices

### 1. Restrict SSH Access
```bash
# Edit security group to only allow your IP
# AWS Console → EC2 → Security Groups → Edit inbound rules
# SSH (22): My IP
```

### 2. Setup Automatic Security Updates
```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 3. Use IAM Roles (Advanced)
Instead of storing API keys in .env, use AWS Secrets Manager:

```bash
# Store secrets
aws secretsmanager create-secret \
  --name llmeval/keys \
  --secret-string '{"OPENROUTER_API_KEY":"xxx"}'

# Retrieve in code
import boto3
secrets = boto3.client('secretsmanager')
secret = secrets.get_secret_value(SecretId='llmeval/keys')
```

---

## Backup & Recovery

### Setup Daily Database Backup

```bash
# Create backup script
cat > ~/backup_llmeval.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
mkdir -p $BACKUP_DIR
cp /home/ubuntu/LlmEval/data/releases.db \
   $BACKUP_DIR/releases-$(date +%Y%m%d).db
# Keep only last 7 days
find $BACKUP_DIR -name "releases-*.db" -mtime +7 -delete
EOF

chmod +x ~/backup_llmeval.sh

# Add to cron (daily at 3 AM)
(crontab -l; echo "0 3 * * * /home/ubuntu/backup_llmeval.sh") | crontab -
```

### Restore from Backup

```bash
# Stop current operations
# (wait for any running process to finish)

# Restore database
cp ~/backups/releases-20260214.db ~/LlmEval/data/releases.db

# Test
cd ~/LlmEval && ./run_monitor.sh
```

---

## Stopping & Starting

### Stop EC2 (Save Money)

```bash
# Stop instance (via console or CLI)
aws ec2 stop-instances --instance-ids i-YOUR_INSTANCE_ID

# Costs while stopped: Only EBS storage (~$1/month)
# Cron won't run while stopped
```

### Start EC2

```bash
aws ec2 start-instances --instance-ids i-YOUR_INSTANCE_ID

# Note: Public IP may change! Use Elastic IP if you need static IP
```

### Terminate EC2 (Delete Completely)

```bash
# ⚠️ WARNING: This deletes everything!
# Backup first: scp -r ubuntu@YOUR_IP:~/LlmEval ./backup/

aws ec2 terminate-instances --instance-ids i-YOUR_INSTANCE_ID
```

---

## Alternative: Lambda Deployment

If you want serverless (no EC2), see `AWS_DEPLOYMENT_GUIDE.md` Option 1.

**Pros:**
- Pay per execution only
- No server maintenance
- Auto-scaling

**Cons:**
- 15-minute timeout limit
- More complex setup
- /tmp storage limitations

---

## Getting Help

1. **Check logs**: `tail -f ~/LlmEval/data/monitor.log`
2. **Verify cron**: `crontab -l`
3. **Test manually**: `cd ~/LlmEval && ./run_monitor.sh`
4. **Check system**: `df -h && free -h`

**Still stuck?** Check the comprehensive guide: `AWS_DEPLOYMENT_GUIDE.md`

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `./run_monitor.sh` | Run manually |
| `tail -f data/monitor.log` | Watch logs |
| `crontab -l` | View cron schedule |
| `crontab -e` | Edit cron schedule |
| `grep CRON /var/log/syslog` | View cron execution history |
| `source venv/bin/activate` | Activate Python environment |
| `df -h` | Check disk space |
| `free -h` | Check memory |
| `htop` | System monitor (install: `sudo apt install htop`) |

---

**Ready to deploy?** Follow steps 1-7 above and you'll be running in 15 minutes! 🚀

**Questions?** Read the full guide: `AWS_DEPLOYMENT_GUIDE.md`
