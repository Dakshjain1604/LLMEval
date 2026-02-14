"""Main application for AI/ML Release Monitor."""

import logging
import sys
import yaml
from pathlib import Path
from typing import List
from datetime import datetime
import os
from dotenv import load_dotenv

from .database import ReleaseDatabase
from .collectors import (
    HuggingFaceCollector,
    ArxivCollector,
    KaggleCollector,
    GitHubCollector,
    Release
)
from .llm_filter import LLMFilter
from .discord_sender_v2 import EnhancedDiscordSender
from .report_generator import ReportGenerator
from .report_cache import ReportCache
from .selection_optimizer import SelectionOptimizer
from .priority_queue import PriorityQueue

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/monitor.log')
    ]
)
logger = logging.getLogger(__name__)


class ReleaseMonitor:
    """Main application for monitoring AI/ML releases."""

    def __init__(self, config_path: str = 'config.yaml'):
        self.config = self._load_config(config_path)
        self._load_env()
        self._init_components()

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            logger.error(f"Config file not found: {config_path}")
            sys.exit(1)

        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        return config

    def _load_env(self):
        """Load environment variables from .env file."""
        load_dotenv()

        # Override config with environment variables
        if os.getenv('DISCORD_WEBHOOK_URL'):
            self.config.setdefault('discord', {})['webhook_url'] = os.getenv('DISCORD_WEBHOOK_URL')

        if os.getenv('ANTHROPIC_API_KEY'):
            self.config.setdefault('llm', {})['api_key'] = os.getenv('ANTHROPIC_API_KEY')

        if os.getenv('OPENAI_API_KEY'):
            self.config.setdefault('llm', {})['api_key'] = os.getenv('OPENAI_API_KEY')

        if os.getenv('OPENROUTER_API_KEY'):
            self.config.setdefault('llm', {})['api_key'] = os.getenv('OPENROUTER_API_KEY')

        if os.getenv('HUGGINGFACE_TOKEN'):
            os.environ['HF_TOKEN'] = os.getenv('HUGGINGFACE_TOKEN')

        if os.getenv('GITHUB_TOKEN'):
            self.config.setdefault('platforms', {}).setdefault('github', {})['token'] = os.getenv('GITHUB_TOKEN')

        if os.getenv('KAGGLE_USERNAME'):
            self.config.setdefault('platforms', {}).setdefault('kaggle', {})['username'] = os.getenv('KAGGLE_USERNAME')

        if os.getenv('KAGGLE_KEY'):
            self.config.setdefault('platforms', {}).setdefault('kaggle', {})['api_key'] = os.getenv('KAGGLE_KEY')

    def _init_components(self):
        """Initialize application components."""
        # Create data directory
        Path('data').mkdir(exist_ok=True)

        # Initialize database
        db_path = self.config.get('storage', {}).get('database', 'data/releases.db')
        self.db = ReleaseDatabase(db_path)

        # Initialize collectors
        self.collectors = []
        if self.config.get('platforms', {}).get('huggingface', {}).get('enabled', False):
            self.collectors.append(HuggingFaceCollector(self.config))
        if self.config.get('platforms', {}).get('arxiv', {}).get('enabled', False):
            self.collectors.append(ArxivCollector(self.config))
        if self.config.get('platforms', {}).get('kaggle', {}).get('enabled', False):
            self.collectors.append(KaggleCollector(self.config))
        if self.config.get('platforms', {}).get('github', {}).get('enabled', False):
            self.collectors.append(GitHubCollector(self.config))

        # Initialize LLM filter
        self.filter = LLMFilter(self.config)

        # Initialize Discord sender (Enhanced version)
        self.discord = EnhancedDiscordSender(self.config)

        # Initialize report generator
        self.report_gen = ReportGenerator()

        # Initialize report cache
        self.report_cache = ReportCache(db_path)

        # Initialize selection optimizer
        self.selection_optimizer = SelectionOptimizer(self.config)

        # Initialize priority queue
        self.priority_queue = PriorityQueue(self.config)

        logger.info(f"Initialized with {len(self.collectors)} collectors")

    def run(self):
        """Run the monitoring cycle."""
        logger.info("=" * 60)
        logger.info("Starting AI/ML Release Monitor")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        try:
            # Step 1: Collect releases from all platforms
            all_releases = self._collect_releases()

            # Step 2: Filter out already seen releases
            new_releases = self._filter_new_releases(all_releases)

            if not new_releases:
                logger.info("No new releases found")
                self._send_summary()
                return

            # Step 3: Filter releases using LLM
            filtered_releases = self._llm_filter(new_releases)

            # Step 4: Store results in database
            self._store_releases(filtered_releases)

            # Step 5: Send to Discord
            self._send_to_discord()

            # Step 6: Cleanup old entries
            self._cleanup()

            # Step 7: Send summary
            self._send_summary()

            logger.info("=" * 60)
            logger.info("Monitor cycle completed successfully")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error during monitor cycle: {e}", exc_info=True)
            raise

    def _collect_releases(self) -> List[Release]:
        """Collect releases from all enabled platforms."""
        logger.info("Collecting releases from platforms...")

        all_releases = []
        for collector in self.collectors:
            try:
                releases = collector.collect()
                all_releases.extend(releases)
            except Exception as e:
                logger.error(f"Error in {collector.__class__.__name__}: {e}")
                continue

        logger.info(f"Collected {len(all_releases)} total releases")
        return all_releases

    def _filter_new_releases(self, releases: List[Release]) -> List[Release]:
        """Filter out releases that have been seen before."""
        new_releases = []

        for release in releases:
            if not self.db.is_seen(release.platform, release.item_id):
                new_releases.append(release)

        logger.info(f"Found {len(new_releases)} new releases (filtered {len(releases) - len(new_releases)} duplicates)")
        return new_releases

    def _llm_filter(self, releases: List[Release]) -> List:
        """Filter releases using LLM."""
        logger.info("Filtering releases with LLM...")

        filtered = self.filter.filter_releases(releases)

        logger.info(f"LLM filtered down to {len(filtered)} relevant releases")
        return filtered

    def _store_releases(self, filtered_releases: List):
        """Store releases in database with dimension data."""
        logger.info("Storing releases in database...")

        for release, score, reasoning, dimensions in filtered_releases:
            self.db.add_release(
                platform=release.platform,
                item_id=release.item_id,
                title=release.title,
                url=release.url,
                description=release.description,
                metadata=release.metadata,
                relevance_score=score,
                filtered_out=False,
                dimensions=dimensions
            )

        logger.info(f"Stored {len(filtered_releases)} releases")

    def _send_to_discord(self):
        """Send unsent releases to Discord with diversity and priority optimization."""
        logger.info("Sending releases to Discord...")

        # Get unsent releases (get more than max to allow for diversity filtering)
        max_items = self.config.get('filtering', {}).get('max_items_per_run', 15)
        releases = self.db.get_unsent_releases(limit=max_items * 3)

        if not releases:
            logger.info("No releases to send")
            return

        # Apply diversity constraints
        releases = self.selection_optimizer.enforce_diversity(releases)

        # Apply priority queue (if enabled)
        releases = self.priority_queue.assign_priority(releases)

        # Limit to max_items
        releases = releases[:max_items]

        # Check if this exact report was already sent
        is_cached, cached_info = self.report_cache.is_report_sent(releases)

        if is_cached:
            logger.info("=" * 60)
            logger.info("⚠️  DUPLICATE REPORT DETECTED")
            logger.info(f"This exact set of {len(releases)} releases was already sent")
            logger.info(f"Previously sent: {cached_info['sent_at']}")
            logger.info(f"Content: {cached_info['content_summary']}")
            logger.info("=" * 60)
            logger.info("Skipping duplicate report to avoid spam")

            # Mark as sent in database (they're technically "sent" already)
            for release in releases:
                self.db.mark_sent(release['platform'], release['item_id'])

            return

        # Generate reports before sending
        logger.info("Generating new reports...")
        json_path = self.report_gen.generate_json_report(releases)
        csv_path = self.report_gen.generate_csv_report(releases)
        md_path = self.report_gen.generate_markdown_report(releases)
        logger.info(f"Reports saved: JSON={json_path}, CSV={csv_path}, MD={md_path}")

        # Send to Discord
        success = self.discord.send_releases(releases)

        if success:
            # Mark as sent in database
            for release in releases:
                self.db.mark_sent(release['platform'], release['item_id'])

            # Cache this report
            report_files = {
                'json': json_path,
                'csv': csv_path,
                'markdown': md_path
            }
            self.report_cache.cache_report(
                releases=releases,
                report_files=report_files,
                discord_sent=True
            )

            logger.info(f"Successfully sent {len(releases)} releases to Discord")
            logger.info(f"Report cached to prevent duplicates")
        else:
            logger.warning("Failed to send releases to Discord")

    def _cleanup(self):
        """Cleanup old database entries and cache."""
        retention_days = self.config.get('storage', {}).get('retention_days', 30)
        self.db.cleanup_old_entries(retention_days)
        self.report_cache.cleanup_old_cache(retention_days)

    def _send_summary(self):
        """Send summary statistics to Discord."""
        stats = self.db.get_stats()
        cache_stats = self.report_cache.get_cache_stats()

        # Merge stats
        stats['cache'] = cache_stats

        self.discord.send_summary(stats)


def main():
    """Entry point for the application."""
    # Check for command line arguments
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = 'config.yaml'

    monitor = ReleaseMonitor(config_path)
    monitor.run()


if __name__ == '__main__':
    main()
