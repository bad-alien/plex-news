import sys
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# Add project root to path so we can import from src/
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tautulli_api import TautulliAPI
from src.visualizations import (
    create_daily_usage_density,
    create_user_content_scatter,
    create_content_growth_line
)

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

def generate_newsletter():
    """
    Generate a Plex newsletter from database.

    Note: Run sync_data.py first to populate the database with fresh data.
    """
    # Initialize Tautulli API (just for API access, not syncing)
    api = TautulliAPI()
    
    # Get the date range for the newsletter (entire year)
    end_date = datetime.now()
    start_date = datetime(end_date.year, 1, 1)  # January 1st of current year
    date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

    print("Generating visualizations...")

    # Generate usage density plot (entire year)
    history_data = api.get_play_history(days=365)
    usage_density_path = create_daily_usage_density(history_data)
    print("Created usage density plot")

    # Generate user content scatter plot (entire year)
    user_stats_viz = api.get_user_stats_by_media(days=365)
    user_scatter_path = create_user_content_scatter(user_stats_viz)
    print("Created user content scatter plot")

    # Generate content growth line plot using the accurate, synced database
    library_stats = api.db.get_all_media_items()
    growth_line_path = create_content_growth_line(library_stats)
    print("Created content growth line plot")

    # Ensure assets exist and get logo path
    logo_path = ensure_assets()

    # Get user statistics (entire year)
    stats = api.get_user_stats(days=365)
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
    from pathlib import Path
    Path("outputs").mkdir(exist_ok=True)

    with open('outputs/newsletter_preview.html', 'w') as f:
        f.write(newsletter_html)

    print("\nNewsletter generated! Open outputs/newsletter_preview.html in your browser to preview.")
    if not logo_path:
        print("\nNote: No logo found. Please add a logo.png file to assets/images/ directory.")

if __name__ == "__main__":
    print("Generating newsletter from database...")
    print("(Run sync_data.py first if you need fresh data)\n")
    generate_newsletter() 