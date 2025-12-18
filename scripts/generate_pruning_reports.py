#!/usr/bin/env python3
"""
Generate CSV reports for library pruning decisions.

Outputs:
  - outputs/movies_least_accessed.csv: Movies sorted by least plays
  - outputs/tvshows_least_accessed.csv: TV shows aggregated by series, sorted by least plays
"""

import sqlite3
import csv
from pathlib import Path

DB_PATH = "data/plex_stats.db"
OUTPUT_DIR = Path("outputs")

def format_size_gb(bytes_size):
    """Convert bytes to GB with 2 decimal places"""
    if bytes_size is None:
        return 0.0
    return round(bytes_size / (1024 ** 3), 2)

def generate_movies_csv():
    """Generate CSV of movies sorted by least plays"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get movies with play counts and users who accessed them
    cursor.execute("""
        SELECT
            m.title,
            m.year,
            m.file_size,
            COALESCE(COUNT(ph.id), 0) as play_count,
            COUNT(DISTINCT u.friendly_name) as unique_users,
            GROUP_CONCAT(DISTINCT u.friendly_name) as users_accessed
        FROM media_items m
        LEFT JOIN play_history ph ON m.rating_key = ph.rating_key
        LEFT JOIN users u ON ph.user_id = u.user_id
        WHERE m.media_type = 'movie'
        GROUP BY m.rating_key
        ORDER BY play_count ASC, m.title ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / "movies_least_accessed.csv"

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        # Use QUOTE_NONNUMERIC to ensure titles are always quoted (fixes alignment in spreadsheets)
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(['title', 'year', 'play_count', 'unique_users', 'users_accessed', 'file_size_gb'])

        for row in rows:
            writer.writerow([
                row['title'],
                row['year'] or '',
                row['play_count'],
                row['unique_users'],
                row['users_accessed'] or '',
                format_size_gb(row['file_size'])
            ])

    print(f"Movies CSV written to {output_path}")
    print(f"  Total movies: {len(rows)}")
    never_played = sum(1 for r in rows if r['play_count'] == 0)
    print(f"  Never played: {never_played}")

def generate_tvshows_csv():
    """Generate CSV of TV shows aggregated by series, sorted by least plays"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get TV shows aggregated by grandparent (show)
    # We join episodes to their parent show via grandparent_rating_key
    cursor.execute("""
        SELECT
            show.title as show_title,
            show.year,
            COUNT(DISTINCT ep.rating_key) as episode_count,
            COALESCE(SUM(ep.file_size), 0) as total_size,
            COALESCE(COUNT(ph.id), 0) as total_plays,
            COUNT(DISTINCT u.friendly_name) as unique_users,
            GROUP_CONCAT(DISTINCT u.friendly_name) as users_accessed
        FROM media_items show
        LEFT JOIN media_items ep ON ep.grandparent_rating_key = show.rating_key AND ep.media_type = 'episode'
        LEFT JOIN play_history ph ON ep.rating_key = ph.rating_key
        LEFT JOIN users u ON ph.user_id = u.user_id
        WHERE show.media_type = 'show'
        GROUP BY show.rating_key
        ORDER BY total_plays ASC, show.title ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / "tvshows_least_accessed.csv"

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        # Use QUOTE_NONNUMERIC to ensure titles are always quoted (fixes alignment in spreadsheets)
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(['title', 'year', 'episode_count', 'total_size_gb', 'total_plays', 'unique_users', 'users_accessed'])

        for row in rows:
            writer.writerow([
                row['show_title'],
                row['year'] or '',
                row['episode_count'],
                format_size_gb(row['total_size']),
                row['total_plays'],
                row['unique_users'],
                row['users_accessed'] or ''
            ])

    print(f"TV Shows CSV written to {output_path}")
    print(f"  Total shows: {len(rows)}")
    never_played = sum(1 for r in rows if r['total_plays'] == 0)
    print(f"  Never played: {never_played}")

if __name__ == "__main__":
    print("Generating pruning reports...\n")
    generate_movies_csv()
    print()
    generate_tvshows_csv()
    print("\nDone!")
