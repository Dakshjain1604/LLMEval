# LlmEval Project Structure

## Root Directory

```
LlmEval/
├── 📄 Core Files
│   ├── run.py                          # Main entry point
│   ├── config.yaml                     # Configuration file
│   ├── requirements.txt                # Python dependencies
│   └── .env                            # API keys (not in git)
│
├── 📚 Documentation
│   ├── README.md                       # Project overview
│   ├── QUICK_START_GUIDE.md           # User guide for the enhanced system
│   ├── IMPLEMENTATION_SUMMARY.md      # Technical implementation details
│   ├── AWS_DEPLOYMENT_GUIDE.md        # Comprehensive AWS deployment guide
│   ├── AWS_QUICKSTART.md              # Quick AWS deployment guide
│   └── verify_implementation.py       # Verification script
│
├── 📁 Source Code (src/)
│   ├── main.py                         # Application orchestration
│   ├── database.py                     # SQLite database management
│   ├── llm_filter.py                  # Multi-dimensional LLM scoring
│   ├── discord_sender_v2.py           # Enhanced Discord integration
│   ├── report_generator.py            # Report generation
│   ├── report_cache.py                # Report caching system
│   ├── selection_optimizer.py         # Diversity-aware selection (NEW)
│   ├── priority_queue.py              # Priority queue system (NEW)
│   └── collectors/                    # Platform collectors
│       ├── base.py
│       ├── huggingface.py
│       ├── arxiv.py
│       ├── kaggle.py
│       └── github.py
│
├── 📁 Data (data/)
│   ├── releases.db                    # SQLite database
│   ├── monitor.log                    # Application logs
│   ├── cron.log                       # Cron execution logs
│   └── reports/                       # Generated reports (JSON, CSV, MD)
│
├── 📁 Deployment (deploy/)
│   └── ec2-quick-deploy.sh           # AWS EC2 deployment script
│
└── 📁 Virtual Environment (venv/)
    └── (Python packages)
```

## File Descriptions

### Core Files

| File | Purpose |
|------|---------|
| `run.py` | Entry point - runs the monitoring cycle |
| `config.yaml` | All configuration (platforms, LLM, filters, thresholds) |
| `requirements.txt` | Python package dependencies |
| `.env` | API keys and secrets (gitignored) |

### Documentation

| File | Purpose | Audience |
|------|---------|----------|
| `README.md` | Project overview and quick start | Everyone |
| `QUICK_START_GUIDE.md` | User guide for enhanced features | Users |
| `IMPLEMENTATION_SUMMARY.md` | Technical implementation details | Developers |
| `AWS_DEPLOYMENT_GUIDE.md` | Comprehensive AWS deployment (3 options) | DevOps |
| `AWS_QUICKSTART.md` | Quick EC2 deployment (15 min) | DevOps |
| `verify_implementation.py` | Verification script for setup | Everyone |

### Source Code Structure

```
src/
├── Core Application
│   ├── main.py                    # Orchestrates the monitoring cycle
│   ├── database.py                # Database operations, migrations
│   └── llm_filter.py             # Multi-dimensional scoring engine
│
├── Enhanced Features (Phase 1-3)
│   ├── selection_optimizer.py    # Diversity constraints, modality inference
│   └── priority_queue.py        # Urgency calculation, priority levels
│
├── Output & Reporting
│   ├── discord_sender_v2.py     # Enhanced Discord with dimension display
│   ├── report_generator.py      # JSON/CSV/MD report generation
│   └── report_cache.py          # SHA256-based duplicate prevention
│
└── Data Collection
    └── collectors/              # Platform-specific collectors
        ├── base.py              # Base collector class
        ├── huggingface.py      # HuggingFace models & datasets
        ├── arxiv.py            # Research papers
        ├── kaggle.py           # Kaggle datasets & models
        └── github.py           # GitHub repositories
```

## Key Features by File

### `llm_filter.py` (Enhanced)
- ✨ Multi-dimensional scoring (5 dimensions + confidence)
- 🎯 Adaptive thresholds (volume, platform, confidence-based)
- 🧮 Weighted composite score calculation
- 📊 Platform-specific threshold adjustment

### `selection_optimizer.py` (NEW)
- 🎨 Diversity constraints enforcement
- 🤖 Modality inference (language, image, audio, video, multimodal)
- 📋 Task type classification
- 🔍 Platform & modality distribution tracking

### `priority_queue.py` (NEW)
- 🏆 5-level priority system (CRITICAL → RESEARCH)
- ⚡ Urgency calculation (recency, novelty, impact, buzz)
- 📈 NEO state-aware batch sizing
- 🎯 Smart dequeuing logic

### `database.py` (Enhanced)
- 💾 19-column schema (11 original + 8 new)
- 🔄 Automatic migration system
- 📊 Dimension data storage
- 🗄️ Confidence and composite score tracking

## Configuration Files

### `config.yaml` Structure

```yaml
schedule:              # Cron schedule
llm:                   # LLM provider & model
platforms:             # Platform configs (HF, arXiv, Kaggle, GitHub)
neo_context:           # NEO's capabilities & limitations
filtering:             # Main filtering configuration
  ├── scoring:         # Dimension weights
  ├── thresholds:      # Adaptive thresholds
  └── selection:       # Diversity & priority queue
storage:               # Database & retention
```

### `.env` (API Keys)

```bash
DISCORD_WEBHOOK_URL=...
OPENROUTER_API_KEY=...
HUGGINGFACE_TOKEN=...
KAGGLE_USERNAME=...
KAGGLE_KEY=...
GITHUB_TOKEN=...
```

## Data Storage

### `data/releases.db` Schema

**Original Columns (11):**
- `id`, `platform`, `item_id`, `title`, `url`, `description`, `metadata`
- `discovered_at`, `relevance_score`, `filtered_out`, `sent_to_discord`

**New Columns (8):**
- `relevance_dim`, `quality_dim`, `novelty_dim`, `evaluability_dim`, `impact_dim`
- `confidence`, `composite_score`, `reasoning`

**Total: 19 columns**

### Logs

| File | Content |
|------|---------|
| `data/monitor.log` | Application logs (collectors, filters, Discord) |
| `data/cron.log` | Cron execution logs (start/end times, exit codes) |

### Reports

Generated in `data/reports/`:
- `releases_YYYYMMDD_HHMMSS.json` - Machine-readable
- `releases_YYYYMMDD_HHMMSS.csv` - Spreadsheet format
- `releases_YYYYMMDD_HHMMSS.md` - Human-readable markdown

## Deployment Structure

### `deploy/` Directory

```
deploy/
└── ec2-quick-deploy.sh    # Automated EC2 setup script
```

**Script Features:**
- ✅ System update & Python installation
- ✅ Virtual environment creation
- ✅ Dependency installation
- ✅ Environment variable setup
- ✅ Cron job configuration
- ✅ Run script creation

## File Count Summary

```
Documentation:    6 files
Core Files:       4 files
Source Code:     11 files
Deployment:       1 file
Total:          ~22 files (excluding venv, data, logs)
```

## Removed Files (Cleaned Up)

The following files were removed as unnecessary:
- ❌ `CACHE_GUIDE.md` - Old feature-specific doc
- ❌ `CONFIG_GUIDE.md` - Superseded by QUICK_START_GUIDE
- ❌ `ENHANCED_REPORT_FEATURES.md` - Old feature doc
- ❌ `IMPROVEMENTS.md` - Old notes
- ❌ `OPENROUTER_GUIDE.md` - Integrated into main docs
- ❌ `QUICKSTART.md` - Superseded by QUICK_START_GUIDE
- ❌ `QUICK_REFERENCE.md` - Superseded by AWS_QUICKSTART
- ❌ `SUMMARY.md` - Old summary
- ❌ `WHAT_TO_CONFIGURE.md` - Integrated into guides
- ❌ `cache_manager.py` - Utility script
- ❌ `install_cron.sh` - Superseded by deploy script
- ❌ `setup.sh` - Old setup script
- ❌ `test_cache.py` - Test file
- ❌ `test_run.py` - Test file

## Quick Navigation

| Task | File to Check |
|------|---------------|
| Run the system | `run.py` |
| Configure settings | `config.yaml` |
| Add API keys | `.env` |
| Deploy to AWS | `AWS_QUICKSTART.md` |
| Understand features | `QUICK_START_GUIDE.md` |
| Technical details | `IMPLEMENTATION_SUMMARY.md` |
| Verify setup | `verify_implementation.py` |
| Check logs | `data/monitor.log` |
| View database | `sqlite3 data/releases.db` |

## Clean Project Structure

The root directory is now clean and organized:
- ✅ Only essential files
- ✅ Clear documentation structure
- ✅ Logical code organization
- ✅ Comprehensive deployment guides
- ✅ All unnecessary files removed

---

**Last Updated:** 2026-02-14
**Project Version:** v2.0 (Enhanced with Multi-Dimensional Scoring)
