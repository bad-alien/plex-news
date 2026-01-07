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

# Maximum session duration to include (4 hours in seconds)
# Sessions beyond this are likely left paused/running and skew the data
MAX_SESSION_DURATION = 4 * 3600  # 14400 seconds

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
    """Get server-wide usage pattern by day of week and hour (in minutes).

    Note: User timezone adjustments are applied to normalize all viewing times
    to Pacific timezone (America/Los_Angeles) for consistent aggregation.

    Sessions longer than MAX_SESSION_DURATION are excluded as outliers.
    """
    cursor = conn.cursor()

    # User timezone offsets (hours to ADD to normalize to Pacific)
    # Eastern users: +3 hours (ET is 3 hours ahead of PT)
    USER_TZ_OFFSETS = {
        '501320151': 3,  # equa50 - Eastern timezone
    }

    # Build timezone-adjusted timestamp expression
    # For users with offsets, we add hours to their localtime result
    # This normalizes their viewing patterns to Pacific time
    tz_cases = " ".join([
        f"WHEN user_id = '{uid}' THEN {offset * 3600}"
        for uid, offset in USER_TZ_OFFSETS.items()
    ])

    # Adjust watched_at by adding offset seconds before converting to localtime
    # This shifts Eastern viewers' times forward so 8pm ET appears as 8pm PT
    adjusted_timestamp = f"""
        CASE {tz_cases} ELSE 0 END + watched_at
    """ if tz_cases else "watched_at"

    query = f"""
        SELECT
            CAST(strftime('%w', {adjusted_timestamp}, 'unixepoch', 'localtime') AS INTEGER) as day_num,
            CAST(strftime('%H', {adjusted_timestamp}, 'unixepoch', 'localtime') AS INTEGER) as hour,
            SUM(duration) / 60 as total_minutes
        FROM play_history
        WHERE strftime('%Y', watched_at, 'unixepoch', 'localtime') = ?
            AND duration <= {MAX_SESSION_DURATION}
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


def get_top_shows(conn, api, limit=3):
    """Get top TV shows by unique viewers, including viewer names.

    Since we don't have show entities in media_items (only synced from play history),
    we aggregate by grandparent_rating_key from episodes and fetch show names from
    play history API (which has grandparent_title).
    """
    cursor = conn.cursor()

    # Aggregate by grandparent_rating_key from episodes
    query = """
        SELECT
            ep.grandparent_rating_key as rating_key,
            COUNT(DISTINCT ph.user_id) as unique_viewers,
            GROUP_CONCAT(DISTINCT u.friendly_name) as viewer_names
        FROM media_items ep
        JOIN play_history ph ON ep.rating_key = ph.rating_key
        JOIN users u ON ph.user_id = u.user_id
        WHERE ep.media_type = 'episode'
            AND ep.grandparent_rating_key IS NOT NULL
            AND strftime('%Y', ph.watched_at, 'unixepoch', 'localtime') = ?
        GROUP BY ep.grandparent_rating_key
        ORDER BY unique_viewers DESC
        LIMIT ?
    """

    cursor.execute(query, (str(YEAR), limit))
    candidates = [dict(row) for row in cursor.fetchall()]

    results = []
    for candidate in candidates:
        rating_key = candidate['rating_key']

        # Fetch show name from play history API (grandparent_title)
        try:
            if api:
                history_result = api._make_request(
                    'get_history',
                    grandparent_rating_key=rating_key,
                    media_type='episode',
                    length=1
                )
                if history_result and 'response' in history_result:
                    data = history_result['response'].get('data', {})
                    items = data.get('data', [])
                    if items:
                        show_title = items[0].get('grandparent_title', f'Show {rating_key}')
                        show_thumb = items[0].get('grandparent_thumb', '')
                        show_year = items[0].get('year', '')

                        candidate['title'] = show_title
                        candidate['thumb'] = show_thumb
                        candidate['year'] = show_year
                        results.append(candidate)
                        continue

                # Fallback if no history found
                candidate['title'] = f'Show {rating_key}'
                candidate['thumb'] = ''
                candidate['year'] = ''
                results.append(candidate)
            else:
                candidate['title'] = f'Show {rating_key}'
                candidate['thumb'] = ''
                candidate['year'] = ''
                results.append(candidate)
        except Exception as e:
            print(f"    Error fetching show info for {rating_key}: {e}")
            continue

    return results


def get_top_artists(conn, api, limit=3):
    """Get top artists by total plays, including play count and listener names.

    Note: Excludes 'Comps' as it's a compilation placeholder, not a real artist.

    Since we don't have artist entities in media_items (only synced from play history),
    we aggregate by grandparent_rating_key from tracks and fetch artist names from
    play history API (which has grandparent_title).
    """
    cursor = conn.cursor()

    # Aggregate by grandparent_rating_key from tracks
    query = """
        SELECT
            track.grandparent_rating_key as rating_key,
            COUNT(*) as total_plays,
            COUNT(DISTINCT ph.user_id) as unique_listeners,
            GROUP_CONCAT(DISTINCT u.friendly_name) as listener_names
        FROM media_items track
        JOIN play_history ph ON track.rating_key = ph.rating_key
        JOIN users u ON ph.user_id = u.user_id
        WHERE track.media_type = 'track'
            AND track.grandparent_rating_key IS NOT NULL
            AND strftime('%Y', ph.watched_at, 'unixepoch', 'localtime') = ?
        GROUP BY track.grandparent_rating_key
        ORDER BY total_plays DESC
        LIMIT ?
    """

    # Fetch more than needed to allow filtering out "Comps"
    cursor.execute(query, (str(YEAR), limit + 10))
    candidates = [dict(row) for row in cursor.fetchall()]

    results = []
    for candidate in candidates:
        if len(results) >= limit:
            break

        rating_key = candidate['rating_key']

        # First, get artist info from database (reliable source for thumb)
        cursor.execute("""
            SELECT title, thumb FROM media_items
            WHERE rating_key = ? AND media_type = 'artist'
        """, (rating_key,))
        db_artist = cursor.fetchone()
        db_title = dict(db_artist)['title'] if db_artist else None
        db_thumb = dict(db_artist)['thumb'] if db_artist else None

        # Fetch artist name from play history API (grandparent_title) as backup
        try:
            if api:
                # Get a single play record for this artist to retrieve the name
                history_result = api._make_request(
                    'get_history',
                    grandparent_rating_key=rating_key,
                    media_type='track',
                    length=1
                )
                if history_result and 'response' in history_result:
                    data = history_result['response'].get('data', {})
                    items = data.get('data', [])
                    if items:
                        artist_title = items[0].get('grandparent_title', db_title or f'Artist {rating_key}')
                        artist_thumb = items[0].get('grandparent_thumb', '')

                        # Skip "Comps"
                        if artist_title.lower() == 'comps':
                            continue

                        candidate['title'] = artist_title
                        # Use API thumb if available, otherwise fall back to database thumb
                        candidate['thumb'] = artist_thumb if artist_thumb else db_thumb
                        results.append(candidate)
                        continue

                # Fallback if no history found - use database values
                candidate['title'] = db_title or f'Artist {rating_key}'
                candidate['thumb'] = db_thumb or ''
                results.append(candidate)
            else:
                # No API available - use database values
                candidate['title'] = db_title or f'Artist {rating_key}'
                candidate['thumb'] = db_thumb or ''
                results.append(candidate)
        except Exception as e:
            print(f"    Error fetching artist info for {rating_key}: {e}")
            continue

    return results


def get_top_albums(conn, api, limit=3):
    """Get top albums by total plays, including play count and listener names.

    Note: Excludes compilation albums under 'Comps' artist.

    Aggregates by album rating_key (parent of tracks) from play history.
    Uses parent_rating_key on tracks to link to albums.
    """
    cursor = conn.cursor()

    # Get top albums from track plays using parent_rating_key for track->album linking
    query = """
        SELECT
            album.rating_key,
            album.title,
            album.thumb,
            album.grandparent_rating_key as artist_rating_key,
            COUNT(*) as total_plays,
            COUNT(DISTINCT ph.user_id) as unique_listeners,
            GROUP_CONCAT(DISTINCT u.friendly_name) as listener_names
        FROM media_items track
        JOIN media_items album ON track.parent_rating_key = album.rating_key
        JOIN play_history ph ON track.rating_key = ph.rating_key
        JOIN users u ON ph.user_id = u.user_id
        WHERE track.media_type = 'track'
            AND album.media_type = 'album'
            AND strftime('%Y', ph.watched_at, 'unixepoch', 'localtime') = ?
        GROUP BY album.rating_key
        ORDER BY total_plays DESC
        LIMIT ?
    """

    cursor.execute(query, (str(YEAR), limit + 10))
    candidates = [dict(row) for row in cursor.fetchall()]

    results = []
    for candidate in candidates:
        if len(results) >= limit:
            break

        # Skip if title contains "Comps" (compilations)
        if candidate.get('title') and 'comps' in candidate['title'].lower():
            continue

        results.append(candidate)

    return results


def get_top_users(conn, limit=4):
    """Get top users by total usage time (minutes), including join date.

    Sessions longer than MAX_SESSION_DURATION are excluded as outliers.
    """
    cursor = conn.cursor()

    query = f"""
        SELECT
            u.user_id,
            u.friendly_name,
            u.thumb,
            SUM(ph.duration) / 60 as total_minutes,
            MIN(ph.watched_at) as first_play_timestamp
        FROM play_history ph
        JOIN users u ON ph.user_id = u.user_id
        WHERE strftime('%Y', ph.watched_at, 'unixepoch', 'localtime') = ?
            AND ph.duration <= {MAX_SESSION_DURATION}
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


def get_users_joined_in_year(conn, year):
    """Get users who joined (first play) in a specific year."""
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
        HAVING strftime('%Y', MIN(ph.watched_at), 'unixepoch', 'localtime') = ?
        ORDER BY first_play_timestamp ASC
    """

    cursor.execute(query, (str(year),))
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


def format_minutes_as_days_hours(minutes):
    """Format minutes as 'XXd XXh', rounding up partial hours."""
    if not minutes or minutes <= 0:
        return "0d 0h"

    # Round up to nearest hour
    total_hours = (minutes + 59) // 60

    days = total_hours // 24
    hours = total_hours % 24

    return f"{days}d {hours}h"


def get_user_play_breakdown(conn, user_id):
    """Get play time breakdown by media type for a user (in minutes).

    Sessions longer than MAX_SESSION_DURATION are excluded as outliers.
    """
    cursor = conn.cursor()

    # Total play time
    cursor.execute(f"""
        SELECT COALESCE(SUM(duration), 0) / 60 as total_minutes
        FROM play_history
        WHERE user_id = ?
            AND strftime('%Y', watched_at, 'unixepoch', 'localtime') = ?
            AND duration <= {MAX_SESSION_DURATION}
    """, (user_id, str(YEAR)))
    total = cursor.fetchone()['total_minutes']

    # Movie play time
    cursor.execute(f"""
        SELECT COALESCE(SUM(ph.duration), 0) / 60 as minutes
        FROM play_history ph
        JOIN media_items mi ON ph.rating_key = mi.rating_key
        WHERE ph.user_id = ?
            AND mi.media_type = 'movie'
            AND strftime('%Y', ph.watched_at, 'unixepoch', 'localtime') = ?
            AND ph.duration <= {MAX_SESSION_DURATION}
    """, (user_id, str(YEAR)))
    movie = cursor.fetchone()['minutes']

    # TV play time (episodes)
    cursor.execute(f"""
        SELECT COALESCE(SUM(ph.duration), 0) / 60 as minutes
        FROM play_history ph
        JOIN media_items mi ON ph.rating_key = mi.rating_key
        WHERE ph.user_id = ?
            AND mi.media_type = 'episode'
            AND strftime('%Y', ph.watched_at, 'unixepoch', 'localtime') = ?
            AND ph.duration <= {MAX_SESSION_DURATION}
    """, (user_id, str(YEAR)))
    tv = cursor.fetchone()['minutes']

    # Music play time (tracks)
    cursor.execute(f"""
        SELECT COALESCE(SUM(ph.duration), 0) / 60 as minutes
        FROM play_history ph
        JOIN media_items mi ON ph.rating_key = mi.rating_key
        WHERE ph.user_id = ?
            AND mi.media_type = 'track'
            AND strftime('%Y', ph.watched_at, 'unixepoch', 'localtime') = ?
            AND ph.duration <= {MAX_SESSION_DURATION}
    """, (user_id, str(YEAR)))
    music = cursor.fetchone()['minutes']

    return {
        'total': total or 0,
        'movie': movie or 0,
        'tv': tv or 0,
        'music': music or 0
    }


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

    # Get users who joined in this year for user_joins array
    print("  - Getting users who joined in 2025...")
    users_joined = get_users_joined_in_year(conn, YEAR)
    user_joins = []
    for user in users_joined:
        friendly_name = user['friendly_name'] or f"User {user['user_id']}"
        filename = f"user-{to_kebab_case(friendly_name)}.jpg"

        # Download avatar if available
        if can_download_images and user.get('thumb'):
            output_path = ASSETS_DIR / filename
            if not output_path.exists():
                if download_user_avatar(user['thumb'], output_path, api):
                    print(f"    Downloaded: {filename}")

        # Format join date
        join_date = ""
        if user.get('first_play_timestamp'):
            from datetime import datetime as dt
            join_dt = dt.fromtimestamp(user['first_play_timestamp'])
            join_date = join_dt.strftime('%b %-d')

        user_joins.append({
            "username": friendly_name,
            "date": join_date,
            "avatar": filename
        })

    manifest["sections"].append({
        "type": "chart",
        "id": "library-growth",
        "title": "New Stuff! New People!",
        "chart_type": "area",
        "config": {
            "xaxis_key": "date",
            "series": [
                {"key": "movies", "label": "Movies", "color": "#e74c3c"},
                {"key": "seasons", "label": "TV Seasons", "color": "#3498db"},
                {"key": "albums", "label": "Albums", "color": "#2ecc71"}
            ]
        },
        "data": growth_data,
        "user_joins": user_joins
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
    top_shows = get_top_shows(conn, api, limit=3)
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
    top_artists = get_top_artists(conn, api, limit=3)
    for i, artist in enumerate(top_artists, 1):
        filename = f"{to_kebab_case(artist['title'])}.jpg"

        if can_download_images:
            output_path = ASSETS_DIR / filename
            if download_poster(artist['thumb'], output_path, api):
                print(f"    Downloaded: {filename}")

        # Format description with total plays and user names
        total_plays = artist.get('total_plays', 0)
        listener_names = artist.get('listener_names', '')
        description = f"{total_plays} plays by {artist['unique_listeners']} users: {listener_names}"

        awards_items.append({
            "category": f"#{i} Most Played Artist",
            "title": artist['title'],
            "description": description,
            "total_plays": total_plays,
            "image_asset_name": filename
        })

    # Top Albums
    print("  - Fetching top albums...")
    top_albums = get_top_albums(conn, api, limit=3)
    for i, album in enumerate(top_albums, 1):
        filename = f"album-{to_kebab_case(album['title'])}.jpg"

        if can_download_images and album.get('thumb'):
            output_path = ASSETS_DIR / filename
            if download_poster(album['thumb'], output_path, api):
                print(f"    Downloaded: {filename}")

        # Format description with total plays and user names
        total_plays = album.get('total_plays', 0)
        listener_names = album.get('listener_names', '')
        description = f"{total_plays} plays by {album['unique_listeners']} users: {listener_names}"

        awards_items.append({
            "category": f"#{i} Most Played Album",
            "title": album['title'],
            "description": description,
            "total_plays": total_plays,
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

    # 5. All Users with Join Dates, Avatars, and Play Time Breakdown
    print("[5/6] Fetching all user join dates, avatars, and play breakdown...")
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

        # Get play time breakdown
        play_breakdown = get_user_play_breakdown(conn, user['user_id'])

        users_data.append({
            "name": friendly_name,
            "join_date": join_date,
            "image_asset_name": filename,
            "play_time": {
                "total": format_minutes_as_days_hours(play_breakdown['total']),
                "movie": format_minutes_as_days_hours(play_breakdown['movie']),
                "tv": format_minutes_as_days_hours(play_breakdown['tv']),
                "music": format_minutes_as_days_hours(play_breakdown['music'])
            }
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
