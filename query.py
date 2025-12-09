#!/usr/bin/env python3
"""
Simple database query tool for Plex stats.

Usage:
  python query.py              # Run the query defined below
  python query.py --schema     # Show database structure

Edit the SQL query below, then run: python query.py
"""

import sqlite3
from datetime import datetime

# ============================================================
# EDIT YOUR SQL QUERY HERE:
# ============================================================

QUERY = """
WITH top_users AS (
    SELECT ph.user_id, u.username
    FROM play_history ph
    JOIN users u ON ph.user_id = u.user_id
    GROUP BY ph.user_id, u.username
    ORDER BY COUNT(*) DESC
    LIMIT 2
),
all_months AS (
    SELECT DISTINCT strftime('%Y-%m', watched_at, 'unixepoch', 'localtime') as month
    FROM play_history
    WHERE strftime('%Y', watched_at, 'unixepoch', 'localtime') = '2025'
)
SELECT
    am.month,
    (SELECT username FROM top_users LIMIT 1) as user1_name,
    COALESCE((
        SELECT COUNT(*)
        FROM play_history
        WHERE user_id = (SELECT user_id FROM top_users LIMIT 1)
            AND strftime('%Y-%m', watched_at, 'unixepoch', 'localtime') = am.month
    ), 0) as user1_plays,
    (SELECT username FROM top_users LIMIT 1 OFFSET 1) as user2_name,
    COALESCE((
        SELECT COUNT(*)
        FROM play_history
        WHERE user_id = (SELECT user_id FROM top_users LIMIT 1 OFFSET 1)
            AND strftime('%Y-%m', watched_at, 'unixepoch', 'localtime') = am.month
    ), 0) as user2_plays
FROM all_months am
ORDER BY am.month
"""

# ============================================================
# Database connection and query execution
# ============================================================

DB_PATH = "data/plex_stats.db"

def format_timestamp(ts):
    """Convert Unix timestamp to readable date"""
    if ts:
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    return None

def run_query(sql):
    """Execute SQL query and display results"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        results = cursor.fetchall()

        if not results:
            print("No results found.")
            return

        # Get column names
        columns = results[0].keys()

        # Calculate column widths
        widths = {}
        for col in columns:
            widths[col] = max(
                len(str(col)),
                max(len(str(row[col])) for row in results)
            )

        # Print header
        header = " | ".join(str(col).ljust(widths[col]) for col in columns)
        print("\n" + header)
        print("-" * len(header))

        # Print rows
        for row in results:
            print(" | ".join(str(row[col]).ljust(widths[col]) for col in columns))

        print(f"\nTotal results: {len(results)}")

    except sqlite3.Error as e:
        print(f"SQL Error: {e}")
    finally:
        conn.close()

def show_schema():
    """Display database schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n=== DATABASE SCHEMA ===\n")

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    for table in tables:
        table_name = table[0]
        print(f"\n{table_name}:")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            col_name, col_type = col[1], col[2]
            print(f"  - {col_name} ({col_type})")

    conn.close()

# ============================================================
# USEFUL QUERY EXAMPLES (uncomment to use):
# ============================================================

# Top users by play count:
# QUERY = """
# SELECT user_id, COUNT(*) as plays
# FROM play_history
# GROUP BY user_id
# ORDER BY plays DESC
# LIMIT 10
# """

# Second most active user:
# QUERY = """
# SELECT user_id, COUNT(*) as plays
# FROM play_history
# GROUP BY user_id
# ORDER BY plays DESC
# LIMIT 1 OFFSET 1
# """

# Plays per day (last 30 days):
# QUERY = """
# SELECT
#     DATE(watched_at, 'unixepoch', 'localtime') as date,
#     COUNT(*) as plays
# FROM play_history
# WHERE watched_at > strftime('%s', 'now', '-30 days')
# GROUP BY date
# ORDER BY date DESC
# """

# Most watched content:
# QUERY = """
# SELECT
#     m.title,
#     m.media_type,
#     COUNT(*) as plays
# FROM play_history ph
# JOIN media_items m ON ph.rating_key = m.rating_key
# GROUP BY ph.rating_key
# ORDER BY plays DESC
# LIMIT 20
# """

# Specific user's activity:
# QUERY = """
# SELECT
#     m.title,
#     m.media_type,
#     COUNT(*) as plays,
#     SUM(ph.duration) as total_minutes
# FROM play_history ph
# JOIN media_items m ON ph.rating_key = m.rating_key
# WHERE ph.user_id = 'rakbarut'
# GROUP BY ph.rating_key
# ORDER BY plays DESC
# LIMIT 20
# """

# Plays by hour of day:
# QUERY = """
# SELECT
#     strftime('%H', watched_at, 'unixepoch', 'localtime') as hour,
#     COUNT(*) as plays
# FROM play_history
# GROUP BY hour
# ORDER BY hour
# """

# Plays by day of week:
# QUERY = """
# SELECT
#     CASE CAST(strftime('%w', watched_at, 'unixepoch', 'localtime') AS INTEGER)
#         WHEN 0 THEN 'Sunday'
#         WHEN 1 THEN 'Monday'
#         WHEN 2 THEN 'Tuesday'
#         WHEN 3 THEN 'Wednesday'
#         WHEN 4 THEN 'Thursday'
#         WHEN 5 THEN 'Friday'
#         WHEN 6 THEN 'Saturday'
#     END as day_of_week,
#     COUNT(*) as plays
# FROM play_history
# GROUP BY strftime('%w', watched_at, 'unixepoch', 'localtime')
# ORDER BY CAST(strftime('%w', watched_at, 'unixepoch', 'localtime') AS INTEGER)
# """

# Library stats:
# QUERY = """
# SELECT
#     media_type,
#     COUNT(*) as count
# FROM media_items
# GROUP BY media_type
# ORDER BY count DESC
# """

# ============================================================

if __name__ == "__main__":
    import sys

    # Show schema if requested
    if len(sys.argv) > 1 and sys.argv[1] == "--schema":
        show_schema()
    else:
        print("\nRunning query...")
        print("=" * 60)
        run_query(QUERY)
        print("\nTip: Run 'python query.py --schema' to see database structure")
        print("=" * 60)
