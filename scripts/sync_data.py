#!/usr/bin/env python3
"""
Sync data from Tautulli to local database.

Usage:
  python sync_data.py              # Incremental sync (only new data since last sync)
  python sync_data.py --clear      # Clear database and do full sync
"""

import sys
from pathlib import Path

# Add project root to path so we can import from src/
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tautulli_api import TautulliAPI
import argparse

def sync_data(clear_first=False):
    """
    Sync data from Tautulli to local database.

    Args:
        clear_first (bool): If True, clear database before syncing
    """
    api = TautulliAPI()

    if clear_first:
        print("Clearing database...")
        api.db.clear_all_data()
        print("✓ Database cleared")

    print("Syncing data from Tautulli (this may take a while)...")
    print("This will sync:")
    print("  - Recently added media (last 100 items)")
    print("  - Play history (incremental from last sync)")
    print()

    success = api.sync_data()

    if success:
        print("\n✓ Sync completed successfully!")

        # Show some stats
        stats = api.db.get_last_sync_time()
        from datetime import datetime
        if stats['history'] > 0:
            last_sync = datetime.fromtimestamp(stats['history'])
            print(f"Last history sync: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")

        # Get counts directly from database
        import sqlite3
        conn = sqlite3.connect("data/plex_stats.db")
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM media_items")
        total_media = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM play_history")
        total_plays = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        conn.close()

        print(f"\nDatabase stats:")
        print(f"  - Media items: {total_media:,}")
        print(f"  - Play history: {total_plays:,}")
        print(f"  - Users: {total_users}")

    else:
        print("\n✗ Sync failed. Check your Tautulli connection in .env file")
        return False

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Plex data from Tautulli")
    parser.add_argument("--clear", action="store_true", help="Clear database before syncing")
    args = parser.parse_args()

    sync_data(clear_first=args.clear)
