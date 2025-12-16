#!/usr/bin/env python3
"""
Generate a racing bar chart GIF showing top artists over time for a Plex user.
"""
import sys
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from PIL import Image
import requests
from io import BytesIO

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tautulli_api import TautulliAPI

# Configuration
DB_PATH = 'data/plex_stats.db'
USER_ID = '451963595'  # jac7k
USERNAME = 'jac7k'
YEAR = 2025
TOP_N = 5
OUTPUT_GIF = 'outputs/racing_bar_chart_jac7k.gif'
TARGET_DURATION_SEC = 60

# Styling (matching heatmap theme)
BG_COLOR = '#0d1117'
TEXT_COLOR = '#e6e6e6'
SECONDARY_TEXT_COLOR = '#8b949e'
BAR_COLORS = ['#0d3a5c', '#1e5a8e', '#2e7ab8', '#5ea3d0']  # Blue gradient

def get_artist_plays_by_date(user_id, year):
    """
    Get cumulative artist play counts by date.
    Returns: dict[date][artist] = cumulative_play_count
    """
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            DATE(ph.watched_at, 'unixepoch') as play_date,
            ph.rating_key,
            COUNT(*) as plays_that_day
        FROM play_history ph
        JOIN media_items mi ON ph.rating_key = mi.rating_key
        WHERE ph.user_id = ?
            AND mi.media_type = 'track'
            AND datetime(ph.watched_at, 'unixepoch') >= ?
            AND datetime(ph.watched_at, 'unixepoch') < ?
        GROUP BY play_date, ph.rating_key
        ORDER BY play_date ASC
    """

    start_date = f'{year}-01-01'
    end_date = f'{year + 1}-01-01'

    cursor = conn.cursor()
    cursor.execute(query, (user_id, start_date, end_date))

    # Get rating_key to artist mapping
    rating_key_to_artist = {}

    # Build daily plays first
    daily_plays = defaultdict(lambda: defaultdict(int))

    for play_date, rating_key, plays in cursor.fetchall():
        # We'll map rating_keys to artists later
        daily_plays[play_date][rating_key] = plays

    conn.close()

    return daily_plays

def get_artist_metadata(api, rating_keys):
    """
    Fetch artist metadata for a set of rating keys.
    Returns: dict[rating_key] = {'artist': str, 'thumb': str}
    """
    print(f"Fetching metadata for {len(rating_keys)} unique tracks...")

    metadata = {}
    total = len(rating_keys)

    for i, rating_key in enumerate(rating_keys, 1):
        if i % 50 == 0 or i == total:
            print(f"  Progress: {i}/{total}")

        try:
            response = api._make_request('get_metadata', rating_key=str(rating_key))
            if response:
                data = response.get('response', {}).get('data', {})
                artist = data.get('grandparent_title', 'Unknown Artist')
                thumb = data.get('grandparent_thumb', '')

                metadata[rating_key] = {
                    'artist': artist,
                    'thumb': thumb
                }
        except Exception as e:
            print(f"  Warning: Could not fetch metadata for {rating_key}: {e}")
            metadata[rating_key] = {
                'artist': 'Unknown Artist',
                'thumb': ''
            }

    return metadata

def download_thumbnail(api, thumb_path, cache_dir='outputs/thumb_cache'):
    """
    Download and cache artist thumbnail.
    Returns: PIL.Image or None
    """
    if not thumb_path:
        return None

    # Create cache directory
    Path(cache_dir).mkdir(exist_ok=True)

    # Create cache filename from thumb path
    cache_file = Path(cache_dir) / f"{thumb_path.replace('/', '_')}.jpg"

    # Check cache
    if cache_file.exists():
        try:
            return Image.open(cache_file)
        except:
            pass

    # Download from Tautulli
    try:
        url = f"{api.base_url}/pms_image_proxy"
        params = {
            'img': thumb_path,
            'width': 100,
            'height': 100,
            'fallback': 'poster'
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.save(cache_file)
            return img
    except Exception as e:
        print(f"  Warning: Could not download thumbnail: {e}")

    return None

def interpolate_values(prev_values, next_values, t):
    """
    Interpolate between two states for smooth transitions.
    t is between 0 and 1.
    """
    result = {}
    all_keys = set(prev_values.keys()) | set(next_values.keys())

    for key in all_keys:
        prev_val = prev_values.get(key, 0)
        next_val = next_values.get(key, 0)
        result[key] = prev_val + (next_val - prev_val) * t

    return result

def render_frame(date_str, artist_data, thumbnails, max_value, fig, ax):
    """
    Render a single frame of the racing bar chart.
    artist_data: list of (artist_name, play_count, rank_position) sorted by rank
    """
    ax.clear()

    # Set background
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # Get top N artists
    top_artists = sorted(artist_data.items(), key=lambda x: x[1], reverse=True)[:TOP_N]

    if not top_artists:
        # No data yet
        ax.text(0.5, 0.5, 'No plays yet',
                ha='center', va='center',
                fontsize=20, color=SECONDARY_TEXT_COLOR,
                transform=ax.transAxes)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return

    # Reverse order so highest is at top
    top_artists.reverse()

    # Calculate bar positions
    y_positions = np.arange(len(top_artists))
    play_counts = [count for _, count in top_artists]
    artist_names = [name for name, _ in top_artists]

    # Create bars with gradient colors
    bars = []
    for i, (y_pos, count) in enumerate(zip(y_positions, play_counts)):
        color = BAR_COLORS[i % len(BAR_COLORS)]
        bar = ax.barh(y_pos, count, color=color, height=0.7, alpha=0.9)
        bars.append(bar)

    # Set up axes
    ax.set_ylim(-0.5, len(top_artists) - 0.5)
    ax.set_xlim(0, max_value * 1.15)  # Add 15% padding

    # Add play count labels at end of bars
    for i, (y_pos, count, artist) in enumerate(zip(y_positions, play_counts, artist_names)):
        # Play count
        ax.text(count + max_value * 0.02, y_pos, f'{int(count):,}',
                va='center', ha='left', fontsize=12,
                color=TEXT_COLOR, fontweight='bold')

        # Artist name on bar
        ax.text(max_value * 0.01, y_pos, artist,
                va='center', ha='left', fontsize=11,
                color=TEXT_COLOR, fontweight='600')

    # Remove spines and ticks
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.set_yticks([])
    ax.set_xticks([])

    # Add date indicator in top left
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    date_display = date_obj.strftime('%B %Y')

    ax.text(0.02, 1.08, date_display,
            transform=ax.transAxes,
            fontsize=24, fontweight='bold',
            color=TEXT_COLOR, va='top')

    # Add total plays count
    total_plays = sum(play_counts)
    ax.text(0.98, 1.08, f'Total Plays: {int(total_plays):,}',
            transform=ax.transAxes,
            fontsize=14,
            color=SECONDARY_TEXT_COLOR, va='top', ha='right')

def generate_racing_bar_chart():
    """Generate the racing bar chart GIF."""
    print(f"Generating racing bar chart for {USERNAME} ({USER_ID}) in {YEAR}...")

    api = TautulliAPI()

    # Get play data
    print("\nFetching play data...")
    daily_plays = get_artist_plays_by_date(USER_ID, YEAR)

    if not daily_plays:
        print("No track plays found!")
        return

    # Get all unique rating keys
    all_rating_keys = set()
    for day_data in daily_plays.values():
        all_rating_keys.update(day_data.keys())

    # Get artist metadata
    print("\nFetching artist metadata...")
    metadata = get_artist_metadata(api, all_rating_keys)

    # Convert rating_key plays to artist plays
    daily_artist_plays = defaultdict(lambda: defaultdict(int))
    for date, day_data in daily_plays.items():
        for rating_key, plays in day_data.items():
            artist = metadata.get(rating_key, {}).get('artist', 'Unknown Artist')
            daily_artist_plays[date][artist] += plays

    # Get date range
    dates = sorted(daily_artist_plays.keys())
    if not dates:
        print("No dates found!")
        return

    start_date = datetime.strptime(dates[0], '%Y-%m-%d')
    end_date = datetime.strptime(dates[-1], '%Y-%m-%d')

    print(f"\nDate range: {start_date.date()} to {end_date.date()}")
    print(f"Total days: {(end_date - start_date).days + 1}")

    # Build cumulative data for each day
    cumulative_data = {}
    running_totals = defaultdict(int)

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')

        # Add today's plays to running totals
        if date_str in daily_artist_plays:
            for artist, plays in daily_artist_plays[date_str].items():
                running_totals[artist] += plays

        # Store snapshot
        cumulative_data[date_str] = dict(running_totals)

        current_date += timedelta(days=1)

    # Calculate max value for consistent scaling
    max_value = 0
    for day_data in cumulative_data.values():
        if day_data:
            max_value = max(max_value, max(day_data.values()))

    print(f"Max cumulative plays: {max_value}")

    # Generate frames
    print(f"\nGenerating frames...")
    frames = []

    # Setup figure
    fig, ax = plt.subplots(figsize=(12, 8), facecolor=BG_COLOR)
    plt.subplots_adjust(left=0.05, right=0.95, top=0.88, bottom=0.05)

    dates_to_render = sorted(cumulative_data.keys())
    total_frames = len(dates_to_render)

    for i, date_str in enumerate(dates_to_render):
        if (i + 1) % 30 == 0 or (i + 1) == total_frames:
            print(f"  Frame {i + 1}/{total_frames}")

        artist_data = cumulative_data[date_str]
        render_frame(date_str, artist_data, None, max_value, fig, ax)

        # Convert to image
        fig.canvas.draw()
        # Save to buffer
        buf = BytesIO()
        fig.savefig(buf, format='png', facecolor=BG_COLOR, dpi=100)
        buf.seek(0)
        frame_img = Image.open(buf)
        frames.append(frame_img.copy())
        buf.close()

    plt.close(fig)

    # Calculate frame duration
    total_frames = len(frames)
    duration_ms = int((TARGET_DURATION_SEC * 1000) / total_frames)

    print(f"\nSaving GIF with {total_frames} frames...")
    print(f"Duration per frame: {duration_ms}ms")
    print(f"Total duration: ~{TARGET_DURATION_SEC}s")

    # Save as GIF
    frames[0].save(
        OUTPUT_GIF,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=False
    )

    print(f"\n✓ Racing bar chart saved as {OUTPUT_GIF}")
    print(f"File size: {Path(OUTPUT_GIF).stat().st_size / 1024 / 1024:.1f} MB")

if __name__ == '__main__':
    generate_racing_bar_chart()
