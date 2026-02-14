# Quick Start Guide: Enhanced LlmEval

## What's New? 🎉

Your LlmEval system now has **multi-dimensional scoring**, **adaptive thresholds**, and **diversity-aware selection**!

### Before vs After

| Feature | Before | After |
|---------|--------|-------|
| Scoring | Single 0-100 score | 5 dimensions + confidence |
| Thresholds | Fixed (60) | Adaptive (50-75) |
| Selection | Top 15 by score | Diverse batch (platforms, modalities) |
| Explainability | One number | Full breakdown |

## Running the System

### Basic Usage (No Changes!)

```bash
python run.py
```

Everything works automatically! The system will:
1. ✅ Migrate your database on first run
2. ✅ Request multi-dimensional scores from LLM
3. ✅ Apply adaptive thresholds
4. ✅ Enforce diversity constraints
5. ✅ Display enhanced Discord reports

### What You'll See in Discord

**Old Format:**
```
Score: 75/100
Platform: HUGGINGFACE
```

**New Format:**
```
Composite Score: 75/100
Platform: HUGGINGFACE

Multi-Dimensional Score:
• Relevance: 80/100
• Quality: 75/100
• Novelty: 70/100
• Evaluability: 80/100
• Impact: 65/100
• Confidence: 0.85
```

## Configuration Examples

### 1. Adjust Dimension Weights

**Want to prioritize novelty over quality?**

Edit `config.yaml`:
```yaml
filtering:
  scoring:
    dimension_weights:
      relevance: 0.30
      quality: 0.15      # Decreased
      novelty: 0.30      # Increased
      evaluability: 0.20
      impact: 0.05
      # Must sum to 1.0
```

### 2. Adjust Thresholds

**Too many/few results?**

Edit `config.yaml`:
```yaml
filtering:
  thresholds:
    default: 65              # Raise to get fewer, higher-quality results
    platform_specific:
      huggingface: 70        # Strict for high-volume platforms
      github: 60             # Lenient for lower-volume
```

### 3. Adjust Diversity

**Want more from each platform?**

Edit `config.yaml`:
```yaml
filtering:
  selection:
    diversity_constraints:
      max_per_platform: 10    # Up from 7
      max_per_modality: 10     # Up from 8
```

### 4. Enable Priority Queue

**Want urgency-based prioritization?**

Edit `config.yaml`:
```yaml
filtering:
  selection:
    use_priority_queue: true  # Change from false
```

## Monitoring Your System

### Check Dimension Scores

```bash
# View latest releases with full dimensions
sqlite3 data/releases.db "
SELECT
  title,
  composite_score,
  relevance_dim,
  quality_dim,
  novelty_dim,
  confidence
FROM releases
WHERE discovered_at > datetime('now', '-1 day')
ORDER BY composite_score DESC
LIMIT 5;
"
```

### Check Adaptive Thresholds

```bash
# View threshold adjustments in logs
tail -f data/monitor.log | grep "Dynamic threshold"
```

Example output:
```
Dynamic threshold: 65 (high volume: 45 candidates)
Dynamic threshold: 55 (low volume: 8 candidates)
```

### Check Diversity

```bash
# View diversity filtering decisions
tail -f data/monitor.log | grep "diversity"
```

Example output:
```
Diversity-filtered batch: 15 releases
  Platform distribution: {'huggingface': 6, 'github': 5, 'arxiv': 4}
  Modality distribution: {'language': 7, 'image': 5, 'multimodal': 3}
```

### View Full Report

```bash
# View latest JSON report with all dimension data
cat $(ls -t data/reports/*.json | head -1) | jq .
```

## Understanding Dimensions

### 1. Relevance (30% weight)
**What it measures:** How well this matches NEO's capabilities and interests
- **High (80-100):** Perfect match for NEO's domain
- **Medium (60-79):** Relevant and interesting
- **Low (40-59):** Somewhat relevant but not ideal

### 2. Quality (20% weight)
**What it measures:** Code quality, documentation, community metrics
- **High (80-100):** Well-documented, high-quality, active community
- **Medium (60-79):** Good documentation, decent quality
- **Low (40-59):** Basic documentation, acceptable quality

### 3. Novelty (25% weight)
**What it measures:** How cutting-edge and unique
- **High (80-100):** Breakthrough/SOTA, novel architecture
- **Medium (60-79):** Recent release, some novel aspects
- **Low (40-59):** Incremental improvement

### 4. Evaluability (20% weight)
**What it measures:** How easily NEO can test and benchmark
- **High (80-100):** Clear benchmarks, easy to test, public access
- **Medium (60-79):** Can be evaluated with some effort
- **Low (40-59):** Evaluation possible but challenging

### 5. Impact (5% weight)
**What it measures:** Expected value and community benefit
- **High (80-100):** High community impact, widely applicable
- **Medium (60-79):** Good potential impact
- **Low (40-59):** Moderate impact

### 6. Confidence (informational)
**What it measures:** How certain the LLM is about the evaluation
- **High (0.8-1.0):** Very confident, clear indicators
- **Medium (0.6-0.8):** Confident, good information
- **Low (0.3-0.5):** Uncertain, limited information

## Troubleshooting

### "Too many results sent"

1. **Raise thresholds:**
   ```yaml
   thresholds:
     default: 70  # Up from 60
   ```

2. **Stricter diversity:**
   ```yaml
   diversity_constraints:
     max_per_platform: 5  # Down from 7
   ```

### "Too few results sent"

1. **Lower thresholds:**
   ```yaml
   thresholds:
     default: 55  # Down from 60
   ```

2. **Disable adaptive thresholds:**
   ```yaml
   adaptive:
     enabled: false
   ```

### "Results not diverse enough"

1. **Stricter constraints:**
   ```yaml
   diversity_constraints:
     max_per_platform: 4     # Force more diversity
     max_per_modality: 5      # Ensure variety
     min_platforms: 3         # Require 3+ platforms
   ```

### "Wrong modality detected"

The system infers modality from text. If it's wrong, check the description/title for keywords. The system learns from:
- **Language:** "llm", "gpt", "text-generation", "language"
- **Image:** "diffusion", "image-generation", "vision"
- **Audio:** "speech", "audio", "tts", "whisper"
- **Video:** "video", "sora", "video-generation"
- **Multimodal:** "multimodal", "vision-language", "vlm"

## Advanced Usage

### Custom Weight Profiles

Create different profiles for different scenarios:

**Research-focused:**
```yaml
dimension_weights:
  relevance: 0.25
  quality: 0.20
  novelty: 0.40      # Prioritize novelty
  evaluability: 0.10
  impact: 0.05
```

**Production-focused:**
```yaml
dimension_weights:
  relevance: 0.30
  quality: 0.35      # Prioritize quality
  novelty: 0.15
  evaluability: 0.15
  impact: 0.05
```

### Platform-Specific Strategies

**High-volume platform (HuggingFace):**
- Higher threshold (65-70)
- Stricter quality requirements
- Lower max_per_platform

**Low-volume platform (Kaggle):**
- Lower threshold (55-60)
- More lenient selection
- Higher max_per_platform

## Migration from Old System

### First Run Checklist

✅ **Before running:**
1. Backup your database: `cp data/releases.db data/releases.db.backup`
2. Backup your config: `cp config.yaml config.yaml.backup`

✅ **First run:**
```bash
python run.py
```

✅ **Check migration:**
```bash
sqlite3 data/releases.db ".schema releases" | grep dim
# Should see: relevance_dim, quality_dim, etc.
```

✅ **Verify Discord output:**
- Look for "Multi-Dimensional Score" section in embeds
- Check for diversity in platform distribution

### Gradual Rollout

**Week 1:** Run with default settings, observe
- Monitor dimension scores in Discord
- Check diversity in batches
- Note any issues

**Week 2:** Tune weights if needed
- If too many low-quality: increase quality weight
- If missing novel items: increase novelty weight

**Week 3:** Enable priority queue
```yaml
use_priority_queue: true
```

**Week 4+:** Optimize and stabilize
- Fine-tune thresholds
- Adjust diversity constraints
- Monitor precision (% evaluated by NEO)

## FAQ

### Q: Will this cost more?
**A:** Yes, ~67% more LLM tokens per release (~$0.03 more per 50 releases with GPT-4). But much better quality!

### Q: Can I disable multi-dimensional scoring?
**A:** Not easily - it's the new foundation. You can adjust weights to effectively ignore dimensions (set weight to 0.0).

### Q: Does this work with my existing database?
**A:** Yes! Automatic migration on first run. Old releases won't have dimensions, new ones will.

### Q: Can I use the old single score?
**A:** The `relevance_score` column still stores the composite score. Use `composite_score` for clarity.

### Q: What if the LLM doesn't return dimensions?
**A:** The parser has default values (all 50s, confidence 0.5). The system won't crash.

### Q: How do I rollback?
**A:**
```bash
git checkout HEAD~1  # Revert code
cp data/releases.db.backup data/releases.db  # Restore DB
```

## Support

**Issues?** Check:
1. Logs: `tail -f data/monitor.log`
2. Database: `sqlite3 data/releases.db ".schema releases"`
3. Config: `python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"`
4. Verification: `python3 verify_implementation.py`

**Still stuck?** Check `IMPLEMENTATION_SUMMARY.md` for technical details.

## What's Next?

This implementation covers **Phases 1-3** of the enhancement plan:
- ✅ Multi-dimensional scoring
- ✅ Adaptive thresholds
- ✅ Diversity selection
- ✅ Priority queue

**Future phases** (not yet implemented):
- 🔜 **Phase 4:** Feedback loop & learning (auto-calibration based on NEO's actual evaluations)
- 🔜 **Phase 5:** Agent integration (resource-aware filtering, NEO state integration)

---

**Ready to go?** Run `python run.py` and watch the magic! 🚀
