"""Base collector interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class Release:
    """Represents a discovered AI/ML release."""
    platform: str
    item_id: str
    title: str
    url: str
    description: str
    release_date: datetime
    metadata: Dict
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class Collector(ABC):
    """Base class for platform collectors."""

    def __init__(self, config: Dict):
        self.config = config
        self.platform_name = self.__class__.__name__.replace('Collector', '').lower()

    @abstractmethod
    def collect(self) -> List[Release]:
        """Collect new releases from the platform.

        Returns:
            List of Release objects discovered since last check.
        """
        pass

    def is_enabled(self) -> bool:
        """Check if this collector is enabled in config."""
        return self.config.get('platforms', {}).get(self.platform_name, {}).get('enabled', False)
