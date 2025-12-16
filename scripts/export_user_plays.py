#!/usr/bin/env python3
"""
Export user play history with artist information for tracks.
"""
import sys
from pathlib import Path
import sqlite3
import csv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tautulli_api import TautulliAPI

def export_user_plays(user_id, username, output_file):
    """Export play history for a user with artist info for tracks."""

    api = TautulliAPI()
    conn = sqlite3.connect('data/plex_stats.db')
    cursor = conn.cursor()

    # Get all plays for the user
    query = """
        SELECT
            date(ph.watched_at, 'unixepoch') as watch_date,
            time(ph.watched_at, 'unixepoch') as watch_time,
            mi.title,
            mi.media_type,
            mi.year,
            ph.rating_key,
            ph.watched_at
        FROM play_history ph
        JOIN media_items mi ON ph.rating_key = mi.rating_key
        WHERE ph.user_id = ?
        ORDER BY ph.watched_at DESC
    """

    cursor.execute(query, (user_id,))
    plays = cursor.fetchall()

    print(f"Found {len(plays)} plays for {username}")
    print("Fetching artist information for tracks...")

    # Get unique track rating keys to batch fetch artist info
    track_rating_keys = set()
    for play in plays:
        media_type = play[3]
        rating_key = play[5]
        if media_type == 'track':
            track_rating_keys.add(rating_key)

    # Fetch artist info for all tracks
    artist_cache = {}
    total_tracks = len(track_rating_keys)
    print(f"Fetching metadata for {total_tracks} unique tracks...")

    for i, rating_key in enumerate(track_rating_keys, 1):
        if i % 10 == 0 or i == total_tracks:
            print(f"  Progress: {i}/{total_tracks}")

        try:
            metadata = api._make_request('get_metadata', rating_key=str(rating_key))
            if metadata:
                track_data = metadata.get('response', {}).get('data', {})
                artist = track_data.get('grandparent_title', '')
                album = track_data.get('parent_title', '')
                artist_cache[rating_key] = {
                    'artist': artist,
                    'album': album
                }
        except Exception as e:
            print(f"  Warning: Could not fetch metadata for rating_key {rating_key}: {e}")
            artist_cache[rating_key] = {'artist': '', 'album': ''}

    # Write CSV
    print(f"Writing to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow(['watch_date', 'watch_time', 'title', 'media_type', 'year', 'artist', 'album'])

        # Data
        for play in plays:
            watch_date, watch_time, title, media_type, year, rating_key, _ = play

            artist = ''
            album = ''
            if media_type == 'track' and rating_key in artist_cache:
                artist = artist_cache[rating_key]['artist']
                album = artist_cache[rating_key]['album']

            writer.writerow([watch_date, watch_time, title, media_type, year, artist, album])

    conn.close()
    print(f"✓ Export complete! {len(plays)} plays written to {output_file}")

if __name__ == '__main__':
    # blackbox.a
    export_user_plays('452892880', 'blackbox.a', 'outputs/blackbox_a_plays.csv')
