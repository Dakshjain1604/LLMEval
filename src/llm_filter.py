"""LLM-based filtering for AI/ML releases."""

import logging
from typing import List, Dict, Tuple
import anthropic
import openai
from .collectors.base import Release

logger = logging.getLogger(__name__)


class LLMFilter:
    """Uses LLM to filter and score releases for relevance to NEO."""

    def __init__(self, config: Dict):
        self.config = config
        self.llm_config = config.get('llm', {})
        self.neo_context = config.get('neo_context', {})
        self.filtering = config.get('filtering', {})

        # Get dimension weights from config
        scoring_config = self.filtering.get('scoring', {})
        self.dimension_weights = scoring_config.get('dimension_weights', {
            'relevance': 0.30,
            'quality': 0.20,
            'novelty': 0.25,
            'evaluability': 0.20,
            'impact': 0.05
        })

        # Get threshold configuration
        thresholds_config = self.filtering.get('thresholds', {})
        self.default_threshold = thresholds_config.get('default', 60)
        self.platform_thresholds = thresholds_config.get('platform_specific', {})
        self.adaptive_config = thresholds_config.get('adaptive', {'enabled': False})

        # Initialize LLM client
        provider = self.llm_config.get('provider', 'anthropic')
        if provider == 'anthropic':
            api_key = self.llm_config.get('api_key')
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = self.llm_config.get('model', 'claude-sonnet-4-5-20250929')
        elif provider == 'openai':
            api_key = self.llm_config.get('api_key')
            openai.api_key = api_key
            self.model = self.llm_config.get('model', 'gpt-4')
        elif provider == 'openrouter':
            api_key = self.llm_config.get('api_key')
            # OpenRouter uses OpenAI-compatible API
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1"
            )
            self.model = self.llm_config.get('model', 'anthropic/claude-3.5-sonnet')
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

        self.provider = provider

    def filter_releases(self, releases: List[Release]) -> List[Tuple[Release, int, str, Dict]]:
        """Filter releases using LLM with multi-dimensional scoring and adaptive thresholds.

        Returns:
            List of tuples: (release, composite_score, reasoning, dimensions_dict)
            where dimensions_dict contains: {
                'relevance': int, 'quality': int, 'novelty': int,
                'evaluability': int, 'impact': int, 'confidence': float
            }
        """
        if not releases:
            return []

        logger.info(f"Filtering {len(releases)} releases with LLM...")

        # Calculate dynamic threshold based on volume
        base_threshold = self.calculate_dynamic_threshold(len(releases))

        results = []

        # First pass: score all releases
        scored_releases = []
        for release in releases:
            try:
                score, reasoning, dimensions = self._score_release(release)
                scored_releases.append((release, score, reasoning, dimensions))
            except Exception as e:
                logger.error(f"Error filtering {release.title}: {e}")
                continue

        # Second pass: apply adaptive thresholds
        for release, score, reasoning, dimensions in scored_releases:
            # Get platform-specific threshold
            platform_threshold = self.get_platform_threshold(release.platform)

            # Use the stricter of base_threshold or platform_threshold
            effective_threshold = max(base_threshold, platform_threshold)

            # Apply confidence-weighted threshold
            confidence = dimensions.get('confidence', 0.5)
            passes = self.apply_confidence_threshold(score, confidence, effective_threshold)

            if passes:
                results.append((release, score, reasoning, dimensions))
                logger.debug(f"✓ {release.title} - Score: {score} (R:{dimensions['relevance']}, Q:{dimensions['quality']}, N:{dimensions['novelty']}, E:{dimensions['evaluability']}, I:{dimensions['impact']}, Conf:{confidence:.2f}) [threshold: {effective_threshold}]")
            else:
                logger.debug(f"✗ {release.title} - Score: {score} (below threshold {effective_threshold})")

        logger.info(f"Filtered down to {len(results)} relevant releases (from {len(scored_releases)} scored)")
        return results

    def _score_release(self, release: Release) -> Tuple[int, str, Dict]:
        """Score a single release with multi-dimensional evaluation.

        Returns:
            Tuple of (composite_score 0-100, reasoning, dimensions_dict)
        """
        prompt = self._build_prompt(release)

        if self.provider == 'anthropic':
            response = self.client.messages.create(
                model=self.model,
                max_tokens=700,  # Increased for multi-dimensional response
                temperature=self.llm_config.get('temperature', 0.3),
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = response.content[0].text

        elif self.provider == 'openai':
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.llm_config.get('temperature', 0.3),
                max_tokens=700
            )
            response_text = response.choices[0].message.content

        elif self.provider == 'openrouter':
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.llm_config.get('temperature', 0.3),
                max_tokens=700
            )
            response_text = response.choices[0].message.content

        # Parse response to extract dimensions
        dimensions = self._parse_response(response_text)

        # Calculate composite score from dimensions
        composite_score = self._calculate_composite_score(dimensions)

        # Get reasoning
        reasoning = dimensions.get('reasoning', 'No reasoning provided')

        return composite_score, reasoning, dimensions

    def _build_prompt(self, release: Release) -> str:
        """Build prompt for LLM evaluation."""
        neo_desc = self.neo_context.get('description', '')
        capabilities = '\n'.join(f"- {cap}" for cap in self.neo_context.get('capabilities', []))
        limitations = '\n'.join(f"- {lim}" for lim in self.neo_context.get('limitations', []))

        priority_keywords = self.filtering.get('priority_keywords', [])
        exclude_keywords = self.filtering.get('exclude_keywords', [])

        prompt = f"""You are an AI assistant helping to filter AI/ML releases for NEO, an autonomous AI/ML evaluation agent.

NEO Context:
{neo_desc}

NEO Capabilities:
{capabilities}

NEO Limitations:
{limitations}

Priority Keywords (give higher scores if present):
{', '.join(priority_keywords) if priority_keywords else 'None'}

Exclude Keywords (give lower scores if present):
{', '.join(exclude_keywords) if exclude_keywords else 'None'}

New Release to Evaluate:
Platform: {release.platform}
Title: {release.title}
Description: {release.description}
URL: {release.url}
Tags: {', '.join(release.tags) if release.tags else 'None'}
Metadata: {release.metadata}

Task:
Evaluate this release using a multi-dimensional scoring system. NEO is specifically looking for:
- LATEST language models (LLMs, chat models, instruction models, code generation)
- LATEST image models (generation, classification, detection, diffusion, segmentation)
- LATEST audio/voice models (speech recognition, TTS, audio generation, music generation)
- LATEST video models (video generation, video understanding, video classification)
- LATEST multimodal models (vision-language, audio-visual, any combination)
- RL/robotics models, embeddings, and other specialized architectures
- UNIQUE or NOVEL architectures and approaches across ALL AI/ML domains
- Models that can be evaluated and benchmarked

Evaluate across 5 dimensions (each scored 0-100):

1. RELEVANCE (0-100): How well does this match NEO's capabilities and interests?
   - 80-100: Perfect match for NEO's domain and capabilities
   - 60-79: Good match, relevant and interesting
   - 40-59: Somewhat relevant but not ideal
   - 20-39: Low relevance
   - 0-19: Not relevant

2. QUALITY (0-100): Code quality, documentation, community metrics
   - 80-100: Well-documented, high-quality code, active community
   - 60-79: Good documentation, decent quality
   - 40-59: Basic documentation, acceptable quality
   - 20-39: Poor documentation or quality
   - 0-19: Very low quality

3. NOVELTY (0-100): How cutting-edge and unique is this model?
   - 80-100: Breakthrough/SOTA, novel architecture
   - 60-79: Recent release, some novel aspects
   - 40-59: Incremental improvement
   - 20-39: Older or derivative work
   - 0-19: Outdated or deprecated

4. EVALUABILITY (0-100): How easily can NEO test and benchmark this?
   - 80-100: Clear benchmarks, easy to test, public access
   - 60-79: Can be evaluated with some effort
   - 40-59: Evaluation possible but challenging
   - 20-39: Difficult to evaluate
   - 0-19: Cannot be evaluated

5. IMPACT (0-100): Expected value and community benefit
   - 80-100: High community impact, widely applicable
   - 60-79: Good potential impact
   - 40-59: Moderate impact
   - 20-39: Limited impact
   - 0-19: Minimal impact

Also provide a CONFIDENCE score (0.0-1.0) indicating how certain you are about this evaluation:
- 0.9-1.0: Very confident, clear indicators
- 0.7-0.8: Confident, good information available
- 0.5-0.6: Moderate confidence, some ambiguity
- 0.3-0.4: Low confidence, limited information
- 0.0-0.2: Very uncertain

Provide your response in this EXACT format:
RELEVANCE: <number 0-100>
QUALITY: <number 0-100>
NOVELTY: <number 0-100>
EVALUABILITY: <number 0-100>
IMPACT: <number 0-100>
CONFIDENCE: <number 0.0-1.0>
REASONING: <1-2 sentence explanation>

Response:"""

        return prompt

    def _parse_response(self, response_text: str) -> Dict:
        """Parse LLM response to extract all dimensions and confidence.

        Returns:
            Dict with keys: relevance, quality, novelty, evaluability, impact, confidence, reasoning
        """
        lines = response_text.strip().split('\n')

        # Default values
        dimensions = {
            'relevance': 50,
            'quality': 50,
            'novelty': 50,
            'evaluability': 50,
            'impact': 50,
            'confidence': 0.5,
            'reasoning': 'Unable to parse LLM response'
        }

        for line in lines:
            line = line.strip()

            if line.startswith('RELEVANCE:'):
                try:
                    score_str = line.replace('RELEVANCE:', '').strip()
                    dimensions['relevance'] = max(0, min(100, int(score_str)))
                except ValueError:
                    logger.warning(f"Could not parse relevance from: {line}")

            elif line.startswith('QUALITY:'):
                try:
                    score_str = line.replace('QUALITY:', '').strip()
                    dimensions['quality'] = max(0, min(100, int(score_str)))
                except ValueError:
                    logger.warning(f"Could not parse quality from: {line}")

            elif line.startswith('NOVELTY:'):
                try:
                    score_str = line.replace('NOVELTY:', '').strip()
                    dimensions['novelty'] = max(0, min(100, int(score_str)))
                except ValueError:
                    logger.warning(f"Could not parse novelty from: {line}")

            elif line.startswith('EVALUABILITY:'):
                try:
                    score_str = line.replace('EVALUABILITY:', '').strip()
                    dimensions['evaluability'] = max(0, min(100, int(score_str)))
                except ValueError:
                    logger.warning(f"Could not parse evaluability from: {line}")

            elif line.startswith('IMPACT:'):
                try:
                    score_str = line.replace('IMPACT:', '').strip()
                    dimensions['impact'] = max(0, min(100, int(score_str)))
                except ValueError:
                    logger.warning(f"Could not parse impact from: {line}")

            elif line.startswith('CONFIDENCE:'):
                try:
                    conf_str = line.replace('CONFIDENCE:', '').strip()
                    dimensions['confidence'] = max(0.0, min(1.0, float(conf_str)))
                except ValueError:
                    logger.warning(f"Could not parse confidence from: {line}")

            elif line.startswith('REASONING:'):
                dimensions['reasoning'] = line.replace('REASONING:', '').strip()

        return dimensions

    def _calculate_composite_score(self, dimensions: Dict) -> int:
        """Calculate weighted composite score from dimensions.

        Args:
            dimensions: Dict with relevance, quality, novelty, evaluability, impact scores

        Returns:
            Composite score (0-100)
        """
        composite = (
            dimensions['relevance'] * self.dimension_weights['relevance'] +
            dimensions['quality'] * self.dimension_weights['quality'] +
            dimensions['novelty'] * self.dimension_weights['novelty'] +
            dimensions['evaluability'] * self.dimension_weights['evaluability'] +
            dimensions['impact'] * self.dimension_weights['impact']
        )

        return int(round(composite))

    def calculate_dynamic_threshold(self, candidates_count: int, target: int = 15) -> int:
        """Calculate dynamic threshold based on candidate volume.

        Args:
            candidates_count: Number of candidates being evaluated
            target: Target number of releases to send (default: 15)

        Returns:
            Adjusted threshold value
        """
        if not self.adaptive_config.get('enabled', False):
            return self.default_threshold

        base = self.default_threshold
        min_threshold = self.adaptive_config.get('min_threshold', 50)
        max_threshold = self.adaptive_config.get('max_threshold', 75)

        # Too few candidates -> lower threshold
        if candidates_count < target * 0.7:
            adjusted = max(min_threshold, base - 5)
            logger.info(f"Dynamic threshold: {adjusted} (low volume: {candidates_count} candidates)")
            return adjusted

        # Too many candidates -> raise threshold
        elif candidates_count > target * 2:
            adjusted = min(max_threshold, base + 5)
            logger.info(f"Dynamic threshold: {adjusted} (high volume: {candidates_count} candidates)")
            return adjusted

        # Just right -> use base
        logger.debug(f"Dynamic threshold: {base} (optimal volume: {candidates_count} candidates)")
        return base

    def get_platform_threshold(self, platform: str) -> int:
        """Get platform-specific threshold or default.

        Args:
            platform: Platform name (e.g., 'huggingface', 'github', 'arxiv')

        Returns:
            Threshold for this platform
        """
        return self.platform_thresholds.get(platform, self.default_threshold)

    def apply_confidence_threshold(self, score: int, confidence: float, base_threshold: int) -> bool:
        """Apply confidence-weighted threshold.

        High confidence scores can have lower effective thresholds.
        Low confidence scores need higher scores to pass.

        Args:
            score: The composite score
            confidence: Confidence level (0.0-1.0)
            base_threshold: Base threshold before confidence adjustment

        Returns:
            True if score passes adjusted threshold
        """
        # High confidence (0.9): threshold × 0.90 = 54 (from 60)
        # Low confidence (0.5): threshold × 1.20 = 72 (from 60)
        adjustment_factor = 1.5 - confidence * 0.5
        adjusted_threshold = base_threshold * adjustment_factor

        passes = score >= adjusted_threshold

        if passes:
            logger.debug(f"Score {score} passes (threshold: {adjusted_threshold:.1f}, confidence: {confidence:.2f})")
        else:
            logger.debug(f"Score {score} fails (threshold: {adjusted_threshold:.1f}, confidence: {confidence:.2f})")

        return passes

    def batch_filter_with_summary(self, releases: List[Release], batch_size: int = 5) -> List[Tuple[Release, int, str, Dict]]:
        """Filter releases in batches for efficiency.

        For large numbers of releases, this can process them in batches
        with a single LLM call per batch.

        Returns:
            List of tuples: (release, composite_score, reasoning, dimensions_dict)
        """
        # For now, just use individual filtering
        # This could be optimized to batch multiple items per LLM call
        return self.filter_releases(releases)
