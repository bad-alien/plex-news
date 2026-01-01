#!/usr/bin/env python3
"""
Generate decoded_manifest.json for Blackbox Decoded 2025 Year in Review.

This script queries the local Plex stats database and generates a JSON manifest
that can be consumed by the badalien.works website for the interactive experience.

Outputs:
    - outputs/decoded_manifest.json
    - outputs/decoded_assets/*.jpg (poster images)
"""

import json
import sqlite3
import re
import sys
import requests
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tautulli_api import TautulliAPI

# Configuration
DB_PATH = project_root / 'data' / 'plex_stats.db'
OUTPUT_JSON = project_root / 'outputs' / 'decoded_manifest.json'
ASSETS_DIR = project_root / 'outputs' / 'decoded_assets'
YEAR = 2025

# Day name mapping (SQLite strftime('%w') returns 0=Sunday)
DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']


def to_kebab_case(title):
    """Convert a title to kebab-case for file naming."""
    # Remove special characters, replace spaces with hyphens
    clean = re.sub(r'[^\w\s-]', '', title.lower())
    clean = re.sub(r'[\s_]+', '-', clean)
    clean = re.sub(r'-+', '-', clean).strip('-')
    return clean


def download_poster(thumb_path, output_path, api):
    """Download a poster image from Tautulli."""
    if not thumb_path:
        print(f"    No thumb path for {output_path.name}")
        return False

    try:
        url = f"{api.base_url}/pms_image_proxy"
        params = {
            'img': thumb_path,
            'width': 800,
            'height': 1200,
            'fallback': 'poster'
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200 and response.headers.get('content-type', '').startswith('image'):
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        else:
            print(f"  Failed to download {output_path.name}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  Error downloading {output_path.name}: {e}")
        return False


def download_user_avatar(user_thumb, output_path, api):
    """Download a user avatar from Tautulli."""
    if not user_thumb:
        return False

    try:
        # User thumbs are typically full URLs or can be fetched via pms_image_proxy
        if user_thumb.startswith('http'):
            response = requests.get(user_thumb, timeout=10)
        else:
            url = f"{api.base_url}/pms_image_proxy"
            params = {
                'img': user_thumb,
                'width': 400,
                'height': 400,
                'fallback': 'user'
            }
            response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        return False
    except Exception as e:
        print(f"  Error downloading user avatar: {e}")
        return False


def get_library_growth_data(conn):
    """Get cumulative library growth by day for 2025."""
    cursor = conn.cursor()

    query = """
        SELECT
            DATE(added_at, 'unixepoch') as add_date,
            media_type,
            COUNT(*) as count
        FROM media_items
        WHERE media_type IN ('movie', 'season', 'album')
            AND added_at IS NOT NULL
            AND strftime('%Y', added_at, 'unixepoch') = ?
        GROUP BY add_date, media_type
        ORDER BY add_date
    """

    cursor.execute(query, (str(YEAR),))
    rows = cursor.fetchall()

    # Organize by date
    daily_data = defaultdict(lambda: {'movies': 0, 'seasons': 0, 'albums': 0})

    for row in rows:
        add_date = row['add_date']
        media_type = row['media_type']
        count = row['count']

        if media_type == 'movie':
            daily_data[add_date]['movies'] = count
        elif media_type == 'season':
            daily_data[add_date]['seasons'] = count
        elif media_type == 'album':
            daily_data[add_date]['albums'] = count

    # Generate all days of the year and build cumulative data
    from datetime import date, timedelta

    start_date = date(YEAR, 1, 1)
    end_date = date(YEAR, 12, 31)

    cumulative = {'movies': 0, 'seasons': 0, 'albums': 0}
    result = []

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')

        # Add daily counts to cumulative
        cumulative['movies'] += daily_data[date_str]['movies']
        cumulative['seasons'] += daily_data[date_str]['seasons']
        cumulative['albums'] += daily_data[date_str]['albums']

        # Format date label as "Jan 1", "Jan 2", etc.
        date_label = current_date.strftime('%b %-d')

        result.append({
            'date': date_label,
            'movies': cumulative['movies'],
            'seasons': cumulative['seasons'],
            'albums': cumulative['albums']
        })

        current_date += timedelta(days=1)

    return result


def get_weekly_pattern_data(conn):
    """Get server-wide usage pattern by day of week and hour (in minutes)."""
    cursor = conn.cursor()

    query = """
        SELECT
            CAST(strftime('%w', watched_at, 'unixepoch', 'localtime') AS INTEGER) as day_num,
            CAST(strftime('%H', watched_at, 'unixepoch', 'localtime') AS INTEGER) as hour,
            SUM(duration) / 60 as total_minutes
        FROM play_history
        WHERE strftime('%Y', watched_at, 'unixepoch', 'localtime') = ?
        GROUP BY day_num, hour
        ORDER BY day_num, hour
    """

    cursor.execute(query, (str(YEAR),))
    rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            'day': DAY_NAMES[row['day_num']],
            'hour': row['hour'],
            'value': row['total_minutes'] or 0
        })

    return result


def get_top_movies(conn, limit=3):
    """Get top movies by unique viewers, including viewer names."""
    cursor = conn.cursor()

    query = """
        SELECT
            m.rating_key,
            m.title,
            m.year,
            m.thumb,
            COUNT(DISTINCT ph.user_id) as unique_viewers,
            GROUP_CONCAT(DISTINCT u.friendly_name) as viewer_names
        FROM media_items m
        JOIN play_history ph ON m.rating_key = ph.rating_key
        JOIN users u ON ph.user_id = u.user_id
        WHERE m.media_type = 'movie'
            AND strftime('%Y', ph.watched_at, 'unixepoch', 'localtime') = ?
        GROUP BY m.rating_key
        ORDER BY unique_viewers DESC
        LIMIT ?
    """

    cursor.execute(query, (str(YEAR), limit))
    return [dict(row) for row in cursor.fetchall()]


def get_top_shows(conn, limit=3):
    """Get top TV shows by unique viewers, including viewer names."""
    cursor = conn.cursor()

    query = """
        SELECT
            show.rating_key,
            show.title,
            show.year,
            show.thumb,
            COUNT(DISTINCT ph.user_id) as unique_viewers,
            GROUP_CONCAT(DISTINCT u.friendly_name) as viewer_names
        FROM media_items show
        JOIN media_items ep ON ep.grandparent_rating_key = show.rating_key
            AND ep.media_type = 'episode'
        JOIN play_history ph ON ep.rating_key = ph.rating_key
        JOIN users u ON ph.user_id = u.user_id
        WHERE show.media_type = 'show'
            AND strftime('%Y', ph.watched_at, 'unixepoch', 'localtime') = ?
        GROUP BY show.rating_key
        ORDER BY unique_viewers DESC
        LIMIT ?
    """

    cursor.execute(query, (str(YEAR), limit))
    return [dict(row) for row in cursor.fetchall()]


def get_top_artists(conn, limit=3):
    """Get top artists by unique listeners, including listener names."""
    cursor = conn.cursor()

    # Join tracks to artists via grandparent_rating_key
    query = """
        SELECT
            artist.rating_key,
            artist.title,
            artist.thumb,
            COUNT(DISTINCT ph.user_id) as unique_listeners,
            GROUP_CONCAT(DISTINCT u.friendly_name) as listener_names
        FROM media_items track
        JOIN media_items artist ON track.grandparent_rating_key = artist.rating_key
            AND artist.media_type = 'artist'
        JOIN play_history ph ON track.rating_key = ph.rating_key
        JOIN users u ON ph.user_id = u.user_id
        WHERE track.media_type = 'track'
            AND strftime('%Y', ph.watched_at, 'unixepoch', 'localtime') = ?
        GROUP BY artist.rating_key
        ORDER BY unique_listeners DESC
        LIMIT ?
    """

    cursor.execute(query, (str(YEAR), limit))
    return [dict(row) for row in cursor.fetchall()]


def get_top_users(conn, limit=4):
    """Get top users by total usage time (minutes), including join date."""
    cursor = conn.cursor()

    query = """
        SELECT
            u.user_id,
            u.friendly_name,
            u.thumb,
            SUM(ph.duration) / 60 as total_minutes,
            MIN(ph.watched_at) as first_play_timestamp
        FROM play_history ph
        JOIN users u ON ph.user_id = u.user_id
        WHERE strftime('%Y', ph.watched_at, 'unixepoch', 'localtime') = ?
        GROUP BY ph.user_id
        ORDER BY total_minutes DESC
        LIMIT ?
    """

    cursor.execute(query, (str(YEAR), limit))
    return [dict(row) for row in cursor.fetchall()]


def get_all_users_join_dates(conn):
    """Get join dates (first play) for all users, including thumbs."""
    cursor = conn.cursor()

    query = """
        SELECT
            u.user_id,
            u.friendly_name,
            u.thumb,
            MIN(ph.watched_at) as first_play_timestamp
        FROM users u
        JOIN play_history ph ON u.user_id = ph.user_id
        GROUP BY u.user_id
        ORDER BY first_play_timestamp ASC
    """

    cursor.execute(query)
    return [dict(row) for row in cursor.fetchall()]


def format_minutes(minutes):
    """Format minutes as human-readable duration."""
    if not minutes:
        return "0 minutes"

    hours = minutes // 60
    mins = minutes % 60

    if hours > 0:
        if mins > 0:
            return f"{hours:,}h {mins}m"
        return f"{hours:,} hours"
    return f"{mins} minutes"


def main():
    print("=" * 60)
    print("GENERATING DECODED MANIFEST FOR 2025")
    print("=" * 60)

    # Create output directories
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Initialize Tautulli API for image downloads
    try:
        api = TautulliAPI()
        # Quick connectivity check
        print("Checking Tautulli connectivity...")
        test_response = requests.get(f"{api.base_url}/api/v2",
                                     params={"apikey": api.api_key, "cmd": "arnold"},
                                     timeout=5)
        if test_response.status_code == 200:
            print("  Tautulli connected!")
            can_download_images = True
        else:
            print("  Tautulli returned error, images will not be downloaded.")
            can_download_images = False
    except requests.exceptions.Timeout:
        print("Warning: Tautulli connection timed out.")
        print("Images will not be downloaded.")
        can_download_images = False
        api = None
    except requests.exceptions.ConnectionError:
        print("Warning: Could not connect to Tautulli.")
        print("Images will not be downloaded.")
        can_download_images = False
        api = None
    except Exception as e:
        print(f"Warning: Could not initialize Tautulli API: {e}")
        print("Images will not be downloaded.")
        can_download_images = False
        api = None

    # Build manifest
    manifest = {
        "meta": {
            "year": str(YEAR),
            "theme_color": "#FF6B35",
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        "sections": []
    }

    # 1. Intro Section
    print("\n[1/5] Adding intro section...")
    manifest["sections"].append({
        "type": "intro",
        "id": "cover",
        "title": "DECODED",
        "subtitle": str(YEAR),
        "description": "Scroll right to explore the year in data."
    })

    # 2. Library Growth Chart
    print("[2/5] Generating library growth data...")
    growth_data = get_library_growth_data(conn)
    manifest["sections"].append({
        "type": "chart",
        "id": "library-growth",
        "title": "Library Expansion",
        "chart_type": "area",
        "config": {
            "xaxis_key": "date",
            "series": [
                {"key": "movies", "label": "Movies", "color": "#e74c3c"},
                {"key": "seasons", "label": "TV Seasons", "color": "#3498db"},
                {"key": "albums", "label": "Albums", "color": "#2ecc71"}
            ]
        },
        "data": growth_data
    })

    # 3. Weekly Pattern Heatmap
    print("[3/5] Generating weekly pattern heatmap...")
    pattern_data = get_weekly_pattern_data(conn)
    manifest["sections"].append({
        "type": "chart",
        "id": "weekly-pattern",
        "title": "The Pulse of the System",
        "chart_type": "heatmap",
        "config": {
            "color": "#FF6B35",
            "unit": "minutes"
        },
        "data": pattern_data
    })

    # 4. Awards Section
    print("[4/5] Generating awards section...")
    awards_items = []

    # Top Movies
    print("  - Fetching top movies...")
    top_movies = get_top_movies(conn, limit=3)
    for i, movie in enumerate(top_movies, 1):
        filename = f"{to_kebab_case(movie['title'])}.jpg"

        if can_download_images:
            output_path = ASSETS_DIR / filename
            if download_poster(movie['thumb'], output_path, api):
                print(f"    Downloaded: {filename}")

        # Format description with count and names
        viewer_names = movie.get('viewer_names', '')
        description = f"Viewed by {movie['unique_viewers']} users: {viewer_names}"

        awards_items.append({
            "category": f"#{i} Most Watched Movie",
            "title": movie['title'],
            "description": description,
            "image_asset_name": filename
        })

    # Top Shows
    print("  - Fetching top TV shows...")
    top_shows = get_top_shows(conn, limit=3)
    for i, show in enumerate(top_shows, 1):
        filename = f"{to_kebab_case(show['title'])}.jpg"

        if can_download_images:
            output_path = ASSETS_DIR / filename
            if download_poster(show['thumb'], output_path, api):
                print(f"    Downloaded: {filename}")

        # Format description with count and names
        viewer_names = show.get('viewer_names', '')
        description = f"Viewed by {show['unique_viewers']} users: {viewer_names}"

        awards_items.append({
            "category": f"#{i} Most Watched TV Show",
            "title": show['title'],
            "description": description,
            "image_asset_name": filename
        })

    # Top Artists
    print("  - Fetching top artists...")
    top_artists = get_top_artists(conn, limit=3)
    for i, artist in enumerate(top_artists, 1):
        filename = f"{to_kebab_case(artist['title'])}.jpg"

        if can_download_images:
            output_path = ASSETS_DIR / filename
            if download_poster(artist['thumb'], output_path, api):
                print(f"    Downloaded: {filename}")

        # Format description with count and names
        listener_names = artist.get('listener_names', '')
        description = f"Played by {artist['unique_listeners']} users: {listener_names}"

        awards_items.append({
            "category": f"#{i} Most Played Artist",
            "title": artist['title'],
            "description": description,
            "image_asset_name": filename
        })

    # Top Users
    print("  - Fetching top users...")
    top_users = get_top_users(conn, limit=4)
    for i, user in enumerate(top_users, 1):
        friendly_name = user['friendly_name'] or f"User {user['user_id']}"
        filename = f"user-{to_kebab_case(friendly_name)}.jpg"

        if can_download_images and user['thumb']:
            output_path = ASSETS_DIR / filename
            if download_user_avatar(user['thumb'], output_path, api):
                print(f"    Downloaded: {filename}")

        # Format join date
        join_date = ""
        if user.get('first_play_timestamp'):
            from datetime import datetime as dt
            join_dt = dt.fromtimestamp(user['first_play_timestamp'])
            join_date = join_dt.strftime('%b %d, %Y')

        awards_items.append({
            "category": f"#{i} Top User",
            "title": friendly_name,
            "description": format_minutes(user['total_minutes']),
            "join_date": join_date,
            "image_asset_name": filename
        })

    manifest["sections"].append({
        "type": "awards",
        "id": "top-picks",
        "title": "Year in Review",
        "items": awards_items
    })

    # 5. All Users with Join Dates and Avatars
    print("[5/6] Fetching all user join dates and avatars...")
    all_users = get_all_users_join_dates(conn)
    users_data = []
    for user in all_users:
        friendly_name = user['friendly_name'] or f"User {user['user_id']}"
        filename = f"user-{to_kebab_case(friendly_name)}.jpg"

        # Download avatar if available
        if can_download_images and user.get('thumb'):
            output_path = ASSETS_DIR / filename
            if not output_path.exists():  # Skip if already downloaded
                if download_user_avatar(user['thumb'], output_path, api):
                    print(f"    Downloaded: {filename}")

        # Format join date
        join_date = ""
        if user.get('first_play_timestamp'):
            from datetime import datetime as dt
            join_dt = dt.fromtimestamp(user['first_play_timestamp'])
            join_date = join_dt.strftime('%b %d, %Y')

        users_data.append({
            "name": friendly_name,
            "join_date": join_date,
            "image_asset_name": filename
        })

    manifest["sections"].append({
        "type": "users",
        "id": "user-directory",
        "title": "User Directory",
        "data": users_data
    })

    # 6. Write manifest
    print("\n[6/6] Writing manifest...")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    conn.close()

    # Summary
    print("\n" + "=" * 60)
    print("MANIFEST GENERATION COMPLETE")
    print("=" * 60)
    print(f"\nOutput files:")
    print(f"  - Manifest: {OUTPUT_JSON}")
    print(f"  - Assets:   {ASSETS_DIR}/")

    # List generated assets
    assets = list(ASSETS_DIR.glob("*.jpg"))
    if assets:
        print(f"\nDownloaded {len(assets)} images:")
        for asset in sorted(assets):
            print(f"  - {asset.name}")

    print("\nDone!")


if __name__ == '__main__':
    main()
