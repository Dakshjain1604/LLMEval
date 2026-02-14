"""Kaggle collector for datasets and models."""

import logging
from datetime import datetime, timedelta
from typing import List
import requests
from .base import Collector, Release

logger = logging.getLogger(__name__)


class KaggleCollector(Collector):
    """Collects new datasets and models from Kaggle."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.kaggle_config = config.get('platforms', {}).get('kaggle', {})
        self.lookback_days = 1

    def collect(self) -> List[Release]:
        """Collect new releases from Kaggle."""
        releases = []

        # Note: Kaggle API requires authentication
        # Check if credentials are available
        username = self.kaggle_config.get('username')
        api_key = self.kaggle_config.get('api_key')

        if not username or not api_key:
            logger.warning("Kaggle credentials not configured, skipping")
            return releases

        if self.kaggle_config.get('check_datasets', True):
            releases.extend(self._collect_datasets())

        if self.kaggle_config.get('check_models', True):
            releases.extend(self._collect_models())

        logger.info(f"Kaggle: Collected {len(releases)} new releases")
        return releases

    def _collect_datasets(self) -> List[Release]:
        """Collect new datasets from Kaggle."""
        releases = []

        try:
            # Use Kaggle public API to list datasets
            url = "https://www.kaggle.com/api/v1/datasets/list"
            params = {
                'sortBy': 'updated',
                'page': 1,
                'pageSize': 50
            }

            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                datasets = response.json()
                min_votes = self.kaggle_config.get('min_votes', 0)

                for dataset in datasets:
                    # Filter by votes
                    if dataset.get('voteCount', 0) < min_votes:
                        continue

                    # Try to parse date
                    last_updated = dataset.get('lastUpdated', '')
                    try:
                        release_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                        release_date = release_date.replace(tzinfo=None)
                    except:
                        release_date = datetime.now()

                    dataset_ref = dataset.get('ref', '')
                    title = dataset.get('title', dataset_ref)

                    release = Release(
                        platform='kaggle',
                        item_id=f"dataset:{dataset_ref}",
                        title=title,
                        url=f"https://www.kaggle.com/datasets/{dataset_ref}",
                        description=dataset.get('subtitle', title),
                        release_date=release_date,
                        metadata={
                            'type': 'dataset',
                            'ref': dataset_ref,
                            'votes': dataset.get('voteCount', 0),
                            'size': dataset.get('totalBytes', 0),
                            'files': dataset.get('totalFiles', 0),
                        },
                        tags=dataset.get('tags', [])
                    )
                    releases.append(release)

        except Exception as e:
            logger.error(f"Error collecting Kaggle datasets: {e}")

        return releases

    def _collect_models(self) -> List[Release]:
        """Collect new models from Kaggle."""
        releases = []

        try:
            # Use Kaggle public API to list models
            url = "https://www.kaggle.com/api/v1/models/list"
            params = {
                'sortBy': 'updated',
                'page': 1,
                'pageSize': 50
            }

            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                models = response.json()

                for model in models:
                    # Try to parse date
                    last_updated = model.get('lastUpdated', '')
                    try:
                        release_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                        release_date = release_date.replace(tzinfo=None)
                    except:
                        release_date = datetime.now()

                    model_ref = model.get('ref', '')
                    title = model.get('title', model_ref)

                    release = Release(
                        platform='kaggle',
                        item_id=f"model:{model_ref}",
                        title=title,
                        url=f"https://www.kaggle.com/models/{model_ref}",
                        description=model.get('subtitle', title),
                        release_date=release_date,
                        metadata={
                            'type': 'model',
                            'ref': model_ref,
                            'framework': model.get('framework', ''),
                        },
                        tags=[]
                    )
                    releases.append(release)

        except Exception as e:
            logger.error(f"Error collecting Kaggle models: {e}")

        return releases
