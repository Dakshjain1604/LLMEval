"""Generate reports for releases."""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict


class ReportGenerator:
    """Generate reports in various formats."""

    def __init__(self, output_dir: str = "data/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_json_report(self, releases: List[Dict], filename: str = None) -> str:
        """Generate JSON report with all release data.

        Args:
            releases: List of release dictionaries
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to generated JSON file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"releases_{timestamp}.json"

        output_path = self.output_dir / filename

        report_data = {
            "generated_at": datetime.now().isoformat(),
            "total_count": len(releases),
            "releases": [
                {
                    "title": r.get('title'),
                    "url": r.get('url'),
                    "platform": r.get('platform'),
                    "description": r.get('description'),
                    "relevance_score": r.get('relevance_score'),
                    "metadata": r.get('metadata'),
                    "discovered_at": r.get('discovered_at'),
                }
                for r in releases
            ],
            "by_platform": self._group_by_platform(releases),
            "by_score": self._group_by_score(releases),
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        return str(output_path)

    def generate_csv_report(self, releases: List[Dict], filename: str = None) -> str:
        """Generate CSV report with all release data.

        Args:
            releases: List of release dictionaries
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to generated CSV file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"releases_{timestamp}.csv"

        output_path = self.output_dir / filename

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Title', 'URL', 'Platform', 'Type', 'Score',
                'Description', 'Discovered At'
            ])

            for r in releases:
                metadata = r.get('metadata', {})
                writer.writerow([
                    r.get('title', ''),
                    r.get('url', ''),
                    r.get('platform', ''),
                    metadata.get('type', ''),
                    r.get('relevance_score', 0),
                    r.get('description', '')[:200],  # Truncate
                    r.get('discovered_at', ''),
                ])

        return str(output_path)

    def generate_markdown_report(self, releases: List[Dict], filename: str = None) -> str:
        """Generate Markdown report with all release data.

        Args:
            releases: List of release dictionaries
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to generated Markdown file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"releases_{timestamp}.md"

        output_path = self.output_dir / filename

        lines = [
            f"# AI/ML Releases Report",
            f"",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Releases:** {len(releases)}",
            f"",
        ]

        # Group by platform
        by_platform = self._group_by_platform(releases)

        for platform, count in sorted(by_platform.items()):
            lines.append(f"## {platform.upper()} ({count} releases)")
            lines.append("")

            platform_releases = [r for r in releases if r.get('platform') == platform]
            platform_releases.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

            for idx, release in enumerate(platform_releases, 1):
                title = release.get('title', 'Unknown')
                url = release.get('url', '')
                score = release.get('relevance_score', 0)
                description = release.get('description', '')[:150]

                lines.append(f"### {idx}. [{title}]({url})")
                lines.append(f"**Score:** {score}/100")
                lines.append(f"**Description:** {description}...")
                lines.append("")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return str(output_path)

    def _group_by_platform(self, releases: List[Dict]) -> Dict[str, int]:
        """Group releases by platform."""
        by_platform = {}
        for r in releases:
            platform = r.get('platform', 'unknown')
            by_platform[platform] = by_platform.get(platform, 0) + 1
        return by_platform

    def _group_by_score(self, releases: List[Dict]) -> Dict[str, int]:
        """Group releases by score range."""
        by_score = {
            "80-100": 0,
            "60-79": 0,
            "40-59": 0,
            "0-39": 0,
        }

        for r in releases:
            score = r.get('relevance_score', 0)
            if score >= 80:
                by_score["80-100"] += 1
            elif score >= 60:
                by_score["60-79"] += 1
            elif score >= 40:
                by_score["40-59"] += 1
            else:
                by_score["0-39"] += 1

        return by_score
