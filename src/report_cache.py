"""Report caching system to prevent duplicate reports."""

import hashlib
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ReportCache:
    """Manages caching of sent reports to prevent duplicates."""

    def __init__(self, db_path: str = "data/releases.db"):
        self.db_path = Path(db_path)
        self._init_cache_table()

    def _init_cache_table(self):
        """Initialize report cache table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS report_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_hash TEXT UNIQUE NOT NULL,
                content_summary TEXT NOT NULL,
                release_ids TEXT NOT NULL,
                platform_summary TEXT NOT NULL,
                model_count INTEGER NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                report_files TEXT,
                discord_sent BOOLEAN DEFAULT 1
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_report_hash
            ON report_cache(report_hash)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sent_at
            ON report_cache(sent_at)
        """)

        conn.commit()
        conn.close()

    def _compute_report_hash(self, releases: List[Dict]) -> str:
        """Compute hash for a set of releases.

        Hash is based on:
        - Platform + item_id combinations (unique identifiers)
        - Sorted to ensure consistent hashing
        """
        release_keys = sorted([
            f"{r.get('platform', '')}:{r.get('item_id', '')}"
            for r in releases
        ])

        hash_input = json.dumps(release_keys, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def is_report_sent(self, releases: List[Dict]) -> Tuple[bool, Optional[Dict]]:
        """Check if a report with these exact releases was already sent.

        Args:
            releases: List of release dictionaries

        Returns:
            Tuple of (is_sent, cached_report_info)
        """
        if not releases:
            return False, None

        report_hash = self._compute_report_hash(releases)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM report_cache
            WHERE report_hash = ?
            ORDER BY sent_at DESC
            LIMIT 1
        """, (report_hash,))

        result = cursor.fetchone()
        conn.close()

        if result:
            cached_info = dict(result)
            logger.info(f"Found cached report from {cached_info['sent_at']}")
            return True, cached_info

        return False, None

    def cache_report(
        self,
        releases: List[Dict],
        report_files: Dict[str, str] = None,
        discord_sent: bool = True
    ) -> str:
        """Cache a sent report.

        Args:
            releases: List of release dictionaries
            report_files: Dict of report type -> file path
            discord_sent: Whether report was sent to Discord

        Returns:
            Report hash
        """
        if not releases:
            return None

        report_hash = self._compute_report_hash(releases)

        # Build summary
        platform_counts = {}
        for r in releases:
            platform = r.get('platform', 'unknown')
            platform_counts[platform] = platform_counts.get(platform, 0) + 1

        platform_summary = json.dumps(platform_counts)

        # Get release IDs
        release_ids = json.dumps([
            {
                'platform': r.get('platform'),
                'item_id': r.get('item_id'),
                'title': r.get('title', '')[:100],
                'score': r.get('relevance_score', 0)
            }
            for r in releases
        ])

        # Content summary
        high_priority = len([r for r in releases if r.get('relevance_score', 0) >= 80])
        content_summary = f"{len(releases)} releases ({high_priority} high priority) from {len(platform_counts)} platforms"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO report_cache
                (report_hash, content_summary, release_ids, platform_summary,
                 model_count, report_files, discord_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                report_hash,
                content_summary,
                release_ids,
                platform_summary,
                len(releases),
                json.dumps(report_files) if report_files else None,
                discord_sent
            ))
            conn.commit()
            logger.info(f"Cached report: {content_summary}")
        except sqlite3.IntegrityError:
            logger.debug(f"Report already cached: {report_hash}")
        finally:
            conn.close()

        return report_hash

    def get_cached_report_files(self, report_hash: str) -> Optional[Dict[str, str]]:
        """Get cached report file paths.

        Args:
            report_hash: Hash of the report

        Returns:
            Dict of report type -> file path, or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT report_files FROM report_cache
            WHERE report_hash = ?
        """, (report_hash,))

        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            return json.loads(result[0])
        return None

    def get_recent_reports(self, days: int = 7) -> List[Dict]:
        """Get recently sent reports.

        Args:
            days: Number of days to look back

        Returns:
            List of recent report summaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM report_cache
            WHERE sent_at >= datetime('now', '-' || ? || ' days')
            ORDER BY sent_at DESC
        """, (days,))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def cleanup_old_cache(self, retention_days: int = 30):
        """Remove cached reports older than retention period.

        Args:
            retention_days: Number of days to retain cache
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM report_cache
            WHERE sent_at < datetime('now', '-' || ? || ' days')
        """, (retention_days,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old cached reports")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM report_cache")
        total_cached = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM report_cache
            WHERE sent_at >= datetime('now', '-7 days')
        """)
        recent_cached = cursor.fetchone()[0]

        cursor.execute("""
            SELECT SUM(model_count) FROM report_cache
        """)
        total_models_sent = cursor.fetchone()[0] or 0

        conn.close()

        return {
            "total_cached_reports": total_cached,
            "cached_last_7_days": recent_cached,
            "total_models_sent": total_models_sent
        }
