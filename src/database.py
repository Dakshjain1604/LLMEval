"""Database management for tracking discovered releases."""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ReleaseDatabase:
    """Manages SQLite database for tracking discovered releases."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS releases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                item_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                description TEXT,
                metadata TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                relevance_score INTEGER,
                relevance_dim INTEGER,
                quality_dim INTEGER,
                novelty_dim INTEGER,
                evaluability_dim INTEGER,
                impact_dim INTEGER,
                confidence REAL,
                composite_score REAL,
                reasoning TEXT,
                filtered_out BOOLEAN DEFAULT 0,
                sent_to_discord BOOLEAN DEFAULT 0,
                UNIQUE(platform, item_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_platform_item
            ON releases(platform, item_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_discovered_at
            ON releases(discovered_at)
        """)

        conn.commit()
        conn.close()

        # Run migrations to add new columns if they don't exist
        self._run_migrations()

    def _run_migrations(self):
        """Run database migrations to add new columns if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get existing columns
        cursor.execute("PRAGMA table_info(releases)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # Define new columns with their types
        new_columns = {
            'relevance_dim': 'INTEGER',
            'quality_dim': 'INTEGER',
            'novelty_dim': 'INTEGER',
            'evaluability_dim': 'INTEGER',
            'impact_dim': 'INTEGER',
            'confidence': 'REAL',
            'composite_score': 'REAL',
            'reasoning': 'TEXT'
        }

        # Add missing columns
        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE releases ADD COLUMN {column_name} {column_type}")
                    logger.info(f"Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    logger.warning(f"Could not add column {column_name}: {e}")

        conn.commit()
        conn.close()

    def is_seen(self, platform: str, item_id: str) -> bool:
        """Check if an item has been seen before."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1 FROM releases WHERE platform = ? AND item_id = ? LIMIT 1",
            (platform, item_id)
        )
        result = cursor.fetchone()
        conn.close()

        return result is not None

    def add_release(
        self,
        platform: str,
        item_id: str,
        title: str,
        url: str,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        relevance_score: Optional[int] = None,
        filtered_out: bool = False,
        dimensions: Optional[Dict] = None
    ):
        """Add a new release to the database.

        Args:
            dimensions: Dict with keys: relevance, quality, novelty, evaluability, impact, confidence, reasoning
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Extract dimension values if provided
        relevance_dim = None
        quality_dim = None
        novelty_dim = None
        evaluability_dim = None
        impact_dim = None
        confidence = None
        composite_score = None
        reasoning = None

        if dimensions:
            relevance_dim = dimensions.get('relevance')
            quality_dim = dimensions.get('quality')
            novelty_dim = dimensions.get('novelty')
            evaluability_dim = dimensions.get('evaluability')
            impact_dim = dimensions.get('impact')
            confidence = dimensions.get('confidence')
            composite_score = relevance_score  # Use the relevance_score as composite_score
            reasoning = dimensions.get('reasoning')

        try:
            cursor.execute("""
                INSERT INTO releases
                (platform, item_id, title, url, description, metadata, relevance_score,
                 relevance_dim, quality_dim, novelty_dim, evaluability_dim, impact_dim,
                 confidence, composite_score, reasoning, filtered_out)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                platform,
                item_id,
                title,
                url,
                description,
                json.dumps(metadata) if metadata else None,
                relevance_score,
                relevance_dim,
                quality_dim,
                novelty_dim,
                evaluability_dim,
                impact_dim,
                confidence,
                composite_score,
                reasoning,
                filtered_out
            ))
            conn.commit()
            logger.debug(f"Added release: {platform}/{item_id}")
        except sqlite3.IntegrityError:
            logger.debug(f"Release already exists: {platform}/{item_id}")
        finally:
            conn.close()

    def mark_sent(self, platform: str, item_id: str):
        """Mark an item as sent to Discord."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE releases
            SET sent_to_discord = 1
            WHERE platform = ? AND item_id = ?
        """, (platform, item_id))

        conn.commit()
        conn.close()

    def get_unsent_releases(self, limit: Optional[int] = None) -> List[Dict]:
        """Get releases that passed filtering but haven't been sent yet."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT * FROM releases
            WHERE filtered_out = 0 AND sent_to_discord = 0
            ORDER BY relevance_score DESC, discovered_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        # Parse metadata JSON
        for result in results:
            if result['metadata']:
                result['metadata'] = json.loads(result['metadata'])

        return results

    def cleanup_old_entries(self, retention_days: int):
        """Remove entries older than retention period."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        cursor.execute(
            "DELETE FROM releases WHERE discovered_at < ?",
            (cutoff_date.isoformat(),)
        )

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old entries")

    def get_stats(self) -> Dict:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM releases")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM releases WHERE filtered_out = 0")
        passed_filter = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM releases WHERE sent_to_discord = 1")
        sent = cursor.fetchone()[0]

        cursor.execute("""
            SELECT platform, COUNT(*) as count
            FROM releases
            GROUP BY platform
        """)
        by_platform = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return {
            "total": total,
            "passed_filter": passed_filter,
            "sent": sent,
            "by_platform": by_platform
        }
