# AI/ML Release Monitor for NEO

An automated system that monitors AI/ML platforms for new models, datasets, and research papers, filters them using LLM intelligence, and sends curated results to Discord.

## Features

- 🔍 **Multi-Platform Monitoring**
  - HuggingFace (models & datasets)
  - arXiv (research papers)
  - Kaggle (datasets & models)
  - GitHub (AI/ML repositories)

- 🤖 **LLM-Powered Filtering**
  - Uses Claude/GPT to evaluate relevance
  - Scores each release (0-100)
  - Filters out noise automatically
  - Considers NEO agent's capabilities

- 💬 **Discord Integration**
  - Rich embed messages
  - Automatic notifications
  - Summary statistics
  - Configurable webhooks

- 📊 **Smart Tracking**
  - SQLite database for deduplication
  - Tracks all discoveries
  - Prevents duplicate notifications
  - **Report-level caching** (NEW!)
  - Prevents duplicate report spam
  - Automatic cleanup

- ⏰ **Automated Execution**
  - Cronjob support (every 12 hours)
  - Configurable schedule
  - Comprehensive logging

## Quick Start

### 1. Installation

```bash
# Clone or copy the project
cd /root/LlmEval

# Run setup script
chmod +x setup.sh
./setup.sh
```

### 2. Configuration

Edit `.env` file with your API keys:

```bash
nano .env
```

Required:
- `DISCORD_WEBHOOK_URL` - Your Discord webhook URL
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` - For LLM filtering

Optional (for higher rate limits):
- `HUGGINGFACE_TOKEN`
- `GITHUB_TOKEN`
- `KAGGLE_USERNAME` and `KAGGLE_KEY`

### 3. Customize Settings

Edit `config.yaml` to customize:
- Platform settings
- Filtering criteria
- NEO agent context
- Schedule

```bash
nano config.yaml
```

### 4. Test Run

```bash
source venv/bin/activate
python run.py
```

### 5. Install Cronjob

```bash
./install_cron.sh
```

The monitor will now run automatically every 12 hours (or as configured).

## Configuration Guide

### Platform Settings

Each platform can be enabled/disabled independently:

```yaml
platforms:
  huggingface:
    enabled: true
    check_models: true
    check_datasets: true
    min_downloads: 100
    priority_tags:
      - "text-generation"
      - "text-classification"

  arxiv:
    enabled: true
    categories:
      - "cs.AI"
      - "cs.LG"
    keywords:
      - "language model"
      - "benchmark"
```

### Filtering Criteria

Adjust LLM filtering behavior:

```yaml
filtering:
  min_relevance_score: 60  # Only send items scoring >= 60
  max_items_per_run: 15    # Max items per notification
  priority_keywords:
    - "sota"
    - "benchmark"
  exclude_keywords:
    - "deprecated"
```

### NEO Context

Customize NEO agent description for better filtering:

```yaml
neo_context:
  description: |
    NEO is an autonomous AI/ML agent that can...

  capabilities:
    - "Can run models locally (up to ~70B parameters)"
    - "Has access to common ML frameworks"

  limitations:
    - "Cannot train large models from scratch"
    - "Limited GPU resources"
```

## Project Structure

```
/root/LlmEval/
├── config.yaml          # Main configuration
├── .env                 # API keys (create from .env.example)
├── requirements.txt     # Python dependencies
├── run.py              # Main entry point
├── setup.sh            # Installation script
├── install_cron.sh     # Cronjob installer
├── src/
│   ├── main.py         # Application core
│   ├── database.py     # SQLite management
│   ├── llm_filter.py   # LLM filtering logic
│   ├── discord_sender.py # Discord integration
│   └── collectors/     # Platform collectors
│       ├── base.py
│       ├── huggingface.py
│       ├── arxiv.py
│       ├── kaggle.py
│       └── github.py
└── data/               # Database and logs
    ├── releases.db
    ├── monitor.log
    └── cron.log
```

## Usage

### Manual Run

```bash
source venv/bin/activate
python run.py
```

### View Logs

```bash
# Application logs
tail -f data/monitor.log

# Cronjob logs
tail -f data/cron.log
```

### Database Stats

```bash
source venv/bin/activate
python -c "from src.database import ReleaseDatabase; db = ReleaseDatabase('data/releases.db'); print(db.get_stats())"
```

### Dry Run (Test Without Sending)

Set in `config.yaml`:

```yaml
discord:
  dry_run: true
```

## Discord Output

The system sends rich embed messages to Discord with:

- ⭐ High-priority releases (score >= 80)
- 📦 Standard releases (score 60-79)
- Platform information
- Relevance scores
- Metadata (downloads, stars, authors, etc.)
- Direct links to resources

Example:

```
🤖 NEO AI/ML Release Monitor - 5 new releases found

⭐ meta-llama/Llama-4-70B
Platform: HuggingFace | Type: Model | Score: 95/100
Downloads: 1,234,567 | Likes: 890
[View Model →]

📦 New Benchmark Dataset for LLM Evaluation
Platform: arXiv | Score: 72/100
Authors: Smith et al. +4 more
[View Paper →]
```

## Report Caching (NEW!)

The system now includes intelligent report caching to prevent duplicate reports:

### Features

- **Duplicate Detection**: Automatically detects and prevents duplicate report combinations
- **Cache Management**: Track all sent reports with metadata
- **Smart Cleanup**: Automatic cleanup based on retention settings

### Cache Management

```bash
# View cache statistics
python cache_manager.py stats

# Show recent reports
python cache_manager.py recent 7

# Compare database and cache
python cache_manager.py compare

# Clean up old cache
python cache_manager.py cleanup 30
```

**See `CACHE_GUIDE.md` for complete documentation.**

## Troubleshooting

### No releases found

- Check platform API keys are correct
- Verify platforms are enabled in config.yaml
- Check `data/monitor.log` for errors
- Reduce `min_downloads` or `min_stars` thresholds

### LLM filtering errors

- Verify API key is correct in `.env`
- Check LLM provider is set correctly in config.yaml
- Monitor API rate limits

### Discord webhook not working

- Verify webhook URL is correct
- Test webhook manually: `curl -X POST -H "Content-Type: application/json" -d '{"content":"test"}' YOUR_WEBHOOK_URL`
- Check Discord server permissions

### Cronjob not running

- Check crontab: `crontab -l`
- Verify paths are absolute
- Check logs: `tail -f data/cron.log`
- Ensure virtual environment path is correct

## Advanced Usage

### Custom Collectors

Add new platforms by creating a collector in `src/collectors/`:

```python
from .base import Collector, Release

class CustomCollector(Collector):
    def collect(self) -> List[Release]:
        # Your collection logic
        pass
```

### Custom Filtering Logic

Modify `src/llm_filter.py` to customize how releases are scored.

### Multiple Configurations

Run with different config files:

```bash
python run.py config_experimental.yaml
```

## Maintenance

### Clean Database

```bash
source venv/bin/activate
python -c "from src.database import ReleaseDatabase; db = ReleaseDatabase('data/releases.db'); db.cleanup_old_entries(7)"
```

### Reset Database

```bash
rm data/releases.db
python run.py  # Will recreate database
```

### Update Dependencies

```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## Contributing

This tool is designed for NEO's autonomous evaluation system. Customize it to fit your workflow!

## License

MIT License - Feel free to modify and adapt for your needs.

## Support

For issues or questions:
1. Check logs: `data/monitor.log`
2. Verify configuration
3. Test platforms individually
4. Check API rate limits

---

**Built for NEO** 🤖 - Autonomous AI/ML Agent
