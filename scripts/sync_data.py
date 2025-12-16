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

def sync_data(clear_first=False, full_sync=False):
    """
    Sync data from Tautulli to local database.

    Args:
        clear_first (bool): If True, clear database before syncing
        full_sync (bool): If True, sync entire library and all history
    """
    api = TautulliAPI()

    if clear_first:
        print("Clearing database...")
        api.db.clear_all_data()
        print("✓ Database cleared")

    print("Syncing data from Tautulli (this may take a while)...")

    if full_sync:
        print("\n📚 FULL SYNC MODE")
        print("This will sync:")
        print("  - ALL media items from ALL libraries (with file sizes)")
        print("  - ALL play history records")
        print("\nThis may take several minutes depending on library size...")
    else:
        print("\n📝 INCREMENTAL SYNC MODE")
        print("This will sync:")
        print("  - Recently added media (last 100 items)")
        print("  - Play history (incremental from last sync)")
        print("\nTip: Use --full-sync to sync your entire library")

    print()

    success = api.sync_data(full_sync=full_sync)

    if success:
        print("\n" + "=" * 60)
        print("✓ SYNC COMPLETED SUCCESSFULLY!")
        print("=" * 60)

        # Show some stats
        stats = api.db.get_last_sync_time()
        from datetime import datetime
        if stats['history'] > 0:
            last_sync = datetime.fromtimestamp(stats['history'])
            print(f"\nLast history sync: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")

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

        cursor.execute("SELECT COUNT(*) FROM media_items WHERE file_size IS NOT NULL")
        items_with_size = cursor.fetchone()[0]

        cursor.execute("SELECT ROUND(SUM(file_size)/1024.0/1024.0/1024.0/1024.0, 2) FROM media_items WHERE file_size IS NOT NULL")
        total_size_tb = cursor.fetchone()[0] or 0

        # Breakdown by media type
        cursor.execute("""
            SELECT media_type, COUNT(*) as count,
                   ROUND(SUM(file_size)/1024.0/1024.0/1024.0, 2) as total_gb
            FROM media_items
            WHERE file_size IS NOT NULL
            GROUP BY media_type
            ORDER BY total_gb DESC
        """)
        media_breakdown = cursor.fetchall()

        conn.close()

        print(f"\n📊 DATABASE STATISTICS")
        print(f"  - Media items: {total_media:,}")
        print(f"  - Play history: {total_plays:,}")
        print(f"  - Users: {total_users}")
        print(f"  - Items with file size: {items_with_size:,}")
        print(f"  - Total library size: {total_size_tb:.2f} TB")

        if media_breakdown:
            print(f"\n💾 STORAGE BY TYPE")
            for media_type, count, size_gb in media_breakdown:
                print(f"  - {media_type}: {count:,} items ({size_gb:.2f} GB)")

    else:
        print("\n✗ Sync failed. Check your Tautulli connection in .env file")
        return False

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Plex data from Tautulli")
    parser.add_argument("--clear", action="store_true", help="Clear database before syncing")
    parser.add_argument("--full-sync", action="store_true", help="Sync entire library and all history (not just incremental)")
    args = parser.parse_args()

    sync_data(clear_first=args.clear, full_sync=args.full_sync)
