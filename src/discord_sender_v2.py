"""Enhanced Discord webhook integration with better structured reports."""

import logging
import requests
import json
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class EnhancedDiscordSender:
    """Sends releases to Discord with highly structured reports."""

    def __init__(self, config: Dict):
        self.config = config
        self.webhook_url = config.get('discord', {}).get('webhook_url', '')
        self.dry_run = config.get('discord', {}).get('dry_run', False)

    def send_releases(self, releases: List[Dict]) -> bool:
        """Send releases to Discord with enhanced formatting."""
        if not self.webhook_url or self.webhook_url == 'YOUR_DISCORD_WEBHOOK_URL_HERE':
            logger.warning("Discord webhook URL not configured")
            return False

        if not releases:
            logger.info("No releases to send")
            return True

        # Send header message
        self._send_header(len(releases))

        # Build and send embeds
        embeds = self._build_embeds(releases)
        chunk_size = 10
        for i in range(0, len(embeds), chunk_size):
            chunk = embeds[i:i + chunk_size]
            if not self._send_chunk(chunk):
                return False

        # Send enhanced consolidated report
        self._send_enhanced_report(releases)

        logger.info(f"Successfully sent {len(releases)} releases to Discord")
        return True

    def _send_header(self, count: int):
        """Send a header message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        content = f"""
╔══════════════════════════════════════════╗
║   🤖 **NEO AI/ML RELEASE MONITOR**      ║
╚══════════════════════════════════════════╝

📅 **Report Date:** {timestamp}
📦 **New Releases Found:** {count}
🎯 **Status:** Ready for Evaluation

---
"""
        self._send_message(content)

    def _build_embeds(self, releases: List[Dict]) -> List[Dict]:
        """Build Discord embed objects."""
        embeds = []

        # Sort by score (highest first)
        sorted_releases = sorted(releases, key=lambda x: x.get('relevance_score', 0), reverse=True)

        for idx, release in enumerate(sorted_releases, 1):
            title = release.get('title', 'Unknown')[:200]
            url = release.get('url', '')
            description = release.get('description', '')[:300]
            platform = release.get('platform', 'unknown').upper()
            score = release.get('relevance_score', 0)
            metadata = release.get('metadata', {})

            # Color based on score
            if score >= 80:
                color = 0x00FF00  # Green - High priority
                priority = "🔥 HIGH PRIORITY"
            elif score >= 70:
                color = 0xFFFF00  # Yellow - Medium
                priority = "⭐ MEDIUM PRIORITY"
            else:
                color = 0xFFA500  # Orange - Standard
                priority = "📦 STANDARD"

            # Get dimension scores (if available)
            relevance_dim = release.get('relevance_dim')
            quality_dim = release.get('quality_dim')
            novelty_dim = release.get('novelty_dim')
            evaluability_dim = release.get('evaluability_dim')
            impact_dim = release.get('impact_dim')
            confidence = release.get('confidence')

            # Build dimension display
            dimension_text = ""
            if all([relevance_dim is not None, quality_dim is not None, novelty_dim is not None]):
                dimension_text = (
                    f"\n\n**Multi-Dimensional Score:**\n"
                    f"• Relevance: {relevance_dim}/100\n"
                    f"• Quality: {quality_dim}/100\n"
                    f"• Novelty: {novelty_dim}/100\n"
                    f"• Evaluability: {evaluability_dim}/100\n"
                    f"• Impact: {impact_dim}/100"
                )
                if confidence is not None:
                    dimension_text += f"\n• Confidence: {confidence:.2f}"

            # Build embed
            embed = {
                "title": f"#{idx} {title}",
                "url": url,
                "description": f"**{priority}** | Composite Score: {score}/100\n\n{description}...{dimension_text}",
                "color": color,
                "fields": [
                    {
                        "name": "📍 Platform",
                        "value": platform,
                        "inline": True
                    },
                    {
                        "name": "🎯 Composite Score",
                        "value": f"{score}/100",
                        "inline": True
                    }
                ]
            }

            # Add type
            item_type = metadata.get('type', 'item')
            embed['fields'].append({
                "name": "📂 Type",
                "value": item_type.capitalize(),
                "inline": True
            })

            # Platform-specific metadata
            if platform == 'HUGGINGFACE':
                if 'downloads' in metadata:
                    embed['fields'].append({
                        "name": "📥 Downloads",
                        "value": f"{metadata['downloads']:,}",
                        "inline": True
                    })
                if 'likes' in metadata:
                    embed['fields'].append({
                        "name": "❤️ Likes",
                        "value": str(metadata['likes']),
                        "inline": True
                    })
                if 'library' in metadata and metadata['library']:
                    embed['fields'].append({
                        "name": "🛠️ Framework",
                        "value": metadata['library'],
                        "inline": True
                    })

            elif platform == 'GITHUB':
                if 'stars' in metadata:
                    embed['fields'].append({
                        "name": "⭐ Stars",
                        "value": f"{metadata['stars']:,}",
                        "inline": True
                    })
                if 'language' in metadata and metadata['language']:
                    embed['fields'].append({
                        "name": "💻 Language",
                        "value": metadata['language'],
                        "inline": True
                    })
                if 'topics' in metadata and metadata['topics']:
                    topics = metadata['topics'][:3]
                    embed['fields'].append({
                        "name": "🏷️ Topics",
                        "value": ', '.join(topics),
                        "inline": False
                    })

            elif platform == 'ARXIV':
                if 'authors' in metadata and metadata['authors']:
                    authors = metadata['authors'][:2]
                    author_text = ', '.join(authors)
                    if len(metadata['authors']) > 2:
                        author_text += f" +{len(metadata['authors']) - 2} more"
                    embed['fields'].append({
                        "name": "✍️ Authors",
                        "value": author_text,
                        "inline": False
                    })
                if 'categories' in metadata:
                    embed['fields'].append({
                        "name": "📚 Categories",
                        "value": ', '.join(metadata['categories'][:3]),
                        "inline": False
                    })

            embed['footer'] = {
                "text": f"Discovered: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }

            embeds.append(embed)

        return embeds

    def _send_enhanced_report(self, releases: List[Dict]):
        """Send an enhanced structured report."""
        # Group by platform and priority
        by_platform = {}
        high_priority = []
        medium_priority = []
        standard_priority = []

        for r in releases:
            platform = r.get('platform', 'unknown')
            if platform not in by_platform:
                by_platform[platform] = []
            by_platform[platform].append(r)

            score = r.get('relevance_score', 0)
            if score >= 80:
                high_priority.append(r)
            elif score >= 70:
                medium_priority.append(r)
            else:
                standard_priority.append(r)

        # Build comprehensive report
        report = self._build_text_report(releases, by_platform, high_priority, medium_priority, standard_priority)
        self._send_message(report)

        # Send machine-readable data
        json_report = self._build_json_report(releases)
        self._send_message(json_report)

    def _build_text_report(self, releases, by_platform, high_priority, medium_priority, standard_priority):
        """Build detailed text report."""
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📋 **CONSOLIDATED RELEASE REPORT**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "## 📊 EXECUTIVE SUMMARY",
            "",
            f"**Total Releases:** {len(releases)}",
            f"**🔥 High Priority (≥80):** {len(high_priority)}",
            f"**⭐ Medium Priority (70-79):** {len(medium_priority)}",
            f"**📦 Standard (60-69):** {len(standard_priority)}",
            "",
            "**Platform Breakdown:**",
        ]

        for platform, items in sorted(by_platform.items()):
            lines.append(f"• **{platform.upper()}:** {len(items)} releases")

        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "## 🔥 HIGH PRIORITY RELEASES (Score ≥ 80)",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ])

        if high_priority:
            for idx, r in enumerate(high_priority, 1):
                lines.append(f"**{idx}. [{r['title'][:80]}]({r['url']})**")
                lines.append(f"   • Platform: {r['platform'].upper()} | Score: {r['relevance_score']}/100")
                lines.append(f"   • Type: {r.get('metadata', {}).get('type', 'N/A')}")
                lines.append("")
        else:
            lines.append("*No high priority releases in this batch*")
            lines.append("")

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "## ⭐ MEDIUM PRIORITY RELEASES (Score 70-79)",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ])

        if medium_priority:
            for idx, r in enumerate(medium_priority, 1):
                lines.append(f"**{idx}. [{r['title'][:80]}]({r['url']})**")
                lines.append(f"   • Platform: {r['platform'].upper()} | Score: {r['relevance_score']}/100")
                lines.append("")
        else:
            lines.append("*No medium priority releases*")
            lines.append("")

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "## 📦 RELEASES BY PLATFORM",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ])

        for platform, items in sorted(by_platform.items()):
            lines.append(f"### {platform.upper()} ({len(items)} releases)")
            lines.append("")
            for idx, r in enumerate(sorted(items, key=lambda x: x['relevance_score'], reverse=True), 1):
                lines.append(f"{idx}. [{r['title'][:60]}]({r['url']}) - Score: {r['relevance_score']}")
            lines.append("")

        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "## 🎯 RECOMMENDED ACTIONS",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ])

        if high_priority:
            lines.append(f"1. **Prioritize evaluation** of {len(high_priority)} high-priority releases")
        if len(by_platform.get('arxiv', [])) > 3:
            lines.append(f"2. **Review papers** - {len(by_platform.get('arxiv', []))} new research papers available")
        if len(by_platform.get('github', [])) > 5:
            lines.append(f"3. **Check repositories** - {len(by_platform.get('github', []))} new GitHub projects")

        lines.append("")
        lines.append(f"📅 **Next Steps:** Feed this data to NEO for automated evaluation")
        lines.append(f"📁 **Data Location:** `/root/LlmEval/data/reports/`")
        lines.append("")

        return '\n'.join(lines)

    def _build_json_report(self, releases):
        """Build machine-readable JSON report."""
        json_data = {
            "report_generated": datetime.now().isoformat(),
            "total_count": len(releases),
            "summary": {
                "high_priority": len([r for r in releases if r.get('relevance_score', 0) >= 80]),
                "medium_priority": len([r for r in releases if 70 <= r.get('relevance_score', 0) < 80]),
                "standard": len([r for r in releases if r.get('relevance_score', 0) < 70]),
            },
            "platforms": {},
            "releases": []
        }

        # Group by platform
        for r in releases:
            platform = r.get('platform')
            if platform not in json_data["platforms"]:
                json_data["platforms"][platform] = 0
            json_data["platforms"][platform] += 1

            json_data["releases"].append({
                "title": r.get('title'),
                "url": r.get('url'),
                "platform": platform,
                "score": r.get('relevance_score'),
                "type": r.get('metadata', {}).get('type'),
                "description": r.get('description', '')[:200]
            })

        # Sort by score
        json_data["releases"].sort(key=lambda x: x['score'], reverse=True)

        json_str = json.dumps(json_data, indent=2)

        # Split if too long
        if len(json_str) > 1800:
            json_str = json_str[:1800] + "\n... (truncated, see local files)"

        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "## 💾 MACHINE-READABLE DATA",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "```json",
            json_str,
            "```",
            "",
            "**📁 Full Reports Available:**",
            "• JSON: `data/reports/releases_*.json`",
            "• CSV: `data/reports/releases_*.csv`",
            "• Markdown: `data/reports/releases_*.md`",
            "",
            "**🔗 Direct Access:**",
            f"```bash",
            f"# View latest JSON report",
            f"cat $(ls -t data/reports/*.json | head -1)",
            f"```",
        ]

        return '\n'.join(lines)

    def _send_chunk(self, embeds: List[Dict]) -> bool:
        """Send a chunk of embeds."""
        payload = {"embeds": embeds}

        if self.dry_run:
            logger.info(f"[DRY RUN] Would send {len(embeds)} embeds")
            return True

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code != 204:
                logger.error(f"Discord error: {response.status_code} - {response.text}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error sending to Discord: {e}")
            return False

    def _send_message(self, content: str):
        """Send a text message."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would send message")
            return True

        # Split long messages
        max_length = 1900
        if len(content) <= max_length:
            payload = {"content": content}
            try:
                response = requests.post(self.webhook_url, json=payload, timeout=10)
                return response.status_code == 204
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                return False
        else:
            # Split into chunks
            chunks = [content[i:i+max_length] for i in range(0, len(content), max_length)]
            for chunk in chunks:
                payload = {"content": chunk}
                try:
                    response = requests.post(self.webhook_url, json=payload, timeout=10)
                    if response.status_code != 204:
                        return False
                except Exception as e:
                    logger.error(f"Error sending chunk: {e}")
                    return False
            return True

    def send_summary(self, stats: Dict) -> bool:
        """Send summary statistics."""
        if not self.webhook_url or self.webhook_url == 'YOUR_DISCORD_WEBHOOK_URL_HERE':
            return False

        embed = {
            "title": "📊 NEO Release Monitor - Session Summary",
            "color": 0x3498DB,
            "fields": [
                {
                    "name": "📦 Total Discovered",
                    "value": str(stats.get('total', 0)),
                    "inline": True
                },
                {
                    "name": "✅ Passed Filter",
                    "value": str(stats.get('passed_filter', 0)),
                    "inline": True
                },
                {
                    "name": "📤 Sent to Discord",
                    "value": str(stats.get('sent', 0)),
                    "inline": True
                }
            ],
            "footer": {
                "text": f"Report: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }

        by_platform = stats.get('by_platform', {})
        if by_platform:
            platform_text = '\n'.join(f"• **{platform.upper()}:** {count}" for platform, count in by_platform.items())
            embed['fields'].append({
                "name": "🌐 By Platform",
                "value": platform_text,
                "inline": False
            })

        # Add cache statistics
        cache_stats = stats.get('cache', {})
        if cache_stats:
            cache_text = (
                f"• **Cached Reports:** {cache_stats.get('total_cached_reports', 0)}\n"
                f"• **Recent (7d):** {cache_stats.get('cached_last_7_days', 0)}\n"
                f"• **Models Sent:** {cache_stats.get('total_models_sent', 0)}"
            )
            embed['fields'].append({
                "name": "💾 Cache Stats",
                "value": cache_text,
                "inline": False
            })

        payload = {"embeds": [embed]}

        if self.dry_run:
            logger.info("[DRY RUN] Would send summary")
            return True

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 204
        except Exception as e:
            logger.error(f"Error sending summary: {e}")
            return False
