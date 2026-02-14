"""Priority queue system for intelligent release ranking."""

import logging
from typing import List, Dict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class QueueLevel(Enum):
    """Priority queue levels."""
    CRITICAL = 1   # Urgent: major releases, SOTA breakthroughs
    HIGH = 2       # High priority: score ≥80 with high confidence
    MEDIUM = 3     # Medium priority: score 70-79
    STANDARD = 4   # Standard priority: score 60-69
    RESEARCH = 5   # Research queue: arXiv papers


class PriorityQueue:
    """Manages priority-based release queuing."""

    def __init__(self, config: Dict):
        self.config = config
        self.use_priority_queue = config.get('filtering', {}).get('selection', {}).get('use_priority_queue', False)

    def assign_priority(self, releases: List[Dict]) -> List[Dict]:
        """Assign priority levels and calculate urgency for releases.

        Args:
            releases: List of release dicts

        Returns:
            List of releases with 'priority_level' and 'urgency_score' added
        """
        if not self.use_priority_queue:
            logger.debug("Priority queue disabled, skipping priority assignment")
            return releases

        logger.info(f"Assigning priorities to {len(releases)} releases...")

        for release in releases:
            # Calculate urgency score
            urgency = self._calculate_urgency(release)
            release['urgency_score'] = urgency

            # Assign queue level
            queue_level = self._determine_queue_level(release)
            release['priority_level'] = queue_level.name
            release['priority_order'] = queue_level.value

            logger.debug(f"{release['title']}: {queue_level.name} (urgency: {urgency:.1f})")

        # Sort by priority_order (lower is higher priority), then by urgency
        releases.sort(key=lambda r: (r['priority_order'], -r['urgency_score']))

        # Log distribution
        distribution = {}
        for release in releases:
            level = release['priority_level']
            distribution[level] = distribution.get(level, 0) + 1

        logger.info(f"Priority distribution: {distribution}")

        return releases

    def _calculate_urgency(self, release: Dict) -> float:
        """Calculate urgency score (0-100) based on multiple factors.

        Higher urgency = should be evaluated sooner
        """
        urgency = 50.0  # Base urgency

        # Factor 1: Recency (recent releases get boost)
        discovered_at = release.get('discovered_at')
        if discovered_at:
            try:
                if isinstance(discovered_at, str):
                    discovered_dt = datetime.fromisoformat(discovered_at)
                else:
                    discovered_dt = discovered_at

                hours_old = (datetime.now() - discovered_dt).total_seconds() / 3600

                # Less than 24 hours old = +20 urgency (decaying)
                if hours_old < 24:
                    urgency += 20 * (1 - hours_old / 24)

                # Time decay (older = less urgent)
                days_old = hours_old / 24
                urgency *= max(0.5, 1 - days_old / 30)

            except Exception as e:
                logger.debug(f"Could not parse discovered_at: {e}")

        # Factor 2: Novelty (cutting-edge models are more urgent)
        novelty_dim = release.get('novelty_dim', 50)
        urgency += novelty_dim * 0.2

        # Factor 3: Impact (high impact = more urgent)
        impact_dim = release.get('impact_dim', 50)
        urgency += impact_dim * 0.15

        # Factor 4: Platform-specific urgency
        platform = release.get('platform', '')
        if platform == 'github':
            # GitHub stars growth indicates hot repo
            metadata = release.get('metadata', {})
            if isinstance(metadata, dict):
                stars = metadata.get('stars', 0)
                # High star count = popular, boost urgency
                if stars > 1000:
                    urgency += min(15, stars / 1000)

        # Factor 5: Keyword-based urgency boosts
        title_lower = release.get('title', '').lower()
        description_lower = release.get('description', '').lower()
        text = f"{title_lower} {description_lower}"

        # SOTA/Breakthrough keywords
        breakthrough_keywords = ['sota', 'state-of-the-art', 'breakthrough', 'novel', 'first']
        if any(kw in text for kw in breakthrough_keywords):
            urgency += 10

        # Major model releases
        major_keywords = ['gpt-5', 'gpt-6', 'claude-4', 'claude-5', 'gemini-2', 'llama-4']
        if any(kw in text for kw in major_keywords):
            urgency += 30  # Very urgent!

        # Clamp to 0-100
        return min(100, max(0, urgency))

    def _determine_queue_level(self, release: Dict) -> QueueLevel:
        """Determine which priority queue a release belongs to.

        Args:
            release: Release dict

        Returns:
            QueueLevel enum
        """
        score = release.get('composite_score') or release.get('relevance_score', 0)
        confidence = release.get('confidence', 0.5)
        platform = release.get('platform', '')
        urgency = release.get('urgency_score', 50)

        # CRITICAL: Major releases or very high urgency
        if urgency > 90:
            return QueueLevel.CRITICAL

        title_lower = release.get('title', '').lower()
        major_keywords = ['gpt-5', 'gpt-6', 'claude-4', 'claude-5', 'gemini-2', 'llama-4']
        if any(kw in title_lower for kw in major_keywords):
            return QueueLevel.CRITICAL

        # HIGH: Excellent score + high confidence
        if score >= 80 and confidence >= 0.8:
            return QueueLevel.HIGH

        # MEDIUM: Good score
        if score >= 70:
            return QueueLevel.MEDIUM

        # RESEARCH: ArXiv papers (lower priority, long-term value)
        if platform == 'arxiv':
            return QueueLevel.RESEARCH

        # STANDARD: Everything else that passed filter
        return QueueLevel.STANDARD

    def dequeue_for_dispatch(self, releases: List[Dict], neo_state: Dict = None, max_items: int = 15) -> List[Dict]:
        """Dequeue releases for dispatch based on priority and NEO state.

        Args:
            releases: List of prioritized releases
            neo_state: Optional NEO agent state (status, queue_size, etc.)
            max_items: Maximum items to dequeue

        Returns:
            List of releases to dispatch
        """
        if not neo_state:
            # No state info, just return top N by priority
            return releases[:max_items]

        # Adjust batch size based on NEO state
        neo_status = neo_state.get('status', 'idle')

        if neo_status == 'idle':
            # NEO is idle, send more items (diverse mix)
            batch_size = min(max_items + 10, len(releases))
        elif neo_status == 'busy':
            # NEO is busy, only send critical items
            batch_size = max(3, max_items - 10)
            # Filter to only CRITICAL and HIGH
            releases = [r for r in releases if r.get('priority_order', 5) <= 2]
        elif neo_state.get('recent_error_rate', 0) > 0.3:
            # High error rate, reduce load
            batch_size = max(5, max_items - 5)
        else:
            batch_size = max_items

        logger.info(f"Dequeuing {batch_size} releases (NEO status: {neo_status})")

        return releases[:batch_size]
