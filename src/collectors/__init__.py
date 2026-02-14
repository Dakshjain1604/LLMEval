"""Platform collectors for discovering new AI/ML releases."""

from .base import Collector, Release
from .huggingface import HuggingFaceCollector
from .arxiv import ArxivCollector
from .kaggle import KaggleCollector
from .github import GitHubCollector

__all__ = [
    'Collector',
    'Release',
    'HuggingFaceCollector',
    'ArxivCollector',
    'KaggleCollector',
    'GitHubCollector',
]
