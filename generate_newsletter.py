from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
from src.tautulli_api import TautulliAPI
from src.visualizations import (
    create_daily_usage_density,
    create_user_content_scatter,
    create_content_growth_line
)
from pathlib import Path
import argparse
import shutil
import os

def format_duration(minutes):
    if not minutes:
        return "0m"
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"

def ensure_assets():
    """Ensure all required assets exist"""
    # Create assets directory structure
    assets_dir = Path("assets/images")
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Check for logo file
    logo_path = assets_dir / "logo.png"
    if not logo_path.exists():
        # Create a default logo.txt to remind users
        with open(assets_dir / "logo.txt", "w") as f:
            f.write("Please place your logo.png file in this directory.")
    
    return logo_path if logo_path.exists() else None

def generate_newsletter(force_sync=False, force_full_sync=False, design_mode=False):
    """
    Generate a Plex newsletter
    
    Args:
        force_sync (bool): Whether to force a sync with Tautulli
        force_full_sync (bool): Whether to force a full sync instead of incremental
        design_mode (bool): Use only cached data, don't make API calls (for design testing)
    """
    # Initialize Tautulli API
    api = TautulliAPI()
    
    # Sync data if requested or if it's the first run (but not in design mode)
    if not design_mode:
        if force_full_sync:
            print("Forcing a full library sync from Tautulli...")
            api.full_library_sync()
            print("Forcing a full history sync from Tautulli...")
            api.sync_data(force_full_sync=True)
        elif force_sync:
            print("Forcing an incremental data sync from Tautulli...")
            api.sync_data()
    elif design_mode:
        print("Design mode: Using cached data only, no API calls")
    
    # Get the date range for the newsletter
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

    print("Generating visualizations...")
    
    if design_mode:
        # Use cached data from database
        print("Using cached database data for visualizations...")
        
        # Get history data from database
        history_data = api.db.get_all_history(days=30)
        usage_density_path = create_daily_usage_density(history_data)
        print("Created usage density plot from cached data")
        
        # Get user stats from database
        user_stats = api.db.get_user_stats_by_media(days=30)
        user_scatter_path = create_user_content_scatter(user_stats)
        print("Created user content scatter plot from cached data")
        
        # Get library stats from database
        library_stats = api.db.get_all_media_items()
        growth_line_path = create_content_growth_line(library_stats)
        print("Created content growth line plot from cached data")
    else:
        # Generate usage density plot
        history_data = api.get_play_history(days=30)  # Get 30 days for better density estimation
        usage_density_path = create_daily_usage_density(history_data)
        print("Created usage density plot")
        
        # Generate user content scatter plot
        user_stats = api.get_user_stats_by_media(days=30)
        user_scatter_path = create_user_content_scatter(user_stats)
        print("Created user content scatter plot")
        
        # Generate content growth line plot using the accurate, synced database
        library_stats = api.db.get_all_media_items()
        growth_line_path = create_content_growth_line(library_stats)
        print("Created content growth line plot")

    # Ensure assets exist and get logo path
    logo_path = ensure_assets()

    if design_mode:
        # Use cached data for newsletter content
        recently_added = api.db.get_recently_added(limit=5)
        home_stats = []  # Empty for design mode, or could add db method
        most_watched = api.db.get_most_watched(days=7, media_types=['movie', 'show', 'episode'])
        stats = api.db.get_user_stats(days=7)
    else:
        # Get recently added content (excluding music)
        recently_added = api.get_recently_added(count=5)
        recently_added = [
            item for item in recently_added 
            if item.get('media_type') not in ['track', 'album', 'artist']
        ]
        print(f"Found {len(recently_added)} recently added items")

        # Get popular content from home stats (music already excluded in API)
        home_stats = api.get_home_stats(time_range=7)
        print(f"Found {len(home_stats)} trending items")

        # Get most watched content by unique users (music already excluded)
        most_watched = api.get_most_watched_by_users(days=7)
        print(f"Found {len(most_watched)} items watched by multiple users")

        # Get user statistics
        stats = api.get_user_stats(days=7)
        print(f"User stats: {stats}")

    # Format user stats for display
    user_stats_display = [
        {'label': 'Total Plays', 'value': stats['total_plays']},
        {'label': 'Watch Time', 'value': format_duration(stats['total_duration'])},
        {'label': 'Active Users', 'value': stats['active_users']}
    ]

    # Add top users if available
    user_details = sorted(stats['user_stats'], key=lambda x: x['plays'], reverse=True)
    if user_details:
        top_user = user_details[0]
        # Handle both 'user' and 'username' fields for compatibility
        user_name = top_user.get('user') or top_user.get('username') or 'Unknown User'
        user_stats_display.append({
            'label': 'Most Active User',
            'value': f"{user_name} ({top_user['plays']} plays)"
        })

    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('newsletter.html')

    # Render the template
    newsletter_html = template.render(
        date_range=date_range,
        recently_added=recently_added,
        popular_content=home_stats[:5],  # Limit to top 5
        most_watched=most_watched[:3],  # Limit to top 3
        user_stats=user_stats_display,
        server_name="Blackbox Alexandria",
        generation_date=datetime.now().strftime("%B %d, %Y"),
        logo_path=str(logo_path) if logo_path else None,
        # Add visualization paths
        usage_density_path=usage_density_path,
        user_scatter_path=user_scatter_path,
        growth_line_path=growth_line_path
    )

    # Save the newsletter
    with open('newsletter_preview.html', 'w') as f:
        f.write(newsletter_html)

    print("\nNewsletter generated! Open newsletter_preview.html in your browser to preview.")
    if not logo_path:
        print("\nNote: No logo found. Please add a logo.png file to assets/images/ directory.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Plex newsletter")
    parser.add_argument("--force-sync", action="store_true", help="Force a sync with Tautulli")
    parser.add_argument("--force-full-sync", action="store_true", help="Force a full sync instead of incremental")
    parser.add_argument("--design-mode", action="store_true", help="Use cached data only (for design testing)")
    args = parser.parse_args()
    
    # Stop the local server if running, to avoid confusion
    # (Note: This is a placeholder for actual server management)
    
    generate_newsletter(
        force_sync=args.force_sync,
        force_full_sync=args.force_full_sync,
        design_mode=args.design_mode
    ) 