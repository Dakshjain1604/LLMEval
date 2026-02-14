"""arXiv collector for research papers."""

import logging
from datetime import datetime, timedelta
from typing import List
import arxiv
from .base import Collector, Release

logger = logging.getLogger(__name__)


class ArxivCollector(Collector):
    """Collects new papers from arXiv."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.arxiv_config = config.get('platforms', {}).get('arxiv', {})
        self.lookback_days = 1  # Look back 1 day

    def collect(self) -> List[Release]:
        """Collect new papers from arXiv."""
        releases = []
        cutoff_date = datetime.now() - timedelta(days=self.lookback_days)

        categories = self.arxiv_config.get('categories', ['cs.AI', 'cs.LG', 'cs.CL'])
        keywords = self.arxiv_config.get('keywords', [])

        try:
            for category in categories:
                # Query arXiv for recent papers in category
                search = arxiv.Search(
                    query=f"cat:{category}",
                    max_results=50,
                    sort_by=arxiv.SortCriterion.SubmittedDate
                )

                for result in search.results():
                    # Check if recent
                    if result.published.replace(tzinfo=None) < cutoff_date:
                        continue

                    # Check keywords if specified
                    if keywords:
                        text = (result.title + " " + result.summary).lower()
                        if not any(keyword.lower() in text for keyword in keywords):
                            continue

                    release = Release(
                        platform='arxiv',
                        item_id=result.entry_id.split('/')[-1],
                        title=result.title,
                        url=result.entry_id,
                        description=result.summary[:500] + "..." if len(result.summary) > 500 else result.summary,
                        release_date=result.published.replace(tzinfo=None),
                        metadata={
                            'type': 'paper',
                            'authors': [author.name for author in result.authors],
                            'categories': result.categories,
                            'pdf_url': result.pdf_url,
                            'primary_category': result.primary_category,
                        },
                        tags=result.categories
                    )
                    releases.append(release)

        except Exception as e:
            logger.error(f"Error collecting arXiv papers: {e}")

        logger.info(f"arXiv: Collected {len(releases)} new papers")
        return releases
