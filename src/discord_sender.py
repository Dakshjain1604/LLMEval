"""Discord webhook integration for sending filtered releases."""

import logging
import requests
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class DiscordSender:
    """Sends filtered releases to Discord via webhook."""

    def __init__(self, config: Dict):
        self.config = config
        self.webhook_url = config.get('discord', {}).get('webhook_url', '')
        self.dry_run = config.get('discord', {}).get('dry_run', False)

    def send_releases(self, releases: List[Dict]) -> bool:
        """Send releases to Discord.

        Args:
            releases: List of release dicts with score and reasoning

        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url or self.webhook_url == 'YOUR_DISCORD_WEBHOOK_URL_HERE':
            logger.warning("Discord webhook URL not configured")
            return False

        if not releases:
            logger.info("No releases to send")
            return True

        # Build Discord embed message
        embeds = self._build_embeds(releases)

        # Send in chunks (Discord has limits)
        chunk_size = 10  # Discord allows up to 10 embeds per message
        for i in range(0, len(embeds), chunk_size):
            chunk = embeds[i:i + chunk_size]
            if not self._send_chunk(chunk, i // chunk_size + 1, len(embeds)):
                return False

        # Send consolidated report after all releases
        if not self._send_consolidated_report(releases):
            logger.warning("Failed to send consolidated report")

        logger.info(f"Successfully sent {len(releases)} releases to Discord")
        return True

    def _build_embeds(self, releases: List[Dict]) -> List[Dict]:
        """Build Discord embed objects for releases."""
        embeds = []

        for release in releases:
            # Extract data
            title = release.get('title', 'Unknown')
            url = release.get('url', '')
            description = release.get('description', '')[:200]  # Truncate
            platform = release.get('platform', 'unknown')
            score = release.get('relevance_score', 0)
            metadata = release.get('metadata', {})

            # Determine color based on score
            if score >= 80:
                color = 0x00FF00  # Green
            elif score >= 60:
                color = 0xFFFF00  # Yellow
            else:
                color = 0xFF9900  # Orange

            # Build embed
            embed = {
                "title": f"{'⭐' if score >= 80 else '📦'} {title}",
                "url": url,
                "description": description,
                "color": color,
                "fields": [
                    {
                        "name": "Platform",
                        "value": platform.capitalize(),
                        "inline": True
                    },
                    {
                        "name": "Relevance Score",
                        "value": f"{score}/100",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": f"Discovered on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                }
            }

            # Add metadata fields
            if metadata:
                meta_type = metadata.get('type', '')
                if meta_type:
                    embed['fields'].insert(1, {
                        "name": "Type",
                        "value": meta_type.capitalize(),
                        "inline": True
                    })

                # Add platform-specific info
                if platform == 'huggingface':
                    if 'downloads' in metadata:
                        embed['fields'].append({
                            "name": "Downloads",
                            "value": f"{metadata['downloads']:,}",
                            "inline": True
                        })
                    if 'likes' in metadata:
                        embed['fields'].append({
                            "name": "Likes",
                            "value": str(metadata['likes']),
                            "inline": True
                        })

                elif platform == 'github':
                    if 'stars' in metadata:
                        embed['fields'].append({
                            "name": "⭐ Stars",
                            "value": f"{metadata['stars']:,}",
                            "inline": True
                        })
                    if 'language' in metadata and metadata['language']:
                        embed['fields'].append({
                            "name": "Language",
                            "value": metadata['language'],
                            "inline": True
                        })

                elif platform == 'arxiv':
                    if 'authors' in metadata and metadata['authors']:
                        authors = metadata['authors'][:3]  # First 3 authors
                        author_text = ', '.join(authors)
                        if len(metadata['authors']) > 3:
                            author_text += f" +{len(metadata['authors']) - 3} more"
                        embed['fields'].append({
                            "name": "Authors",
                            "value": author_text,
                            "inline": False
                        })

            embeds.append(embed)

        return embeds

    def _send_chunk(self, embeds: List[Dict], chunk_num: int, total_embeds: int) -> bool:
        """Send a chunk of embeds to Discord."""
        # Add header message for first chunk
        content = None
        if chunk_num == 1:
            content = f"🤖 **NEO AI/ML Release Monitor** - {len(embeds)} new releases found"

        payload = {
            "embeds": embeds
        }

        if content:
            payload["content"] = content

        if self.dry_run:
            logger.info(f"[DRY RUN] Would send {len(embeds)} embeds to Discord")
            logger.debug(f"Payload: {payload}")
            return True

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code == 204:
                logger.debug(f"Sent chunk {chunk_num} successfully")
                return True
            else:
                logger.error(f"Discord webhook error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending to Discord: {e}")
            return False

    def _send_consolidated_report(self, releases: List[Dict]) -> bool:
        """Send a consolidated report with all release links.

        This makes it easier for downstream tools to process.
        """
        if not releases:
            return True

        # Group releases by platform
        by_platform = {}
        for release in releases:
            platform = release.get('platform', 'unknown')
            if platform not in by_platform:
                by_platform[platform] = []
            by_platform[platform].append(release)

        # Build markdown report
        report_lines = [
            f"**📋 CONSOLIDATED REPORT - {len(releases)} Releases**",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        for platform, items in sorted(by_platform.items()):
            report_lines.append(f"### {platform.upper()} ({len(items)} releases)")
            report_lines.append("")

            for idx, release in enumerate(items, 1):
                title = release.get('title', 'Unknown')[:80]  # Truncate long titles
                url = release.get('url', '')
                score = release.get('relevance_score', 0)
                metadata = release.get('metadata', {})
                item_type = metadata.get('type', 'item')

                # Create line with emoji based on type
                emoji = self._get_emoji_for_type(item_type)
                report_lines.append(f"{idx}. {emoji} **[{title}]({url})** (Score: {score}/100)")

            report_lines.append("")

        # Add JSON data section for machine parsing
        report_lines.append("---")
        report_lines.append("**📊 Machine-Readable Data:**")
        report_lines.append("```json")

        # Create simplified JSON structure
        import json
        json_data = {
            "generated_at": datetime.now().isoformat(),
            "total_count": len(releases),
            "releases": [
                {
                    "title": r.get('title'),
                    "url": r.get('url'),
                    "platform": r.get('platform'),
                    "score": r.get('relevance_score'),
                    "type": r.get('metadata', {}).get('type'),
                    "description": r.get('description', '')[:200]  # Truncate
                }
                for r in releases
            ]
        }

        json_str = json.dumps(json_data, indent=2)
        # Discord has a 2000 char limit per message, so truncate if needed
        if len(json_str) > 1800:
            json_str = json_str[:1800] + "\n... (truncated)"

        report_lines.append(json_str)
        report_lines.append("```")

        # Create the message
        content = "\n".join(report_lines)

        # Split into chunks if too long (Discord 2000 char limit)
        if len(content) > 1900:
            # Send in parts
            parts = self._split_content(content, 1900)
            for part_idx, part in enumerate(parts):
                if part_idx == 0:
                    part = f"**📋 CONSOLIDATED REPORT - {len(releases)} Releases** (Part {part_idx + 1}/{len(parts)})\n\n" + part
                else:
                    part = f"*(Continued {part_idx + 1}/{len(parts)})*\n\n" + part

                payload = {"content": part}

                if self.dry_run:
                    logger.info(f"[DRY RUN] Would send consolidated report part {part_idx + 1}")
                    continue

                try:
                    response = requests.post(self.webhook_url, json=payload, timeout=10)
                    if response.status_code != 204:
                        logger.error(f"Failed to send report part {part_idx + 1}: {response.status_code}")
                        return False
                except Exception as e:
                    logger.error(f"Error sending report part {part_idx + 1}: {e}")
                    return False
        else:
            # Send as single message
            payload = {"content": content}

            if self.dry_run:
                logger.info("[DRY RUN] Would send consolidated report")
                logger.debug(f"Report content:\n{content}")
                return True

            try:
                response = requests.post(self.webhook_url, json=payload, timeout=10)
                if response.status_code != 204:
                    logger.error(f"Failed to send report: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"Error sending report: {e}")
                return False

        logger.info("Sent consolidated report")
        return True

    def _get_emoji_for_type(self, item_type: str) -> str:
        """Get emoji based on item type."""
        emoji_map = {
            'model': '🤖',
            'dataset': '📊',
            'paper': '📄',
            'repository': '💻',
        }
        return emoji_map.get(item_type, '📦')

    def _split_content(self, content: str, max_length: int) -> List[str]:
        """Split content into chunks respecting line breaks."""
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_length = 0

        for line in lines:
            line_length = len(line) + 1  # +1 for newline
            if current_length + line_length > max_length and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def send_summary(self, stats: Dict) -> bool:
        """Send a summary message to Discord."""
        if not self.webhook_url or self.webhook_url == 'YOUR_DISCORD_WEBHOOK_URL_HERE':
            return False

        embed = {
            "title": "📊 NEO Release Monitor Summary",
            "color": 0x3498DB,
            "fields": [
                {
                    "name": "Total Discovered",
                    "value": str(stats.get('total', 0)),
                    "inline": True
                },
                {
                    "name": "Passed Filter",
                    "value": str(stats.get('passed_filter', 0)),
                    "inline": True
                },
                {
                    "name": "Sent to Discord",
                    "value": str(stats.get('sent', 0)),
                    "inline": True
                }
            ],
            "footer": {
                "text": f"Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }

        # Add platform breakdown
        by_platform = stats.get('by_platform', {})
        if by_platform:
            platform_text = '\n'.join(f"• {platform}: {count}" for platform, count in by_platform.items())
            embed['fields'].append({
                "name": "By Platform",
                "value": platform_text,
                "inline": False
            })

        payload = {"embeds": [embed]}

        if self.dry_run:
            logger.info("[DRY RUN] Would send summary to Discord")
            return True

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 204
        except Exception as e:
            logger.error(f"Error sending summary to Discord: {e}")
            return False
