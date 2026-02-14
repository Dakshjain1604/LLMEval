"""Selection optimizer for diversity-aware batch composition."""

import logging
from typing import List, Dict
from collections import defaultdict

logger = logging.getLogger(__name__)


class SelectionOptimizer:
    """Optimizes release selection for diversity and quality."""

    def __init__(self, config: Dict):
        self.config = config
        selection_config = config.get('filtering', {}).get('selection', {})

        self.use_diversity = selection_config.get('use_diversity_constraints', True)
        self.constraints = selection_config.get('diversity_constraints', {})

        self.max_per_platform = self.constraints.get('max_per_platform', 7)
        self.max_per_modality = self.constraints.get('max_per_modality', 8)
        self.min_platforms = self.constraints.get('min_platforms', 2)
        self.max_similar_tasks = self.constraints.get('max_similar_tasks', 4)

    def enforce_diversity(self, releases: List[Dict]) -> List[Dict]:
        """Enforce diversity constraints on release selection.

        Args:
            releases: List of release dicts (from database)

        Returns:
            Filtered list with diversity constraints applied
        """
        if not self.use_diversity:
            logger.info("Diversity constraints disabled, returning all releases")
            return releases

        logger.info(f"Applying diversity constraints to {len(releases)} releases...")

        diverse_batch = []
        platform_counts = defaultdict(int)
        modality_counts = defaultdict(int)
        task_counts = defaultdict(int)

        # Sort by composite_score or relevance_score descending
        sorted_releases = sorted(
            releases,
            key=lambda r: r.get('composite_score') or r.get('relevance_score', 0),
            reverse=True
        )

        for release in sorted_releases:
            platform = release['platform']
            modality = self._infer_modality(release)
            task_type = self._infer_task_type(release)

            # Check diversity constraints
            if platform_counts[platform] >= self.max_per_platform:
                logger.debug(f"Skipping {release['title']}: max per platform ({platform}) reached")
                continue

            if modality_counts[modality] >= self.max_per_modality:
                logger.debug(f"Skipping {release['title']}: max per modality ({modality}) reached")
                continue

            if task_type and task_counts[task_type] >= self.max_similar_tasks:
                logger.debug(f"Skipping {release['title']}: max similar tasks ({task_type}) reached")
                continue

            # Add to diverse batch
            diverse_batch.append(release)
            platform_counts[platform] += 1
            modality_counts[modality] += 1
            if task_type:
                task_counts[task_type] += 1

            # Stop when we have enough
            if len(diverse_batch) >= 15:
                break

        # Check minimum platforms constraint
        unique_platforms = len(set(r['platform'] for r in diverse_batch))
        if unique_platforms < self.min_platforms:
            logger.warning(f"Only {unique_platforms} platforms represented (minimum: {self.min_platforms})")

        logger.info(f"Diversity-filtered batch: {len(diverse_batch)} releases")
        logger.info(f"  Platform distribution: {dict(platform_counts)}")
        logger.info(f"  Modality distribution: {dict(modality_counts)}")

        return diverse_batch

    def _infer_modality(self, release: Dict) -> str:
        """Infer the modality of a release.

        Returns: 'language', 'image', 'audio', 'video', 'multimodal', or 'other'
        """
        text_to_check = (
            f"{release.get('title', '')} "
            f"{release.get('description', '')} "
            f"{release.get('metadata', {})}"
        ).lower()

        # Check for multimodal first (most specific)
        multimodal_keywords = [
            'multimodal', 'vision-language', 'vlm', 'audio-visual',
            'speech-to-text', 'text-to-speech', 'image-to-text',
            'text-to-image', 'visual-language'
        ]
        if any(kw in text_to_check for kw in multimodal_keywords):
            return 'multimodal'

        # Video
        video_keywords = [
            'video', 'sora', 'video-generation', 'video-classification',
            'video-understanding', 'text-to-video'
        ]
        if any(kw in text_to_check for kw in video_keywords):
            return 'video'

        # Audio
        audio_keywords = [
            'audio', 'speech', 'voice', 'tts', 'text-to-speech',
            'whisper', 'asr', 'speech-recognition', 'music',
            'audio-generation', 'music-generation'
        ]
        if any(kw in text_to_check for kw in audio_keywords):
            return 'audio'

        # Image
        image_keywords = [
            'image', 'vision', 'diffusion', 'stable-diffusion',
            'image-generation', 'image-classification', 'object-detection',
            'segmentation', 'image-segmentation', 'dall-e', 'midjourney',
            'flux', 'imagen'
        ]
        if any(kw in text_to_check for kw in image_keywords):
            return 'image'

        # Language (most common, check last)
        language_keywords = [
            'language', 'llm', 'gpt', 'text', 'chat', 'instruction',
            'conversational', 'text-generation', 'question-answering',
            'translation', 'summarization', 'code-generation', 'codex',
            'llama', 'mistral', 'gemma', 'qwen', 'phi'
        ]
        if any(kw in text_to_check for kw in language_keywords):
            return 'language'

        return 'other'

    def _infer_task_type(self, release: Dict) -> str:
        """Infer the task type for grouping similar releases.

        Returns: Task type identifier (e.g., 'text-generation', 'image-generation')
        """
        text_to_check = (
            f"{release.get('title', '')} "
            f"{release.get('description', '')} "
            f"{release.get('metadata', {})}"
        ).lower()

        # Define task type keywords
        task_keywords = {
            'text-generation': ['text-generation', 'language-model', 'llm', 'chat', 'gpt'],
            'code-generation': ['code-generation', 'codex', 'copilot', 'code'],
            'image-generation': ['image-generation', 'diffusion', 'text-to-image', 'stable-diffusion'],
            'image-classification': ['image-classification', 'vision-model'],
            'object-detection': ['object-detection', 'detection', 'yolo'],
            'speech-recognition': ['speech-recognition', 'asr', 'whisper'],
            'tts': ['text-to-speech', 'tts', 'voice-synthesis'],
            'audio-generation': ['audio-generation', 'music-generation'],
            'video-generation': ['video-generation', 'text-to-video'],
            'embedding': ['embedding', 'sentence-similarity'],
            'rl': ['reinforcement-learning', 'rl', 'robotics']
        }

        for task_type, keywords in task_keywords.items():
            if any(kw in text_to_check for kw in keywords):
                return task_type

        return 'other'
