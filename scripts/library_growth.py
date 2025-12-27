#!/usr/bin/env python3
"""
Library Growth Visualization

Generates an interactive HTML chart showing cumulative growth of:
- Movies
- TV Seasons
- Albums

Over time based on added_at timestamps.
"""

import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys
import os
import re

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = 'data/plex_stats.db'
OUTPUT_HTML = 'outputs/library_growth.html'


def get_library_data():
    """Fetch added_at data for movies, seasons, and albums."""
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            DATE(added_at, 'unixepoch') as date_added,
            media_type,
            COUNT(*) as count
        FROM media_items
        WHERE media_type IN ('movie', 'season', 'album')
            AND added_at IS NOT NULL
            AND added_at > 0
        GROUP BY date_added, media_type
        ORDER BY date_added
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def prepare_cumulative_data(df):
    """Prepare cumulative counts for each media type."""
    # Convert to datetime
    df['date_added'] = pd.to_datetime(df['date_added'])

    # Fixed date range: Jan 1, 2025 - Dec 31, 2025
    start_date = pd.Timestamp('2025-01-01')
    end_date = pd.Timestamp('2025-12-31')
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')

    result = {}

    for media_type in ['movie', 'season', 'album']:
        # Filter for this media type
        type_df = df[df['media_type'] == media_type].copy()

        # Create a series with all dates
        type_df = type_df.set_index('date_added')['count']
        type_df = type_df.reindex(all_dates, fill_value=0)

        # Calculate cumulative sum
        cumulative = type_df.cumsum()

        # For movies, we need to add the pre-2025 count as the starting point
        if media_type == 'movie':
            pre_2025 = df[(df['media_type'] == 'movie') &
                          (df['date_added'] < start_date)]['count'].sum()
            cumulative = cumulative + pre_2025

        result[media_type] = cumulative

    return result, all_dates


def create_visualization(data, dates):
    """Create interactive Plotly chart with animation frames."""

    # Color scheme
    colors = {
        'movie': '#e74c3c',    # Red
        'season': '#3498db',   # Blue
        'album': '#2ecc71'     # Green
    }

    labels = {
        'movie': 'Movies',
        'season': 'TV Seasons',
        'album': 'Albums'
    }

    # Calculate fixed y-axis range based on final values
    max_y = max(data[mt].max() for mt in ['movie', 'season', 'album'])
    y_range = [0, max_y * 1.1]

    fig = go.Figure()

    # Add initial empty traces (will be animated)
    for media_type in ['movie', 'season', 'album']:
        fig.add_trace(go.Scatter(
            x=[dates[0]],
            y=[data[media_type].iloc[0]],
            mode='lines',
            name=labels[media_type],
            line=dict(color=colors[media_type], width=2.5),
            hovertemplate=f'<b>{labels[media_type]}</b><br>' +
                         'Date: %{x|%Y-%m-%d}<br>' +
                         'Total: %{y:,}<extra></extra>'
        ))

    # Create animation frames - sample every few days for smooth animation
    n_frames = 60  # Number of animation frames
    step = max(1, len(dates) // n_frames)
    frame_indices = list(range(0, len(dates), step))
    if frame_indices[-1] != len(dates) - 1:
        frame_indices.append(len(dates) - 1)

    frames = []
    for i in frame_indices:
        frame_data = []
        for media_type in ['movie', 'season', 'album']:
            frame_data.append(go.Scatter(
                x=dates[:i+1],
                y=data[media_type].iloc[:i+1]
            ))
        frames.append(go.Frame(data=frame_data, name=str(i)))

    fig.frames = frames

    # Layout with fixed axes
    fig.update_layout(
        title=dict(
            text='Library Growth Over Time (2025)',
            font=dict(size=24, color='#e6e6e6'),
            x=0.5
        ),
        xaxis=dict(
            title=dict(text='Date', font=dict(color='#e6e6e6')),
            gridcolor='#30363d',
            tickformat='%b',
            tickfont=dict(color='#8b949e'),
            range=[dates[0], dates[-1]],
            fixedrange=False
        ),
        yaxis=dict(
            title=dict(text='Cumulative Count', font=dict(color='#e6e6e6')),
            gridcolor='#30363d',
            tickfont=dict(color='#8b949e'),
            range=y_range,
            fixedrange=False
        ),
        plot_bgcolor='#0d1117',
        paper_bgcolor='#0d1117',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            font=dict(color='#e6e6e6')
        ),
        hovermode='x unified',
        margin=dict(t=100, l=60, r=40, b=60),
        updatemenus=[dict(
            type='buttons',
            showactive=False,
            visible=False,
            buttons=[dict(
                label='Play',
                method='animate',
                args=[None, dict(
                    frame=dict(duration=50, redraw=True),
                    fromcurrent=True,
                    mode='immediate'
                )]
            )]
        )]
    )

    return fig


def generate_html(fig):
    """Generate standalone HTML file with auto-play animation."""
    # Get the div ID from the figure
    plot_div = fig.to_html(full_html=False, include_plotlyjs=False)

    # Extract div id
    div_match = re.search(r'id="([^"]+)"', plot_div)
    div_id = div_match.group(1) if div_match else 'plotly-graph'

    custom_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Plex Library Growth</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background-color: #0d1117;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #8b949e;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        {plot_div}
        <div class="footer">
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
    <script>
        // Auto-play animation on load
        window.addEventListener('load', function() {{
            var plotDiv = document.getElementById('{div_id}');
            if (plotDiv && plotDiv.data) {{
                Plotly.animate('{div_id}', null, {{
                    frame: {{duration: 50, redraw: true}},
                    mode: 'immediate',
                    fromcurrent: false,
                    transition: {{duration: 0}}
                }});
            }}
        }});
    </script>
</body>
</html>
"""

    return custom_html


def main():
    print("Fetching library data...")
    df = get_library_data()

    if df.empty:
        print("No data found!")
        return

    print(f"Found {len(df)} date/type records")

    # Show summary
    for media_type in ['movie', 'season', 'album']:
        total = df[df['media_type'] == media_type]['count'].sum()
        print(f"  {media_type}: {total} items")

    print("\nPreparing cumulative data...")
    data, dates = prepare_cumulative_data(df)

    print("Creating visualization...")
    fig = create_visualization(data, dates)

    print(f"Saving to {OUTPUT_HTML}...")
    html = generate_html(fig)

    with open(OUTPUT_HTML, 'w') as f:
        f.write(html)

    print(f"\nDone! Open {OUTPUT_HTML} in your browser to view.")


if __name__ == '__main__':
    main()
