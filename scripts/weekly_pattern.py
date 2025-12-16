#!/usr/bin/env python3
"""
Generate weekly usage pattern density plot for a specific user.

Shows overlapping density plots of hourly activity patterns averaged by day of week.
"""

import sys
from pathlib import Path
from datetime import datetime
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import pytz

# Add project root to path so we can import from src/
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configuration
DB_PATH = 'data/plex_stats.db'
USER_ID = '451963595'  # jac7k
YEAR = 2025
OUTPUT_HTML = 'outputs/weekly_pattern.html'

# Color palette (same as existing density plot)
PALETTE = ["#7e55a3", "#6368b6", "#4079bf", "#0087bf", "#0093b7", "#009daa", "#26a69a"]

def get_user_play_history(user_id, year):
    """Fetch play history timestamps for specified user and year."""
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT ph.watched_at
        FROM play_history ph
        WHERE ph.user_id = ?
            AND datetime(ph.watched_at, 'unixepoch') >= ?
            AND datetime(ph.watched_at, 'unixepoch') < ?
    """

    start_date = f'{year}-01-01'
    end_date = f'{year + 1}-01-01'

    df = pd.read_sql_query(query, conn, params=(user_id, start_date, end_date))
    conn.close()

    return df

def create_weekly_pattern_density(df, user_name='User'):
    """
    Creates an overlapping density plot showing usage patterns by day of week.

    Args:
        df: DataFrame with 'watched_at' column (unix timestamps)
        user_name: Name to display in title

    Returns:
        str: Path to saved plot image
    """
    if df.empty:
        # Create empty plot if no data
        plt.figure(figsize=(12, 8))
        plt.text(0.5, 0.5, 'No usage data available', ha='center', va='center',
                transform=plt.gca().transAxes)
        output_img = 'outputs/weekly_pattern.png'
        plt.savefig(output_img, bbox_inches='tight', dpi=300)
        plt.close()
        return output_img

    # Convert timestamps from UTC to America/Los_Angeles
    la_tz = pytz.timezone('America/Los_Angeles')
    timestamps = pd.to_datetime(df['watched_at'], unit='s', utc=True)
    df['datetime'] = timestamps.dt.tz_convert(la_tz)

    df['hour'] = df['datetime'].dt.hour
    df['day'] = df['datetime'].dt.day_name()

    # Set up the day order (Sunday to Saturday)
    day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    # Filter to only include days that have data
    df = df[df['day'].isin(day_order)]

    if df.empty:
        # Create empty plot if no data after filtering
        plt.figure(figsize=(12, 8))
        plt.text(0.5, 0.5, 'No usage data available', ha='center', va='center',
                transform=plt.gca().transAxes)
        output_img = 'outputs/weekly_pattern.png'
        plt.savefig(output_img, bbox_inches='tight', dpi=300)
        plt.close()
        return output_img

    # Set the theme for clean background
    sns.set_theme(style="white")

    # Shift hours for 6am to 6am view
    # 6am becomes 0, 5am becomes 23
    df['shifted_hour'] = (df['hour'] - 6 + 24) % 24

    # Initialize the FacetGrid object
    g = sns.FacetGrid(df, row="day", hue="day", aspect=15, height=.75,
                      palette=PALETTE, row_order=day_order)

    # Draw the densities
    g.map(sns.kdeplot, "shifted_hour",
          bw_adjust=.5, clip_on=True,
          fill=True, alpha=1, linewidth=1.5)
    g.map(sns.kdeplot, "shifted_hour", clip_on=True, color="w", lw=2, bw_adjust=.5)

    # Add a reference line at y=0
    g.refline(y=0, linewidth=2, linestyle="-", color=None, clip_on=False)

    # Label function for day names
    def label(x, color, label):
        ax = plt.gca()
        ax.text(-0.02, .5, label, fontweight="bold", color=color,
                ha="right", va="center", transform=ax.transAxes, fontsize=12)

    g.map(label, "shifted_hour")

    # Set the subplots to overlap
    g.figure.subplots_adjust(hspace=-.25)

    # Remove axes details that don't play well with overlap
    g.set_titles("")
    g.set(yticks=[], ylabel="")
    g.despine(bottom=True, left=True)

    # Make subplot backgrounds transparent and set axes
    for i, ax in enumerate(g.axes.flat):
        # Remove the background patch
        ax.patch.set_visible(False)

        # Set the x-axis limits from 0 to 24 (for our shifted hours)
        ax.set_xlim(0, 24)

        # Only add x-axis labels to the bottom-most plot
        if i == len(g.axes.flat) - 1:
            # Create tick positions every 4 hours on the 0-24 scale
            tick_positions = list(range(0, 25, 4))

            # Map tick positions back to original hours (6am to 6am)
            original_hours = [(pos + 6) % 24 for pos in tick_positions]

            time_labels = []
            for hour in original_hours:
                if hour == 0:
                    time_labels.append("12am")
                elif hour == 6:
                    time_labels.append("6am")
                elif hour < 12:
                    time_labels.append(f"{hour}am")
                elif hour == 12:
                    time_labels.append("12pm")
                else:
                    time_labels.append(f"{hour-12}pm")

            # The last label should be "6am" again
            time_labels[-1] = "6am"

            ax.set_xticks(tick_positions)
            ax.set_xticklabels(time_labels, rotation=0, ha='center', fontsize=12, color='white')
            ax.tick_params(colors='white')
            ax.set_xlabel("")  # Remove the x-axis title
        else:
            # Remove x-tick labels from all other plots
            ax.set_xticklabels([])

    # Remove titles and labels completely
    g.fig.suptitle("")

    # Save with a transparent background
    output_img = 'outputs/weekly_pattern.png'
    plt.savefig(output_img, bbox_inches='tight', dpi=300, transparent=True)
    plt.close()

    return output_img

def generate_weekly_pattern():
    """Generate and save weekly pattern visualization."""
    print(f"Fetching play history for user {USER_ID} in {YEAR}...")
    df = get_user_play_history(USER_ID, YEAR)

    if df.empty:
        print("No play data found!")
        return

    print(f"Processing {len(df)} play records...")

    # Create the density plot
    output_img = create_weekly_pattern_density(df, user_name='jac7k')
    print(f"Weekly pattern plot saved as {output_img}")

    # Generate HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Usage Pattern - {YEAR}</title>
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
        .pattern-container {{
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
        <h1>Weekly Usage Pattern - {YEAR}</h1>
        <div class="pattern-container">
            <img src="{output_img}" alt="Weekly Usage Pattern">
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
    print(f"\nDone! Open {OUTPUT_HTML} in your browser to view the weekly pattern.")

if __name__ == '__main__':
    generate_weekly_pattern()
