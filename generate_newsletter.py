from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
from src.tautulli_api import TautulliAPI

def format_duration(minutes):
    if not minutes:
        return ""
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"

def generate_newsletter():
    # Initialize Tautulli API
    api = TautulliAPI()
    
    # Get the date range for the newsletter
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

    # Get recently added content
    recently_added = api.get_recently_added(count=5)
    
    # Get popular content from home stats
    home_stats = api.get_home_stats(time_range=7)
    popular_content = []
    for stat in home_stats:
        if stat.get('id') in ['popular_movies', 'popular_tv']:
            for item in stat.get('rows', [])[:3]:
                popular_content.append({
                    'title': item.get('title'),
                    'thumb': item.get('thumb', ''),
                    'play_count': item.get('total_plays', 0)
                })

    # Get most watched content by unique users
    most_watched = api.get_most_watched_by_users(days=7)[:3]  # Top 3 most watched items

    # Get user statistics using the new method
    stats = api.get_user_stats(days=7)
    
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
        popular_content=popular_content,
        most_watched=most_watched,  # Add most watched content to the template
        user_stats=user_stats,
        server_name="Your Plex Server",
        generation_date=datetime.now().strftime("%B %d, %Y")
    )

    # Save the newsletter
    with open('newsletter_preview.html', 'w') as f:
        f.write(newsletter_html)

    print("Newsletter generated! Open newsletter_preview.html in your browser to preview.")

if __name__ == "__main__":
    generate_newsletter() 