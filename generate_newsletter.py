from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
from src.tautulli_api import TautulliAPI
from pathlib import Path
import argparse

def format_duration(minutes):
    if not minutes:
        return "0m"
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"

def generate_newsletter(force_sync=False, force_full_sync=False):
    """
    Generate a Plex newsletter
    
    Args:
        force_sync (bool): Whether to force a sync with Tautulli
        force_full_sync (bool): Whether to force a full sync instead of incremental
    """
    # Initialize Tautulli API
    api = TautulliAPI()
    
    # Sync data if requested or if it's the first run
    if force_sync or force_full_sync:
        print("Syncing data from Tautulli...")
        api.sync_data(force_full_sync=force_full_sync)
    
    # Get the date range for the newsletter
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

    # Check for logo file
    logo_path = None
    if Path("assets/images/logo.png").exists():
        logo_path = "assets/images/logo.png"
    elif Path("assets/images/logo.jpg").exists():
        logo_path = "assets/images/logo.jpg"

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
    
    user_stats = [
        {'label': 'Total Plays', 'value': stats['total_plays']},
        {'label': 'Watch Time', 'value': format_duration(stats['total_duration'])},
        {'label': 'Active Users', 'value': stats['active_users']}
    ]

    # Add top users if available
    user_details = sorted(stats['user_stats'], key=lambda x: x['plays'], reverse=True)
    if user_details:
        top_user = user_details[0]
        user_stats.append({
            'label': 'Most Active User',
            'value': f"{top_user['user']} ({top_user['plays']} plays)"
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
        user_stats=user_stats,
        server_name="Your Plex Server",
        generation_date=datetime.now().strftime("%B %d, %Y"),
        logo_path=logo_path  # Add logo path to template
    )

    # Save the newsletter
    with open('newsletter_preview.html', 'w') as f:
        f.write(newsletter_html)

    print("\nNewsletter generated! Open newsletter_preview.html in your browser to preview.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Plex newsletter")
    parser.add_argument("--force-sync", action="store_true", help="Force a sync with Tautulli")
    parser.add_argument("--force-full-sync", action="store_true", help="Force a full sync instead of incremental")
    args = parser.parse_args()
    
    generate_newsletter(
        force_sync=args.force_sync,
        force_full_sync=args.force_full_sync
    ) 