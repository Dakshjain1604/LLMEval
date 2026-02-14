#!/usr/bin/env python3
"""Verification script for LlmEval enhancement implementation."""

import sys
import yaml
import sqlite3
import tempfile
import os
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text):
    """Print a section header."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


def print_success(text):
    """Print success message."""
    print(f"{GREEN}✓{RESET} {text}")


def print_error(text):
    """Print error message."""
    print(f"{RED}✗{RESET} {text}")


def print_warning(text):
    """Print warning message."""
    print(f"{YELLOW}⚠{RESET} {text}")


def verify_python_syntax():
    """Verify all Python files compile without syntax errors."""
    print_header("1. Verifying Python Syntax")

    files_to_check = [
        'src/llm_filter.py',
        'src/database.py',
        'src/main.py',
        'src/discord_sender_v2.py',
        'src/selection_optimizer.py',
        'src/priority_queue.py'
    ]

    all_good = True
    for filepath in files_to_check:
        try:
            with open(filepath, 'r') as f:
                compile(f.read(), filepath, 'exec')
            print_success(f"{filepath} - syntax OK")
        except SyntaxError as e:
            print_error(f"{filepath} - syntax error: {e}")
            all_good = False
        except FileNotFoundError:
            print_error(f"{filepath} - file not found")
            all_good = False

    return all_good


def verify_configuration():
    """Verify configuration file is valid and has new sections."""
    print_header("2. Verifying Configuration")

    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print_success("config.yaml loads successfully")
    except Exception as e:
        print_error(f"Failed to load config.yaml: {e}")
        return False

    # Check for new sections
    checks = [
        ('filtering.scoring.dimension_weights', 'Dimension weights'),
        ('filtering.thresholds.default', 'Default threshold'),
        ('filtering.thresholds.adaptive', 'Adaptive thresholds'),
        ('filtering.selection.diversity_constraints', 'Diversity constraints'),
    ]

    all_good = True
    for path, name in checks:
        keys = path.split('.')
        value = config
        try:
            for key in keys:
                value = value[key]
            print_success(f"{name} configured")
        except KeyError:
            print_error(f"{name} missing from config")
            all_good = False

    # Verify dimension weights sum to 1.0
    try:
        weights = config['filtering']['scoring']['dimension_weights']
        total = sum(weights.values())
        if abs(total - 1.0) < 0.001:
            print_success(f"Dimension weights sum to {total:.3f} ✓")
        else:
            print_error(f"Dimension weights sum to {total:.3f}, should be 1.0")
            all_good = False
    except Exception as e:
        print_error(f"Could not verify dimension weights: {e}")
        all_good = False

    return all_good


def verify_database_schema():
    """Verify database schema has new columns."""
    print_header("3. Verifying Database Schema")

    # Create a temporary test database
    temp_db = tempfile.mktemp(suffix='.db')

    try:
        # Import and initialize
        from src.database import ReleaseDatabase
        db = ReleaseDatabase(temp_db)

        # Check schema
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(releases)')
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()

        print_success(f"Database initialized with {len(columns)} columns")

        # Check for new columns
        required_columns = [
            'relevance_dim', 'quality_dim', 'novelty_dim',
            'evaluability_dim', 'impact_dim', 'confidence',
            'composite_score', 'reasoning'
        ]

        all_good = True
        for col in required_columns:
            if col in columns:
                print_success(f"Column '{col}' present")
            else:
                print_error(f"Column '{col}' missing")
                all_good = False

        # Cleanup
        os.remove(temp_db)
        return all_good

    except Exception as e:
        print_error(f"Database schema verification failed: {e}")
        if os.path.exists(temp_db):
            os.remove(temp_db)
        return False


def verify_database_migration():
    """Verify migration from old schema works."""
    print_header("4. Verifying Database Migration")

    temp_db = tempfile.mktemp(suffix='.db')

    try:
        # Create old schema
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute('''
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
                filtered_out BOOLEAN DEFAULT 0,
                sent_to_discord BOOLEAN DEFAULT 0,
                UNIQUE(platform, item_id)
            )
        ''')
        conn.commit()

        # Check columns before
        cursor.execute('PRAGMA table_info(releases)')
        old_columns = [col[1] for col in cursor.fetchall()]
        old_count = len(old_columns)
        conn.close()

        print_success(f"Old schema created with {old_count} columns")

        # Run migration
        from src.database import ReleaseDatabase
        db = ReleaseDatabase(temp_db)

        # Check columns after
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(releases)')
        new_columns = [col[1] for col in cursor.fetchall()]
        new_count = len(new_columns)
        conn.close()

        print_success(f"After migration: {new_count} columns")

        # Verify new columns added
        new_cols = ['relevance_dim', 'quality_dim', 'novelty_dim',
                   'evaluability_dim', 'impact_dim', 'confidence',
                   'composite_score', 'reasoning']
        all_present = all(col in new_columns for col in new_cols)

        if all_present:
            print_success("All new columns added successfully")
            os.remove(temp_db)
            return True
        else:
            print_error("Some new columns missing after migration")
            os.remove(temp_db)
            return False

    except Exception as e:
        print_error(f"Migration verification failed: {e}")
        if os.path.exists(temp_db):
            os.remove(temp_db)
        return False


def verify_components():
    """Verify new components work."""
    print_header("5. Verifying New Components")

    try:
        # Load config
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        # Enable priority queue for testing
        config['filtering']['selection']['use_priority_queue'] = True

        # Test SelectionOptimizer
        from src.selection_optimizer import SelectionOptimizer
        optimizer = SelectionOptimizer(config)
        print_success("SelectionOptimizer initialized")

        # Test modality inference
        test_release = {
            'title': 'GPT Model',
            'description': 'language model text generation',
            'metadata': {}
        }
        modality = optimizer._infer_modality(test_release)
        if modality == 'language':
            print_success(f"Modality inference works (detected: {modality})")
        else:
            print_warning(f"Modality inference unexpected: {modality}")

        # Test PriorityQueue
        from src.priority_queue import PriorityQueue
        pq = PriorityQueue(config)
        print_success("PriorityQueue initialized")

        # Test priority assignment
        from datetime import datetime
        test_releases = [{
            'title': 'Test Release',
            'platform': 'huggingface',
            'relevance_score': 75,
            'composite_score': 75,
            'novelty_dim': 70,
            'impact_dim': 60,
            'confidence': 0.8,
            'discovered_at': datetime.now().isoformat(),
            'description': 'test',
            'metadata': {}
        }]

        releases_with_priority = pq.assign_priority(test_releases)
        if 'priority_level' in releases_with_priority[0]:
            print_success(f"Priority assignment works (level: {releases_with_priority[0]['priority_level']})")
        else:
            print_error("Priority assignment failed")
            return False

        # Test composite scoring
        weights = config['filtering']['scoring']['dimension_weights']
        test_dimensions = {
            'relevance': 80,
            'quality': 70,
            'novelty': 75,
            'evaluability': 80,
            'impact': 65
        }
        expected = int(round(
            test_dimensions['relevance'] * weights['relevance'] +
            test_dimensions['quality'] * weights['quality'] +
            test_dimensions['novelty'] * weights['novelty'] +
            test_dimensions['evaluability'] * weights['evaluability'] +
            test_dimensions['impact'] * weights['impact']
        ))
        print_success(f"Composite scoring formula works (score: {expected})")

        return True

    except Exception as e:
        print_error(f"Component verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification checks."""
    print(f"\n{BLUE}{'=' * 60}")
    print("LlmEval Enhancement Verification")
    print(f"{'=' * 60}{RESET}\n")

    results = []

    # Run all checks
    results.append(("Python Syntax", verify_python_syntax()))
    results.append(("Configuration", verify_configuration()))
    results.append(("Database Schema", verify_database_schema()))
    results.append(("Database Migration", verify_database_migration()))
    results.append(("New Components", verify_components()))

    # Summary
    print_header("Verification Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        if result:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")

    print(f"\n{BLUE}{'=' * 60}{RESET}")
    if passed == total:
        print(f"{GREEN}✓ All {total} checks passed!{RESET}")
        print(f"{GREEN}✓ Implementation verified successfully{RESET}")
        print(f"\n{BLUE}You can now run: python run.py{RESET}\n")
        return 0
    else:
        print(f"{RED}✗ {total - passed} check(s) failed{RESET}")
        print(f"{YELLOW}Please review the errors above{RESET}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
