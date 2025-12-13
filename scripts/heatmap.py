import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime, timedelta
import numpy as np
import calendar

# Configuration
DB_PATH = 'data/plex_stats.db'
USER_ID = '451963595'  # jac7k
YEAR = 2025
OUTPUT_HTML = 'outputs/viz-testing.html'

# Pastel blue gradient colors (light to dark)
COLORS = ['#1a1d29', '#0d3a5c', '#1e5a8e', '#2e7ab8', '#5ea3d0']

def get_play_data(user_id, year):
    """Fetch play history from database for specified user and year."""
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            DATE(ph.watched_at, 'unixepoch') as play_date,
            mi.media_type,
            COUNT(*) as play_count
        FROM play_history ph
        JOIN media_items mi ON ph.rating_key = mi.rating_key
        WHERE ph.user_id = ?
            AND datetime(ph.watched_at, 'unixepoch') >= ?
            AND datetime(ph.watched_at, 'unixepoch') < ?
        GROUP BY play_date, mi.media_type
    """

    start_date = f'{year}-01-01'
    end_date = f'{year + 1}-01-01'

    df = pd.read_sql_query(query, conn, params=(user_id, start_date, end_date))
    conn.close()

    return df

def prepare_heatmap_data(df, media_types, year):
    """Prepare data for heatmap visualization."""
    # Filter for specified media types
    df_filtered = df[df['media_type'].isin(media_types)].copy()

    # Group by date and sum play counts
    daily_counts = df_filtered.groupby('play_date')['play_count'].sum().reset_index()
    daily_counts['play_date'] = pd.to_datetime(daily_counts['play_date'])

    # Create a complete date range for the year
    start_date = pd.Timestamp(f'{year}-01-01')
    end_date = pd.Timestamp(f'{year}-12-31')
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')

    # Create a dataframe with all dates
    date_df = pd.DataFrame({'play_date': all_dates})

    # Merge with play counts
    result = date_df.merge(daily_counts, on='play_date', how='left')
    result['play_count'] = result['play_count'].fillna(0)

    return result

def create_github_heatmap(data, title, ax):
    """Create a GitHub-style contribution heatmap with individual squares."""
    # Add week and day of week columns
    data['week'] = data['play_date'].dt.isocalendar().week
    data['day_of_week'] = data['play_date'].dt.dayofweek

    # Adjust week numbers to start from 0
    data['week'] = data['week'] - data['week'].min()

    # Create a matrix for the heatmap (7 rows for days, columns for weeks)
    weeks = data['week'].max() + 1
    heatmap_matrix = np.zeros((7, weeks))

    for _, row in data.iterrows():
        week = int(row['week'])
        day = int(row['day_of_week'])
        heatmap_matrix[day, week] = row['play_count']

    # Get max count for this specific heatmap for dynamic scaling
    max_count = data['play_count'].max()

    # Determine color based on percentile of max count for this heatmap
    def get_color(count):
        if count == 0:
            return COLORS[0]
        elif count <= max_count * 0.25:
            return COLORS[1]
        elif count <= max_count * 0.50:
            return COLORS[2]
        elif count <= max_count * 0.75:
            return COLORS[3]
        else:
            return COLORS[4]

    # Draw individual squares
    square_size = 0.75  # Size of each square (less than 1 for gaps)
    for i in range(7):
        for j in range(weeks):
            count = heatmap_matrix[i, j]
            color = get_color(count)
            rect = mpatches.Rectangle((j - square_size/2, i - square_size/2),
                                     square_size, square_size,
                                     facecolor=color, edgecolor=color)
            ax.add_patch(rect)

    # Set up the axes
    ax.set_xlim(-0.5, weeks - 0.5)
    ax.set_ylim(-0.5, 6.5)
    ax.set_yticks([0, 1, 2, 3, 4, 5, 6])
    ax.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
    ax.invert_yaxis()

    # Set aspect ratio to equal so squares are actually square
    ax.set_aspect('equal', adjustable='box')

    # Month labels
    month_positions = []
    month_labels = []
    current_month = None

    for idx, row in data.iterrows():
        month = row['play_date'].month
        week = row['week']
        if month != current_month:
            month_positions.append(week)
            month_labels.append(calendar.month_abbr[month])
            current_month = month

    ax.set_xticks(month_positions)
    ax.set_xticklabels(month_labels)
    ax.tick_params(axis='x', which='both', length=0)
    ax.tick_params(axis='y', which='both', length=0)

    # Style
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20, color='#e6e6e6')
    ax.set_facecolor('#0d1117')

    # Remove spines
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Set tick colors
    ax.tick_params(colors='#8b949e', labelsize=9)

    # Add total count - positioned on the left
    total_plays = int(data['play_count'].sum())
    ax.text(-0.5, -1.5, f'{total_plays} plays in {YEAR}',
            fontsize=11, color='#8b949e', ha='left')

    return ax, max_count

def generate_heatmap():
    """Generate and save heatmap visualization."""
    print(f"Fetching play data for user {USER_ID} in {YEAR}...")
    df = get_play_data(USER_ID, YEAR)

    if df.empty:
        print("No play data found!")
        return

    print(f"Processing {len(df)} records...")

    # Prepare data for music and video
    music_data = prepare_heatmap_data(df, ['track'], YEAR)
    video_data = prepare_heatmap_data(df, ['movie', 'episode'], YEAR)

    # Create figure with dark background
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 8), facecolor='#0d1117')
    plt.subplots_adjust(hspace=0.5)

    # Create heatmaps and get their max counts
    ax1, music_max = create_github_heatmap(music_data, 'Music Plays', ax1)
    ax2, video_max = create_github_heatmap(video_data, 'Movie + TV Plays', ax2)

    # Add separate legends for each heatmap with their specific thresholds
    # Music legend
    music_legend_elements = [
        mpatches.Patch(facecolor=COLORS[0], label='0'),
        mpatches.Patch(facecolor=COLORS[1], label=f'1-{int(music_max * 0.25)}'),
        mpatches.Patch(facecolor=COLORS[2], label=f'{int(music_max * 0.25) + 1}-{int(music_max * 0.50)}'),
        mpatches.Patch(facecolor=COLORS[3], label=f'{int(music_max * 0.50) + 1}-{int(music_max * 0.75)}'),
        mpatches.Patch(facecolor=COLORS[4], label=f'{int(music_max * 0.75) + 1}+')
    ]

    # Add legend below first heatmap
    ax1.legend(handles=music_legend_elements, loc='upper right',
               frameon=False, ncol=5, fontsize=9, labelcolor='#8b949e',
               bbox_to_anchor=(1.0, -0.08))

    # Video legend
    video_legend_elements = [
        mpatches.Patch(facecolor=COLORS[0], label='0'),
        mpatches.Patch(facecolor=COLORS[1], label=f'1-{int(video_max * 0.25)}'),
        mpatches.Patch(facecolor=COLORS[2], label=f'{int(video_max * 0.25) + 1}-{int(video_max * 0.50)}'),
        mpatches.Patch(facecolor=COLORS[3], label=f'{int(video_max * 0.50) + 1}-{int(video_max * 0.75)}'),
        mpatches.Patch(facecolor=COLORS[4], label=f'{int(video_max * 0.75) + 1}+')
    ]

    # Add legend below second heatmap
    ax2.legend(handles=video_legend_elements, loc='upper right',
               frameon=False, ncol=5, fontsize=9, labelcolor='#8b949e',
               bbox_to_anchor=(1.0, -0.08))

    # Save as high-res image
    output_img = 'outputs/heatmap_viz.png'
    plt.savefig(output_img, dpi=150, bbox_inches='tight', facecolor='#0d1117')
    print(f"Heatmap saved as {output_img}")

    # Generate HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Plex Activity Heatmap - {YEAR}</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background-color: #0d1117;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
            color: #e6e6e6;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            color: #e6e6e6;
            margin-bottom: 40px;
            font-size: 32px;
        }}
        .heatmap-container {{
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 20px;
            box-shadow: 0 0 15px rgba(0,0,0,0.3);
        }}
        img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #8b949e;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Plex Activity Heatmap - {YEAR}</h1>
        <div class="heatmap-container">
            <img src="{output_img}" alt="Activity Heatmap">
        </div>
        <div class="footer">
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""

    with open(OUTPUT_HTML, 'w') as f:
        f.write(html_content)

    print(f"HTML visualization saved as {OUTPUT_HTML}")
    print("\nDone! Open outputs/viz-testing.html in your browser to view the heatmap.")

if __name__ == '__main__':
    generate_heatmap()
