"""GitHub collector for AI/ML repositories."""

import logging
from datetime import datetime, timedelta
from typing import List
from github import Github, GithubException
from .base import Collector, Release

logger = logging.getLogger(__name__)


class GitHubCollector(Collector):
    """Collects new AI/ML repositories from GitHub."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.github_config = config.get('platforms', {}).get('github', {})
        self.lookback_days = 1

        # Initialize GitHub API
        token = self.github_config.get('token')
        self.github = Github(token) if token else Github()

    def collect(self) -> List[Release]:
        """Collect new repositories from GitHub."""
        releases = []
        cutoff_date = datetime.now() - timedelta(days=self.lookback_days)

        topics = self.github_config.get('topics', ['machine-learning', 'deep-learning'])
        min_stars = self.github_config.get('min_stars', 50)

        try:
            for topic in topics:
                # Search for recently updated repos with topic
                query = f"topic:{topic} stars:>={min_stars} pushed:>={cutoff_date.strftime('%Y-%m-%d')}"

                repos = self.github.search_repositories(
                    query=query,
                    sort='updated',
                    order='desc'
                )

                # Limit to first 50 results per topic
                for i, repo in enumerate(repos):
                    if i >= 50:
                        break

                    # Skip forks
                    if repo.fork:
                        continue

                    # Check if recently updated
                    if repo.updated_at.replace(tzinfo=None) < cutoff_date:
                        continue

                    release = Release(
                        platform='github',
                        item_id=repo.full_name,
                        title=repo.name,
                        url=repo.html_url,
                        description=repo.description or f"GitHub repository: {repo.full_name}",
                        release_date=repo.updated_at.replace(tzinfo=None),
                        metadata={
                            'type': 'repository',
                            'full_name': repo.full_name,
                            'stars': repo.stargazers_count,
                            'forks': repo.forks_count,
                            'language': repo.language,
                            'topics': repo.get_topics(),
                            'license': repo.license.name if repo.license else None,
                        },
                        tags=repo.get_topics()
                    )
                    releases.append(release)

        except GithubException as e:
            logger.error(f"Error collecting GitHub repos: {e}")
        except Exception as e:
            logger.error(f"Unexpected error collecting GitHub repos: {e}")

        logger.info(f"GitHub: Collected {len(releases)} new repositories")
        return releases
