"""HuggingFace collector for models and datasets."""

import logging
from datetime import datetime, timedelta
from typing import List
from huggingface_hub import HfApi
from .base import Collector, Release

logger = logging.getLogger(__name__)


class HuggingFaceCollector(Collector):
    """Collects new models and datasets from HuggingFace."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.api = HfApi()
        self.hf_config = config.get('platforms', {}).get('huggingface', {})
        self.lookback_hours = 12  # Look back 12 hours

    def collect(self) -> List[Release]:
        """Collect new releases from HuggingFace."""
        releases = []

        if self.hf_config.get('check_models', True):
            releases.extend(self._collect_models())

        if self.hf_config.get('check_datasets', True):
            releases.extend(self._collect_datasets())

        logger.info(f"HuggingFace: Collected {len(releases)} new releases")
        return releases

    def _collect_models(self) -> List[Release]:
        """Collect new models from HuggingFace."""
        releases = []
        cutoff_date = datetime.now() - timedelta(hours=self.lookback_hours)

        try:
            # Get recently updated models
            models = self.api.list_models(
                sort="lastModified",
                direction=-1,
                limit=100
            )

            priority_tags = set(self.hf_config.get('priority_tags', []))
            min_downloads = self.hf_config.get('min_downloads', 0)

            for model in models:
                # Check if recently updated
                if model.lastModified:
                    model_date = model.lastModified.replace(tzinfo=None) if model.lastModified.tzinfo else model.lastModified
                    if model_date < cutoff_date:
                        break  # Models are sorted by date, so stop here

                # Filter by downloads
                if model.downloads and model.downloads < min_downloads:
                    continue

                # Check tags if priority_tags is set
                model_tags = set(model.tags) if model.tags else set()
                if priority_tags and not priority_tags.intersection(model_tags):
                    continue

                release = Release(
                    platform='huggingface',
                    item_id=f"model:{model.modelId}",
                    title=model.modelId,
                    url=f"https://huggingface.co/{model.modelId}",
                    description=f"Model: {model.modelId}",
                    release_date=model.lastModified or datetime.now(),
                    metadata={
                        'type': 'model',
                        'model_id': model.modelId,
                        'downloads': model.downloads,
                        'likes': model.likes,
                        'tags': list(model_tags),
                        'pipeline_tag': model.pipeline_tag,
                        'library': model.library_name,
                    },
                    tags=list(model_tags)
                )
                releases.append(release)

        except Exception as e:
            logger.error(f"Error collecting HuggingFace models: {e}")

        return releases

    def _collect_datasets(self) -> List[Release]:
        """Collect new datasets from HuggingFace."""
        releases = []
        cutoff_date = datetime.now() - timedelta(hours=self.lookback_hours)

        try:
            # Get recently updated datasets
            datasets = self.api.list_datasets(
                sort="lastModified",
                direction=-1,
                limit=100
            )

            min_downloads = self.hf_config.get('min_downloads', 0)

            for dataset in datasets:
                # Check if recently updated
                if dataset.lastModified:
                    dataset_date = dataset.lastModified.replace(tzinfo=None) if dataset.lastModified.tzinfo else dataset.lastModified
                    if dataset_date < cutoff_date:
                        break

                # Filter by downloads
                if dataset.downloads and dataset.downloads < min_downloads:
                    continue

                dataset_tags = set(dataset.tags) if dataset.tags else set()

                release = Release(
                    platform='huggingface',
                    item_id=f"dataset:{dataset.id}",
                    title=dataset.id,
                    url=f"https://huggingface.co/datasets/{dataset.id}",
                    description=f"Dataset: {dataset.id}",
                    release_date=dataset.lastModified or datetime.now(),
                    metadata={
                        'type': 'dataset',
                        'dataset_id': dataset.id,
                        'downloads': dataset.downloads,
                        'likes': dataset.likes,
                        'tags': list(dataset_tags),
                    },
                    tags=list(dataset_tags)
                )
                releases.append(release)

        except Exception as e:
            logger.error(f"Error collecting HuggingFace datasets: {e}")

        return releases
