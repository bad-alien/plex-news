# Plex Newsletter Generator

A Python application that generates beautiful weekly newsletters for your Plex server using Tautulli statistics.

## Features

- Weekly digest of your Plex server activity
- Recently added content overview
- Trending content analysis
- Community favorites (most watched by multiple users)
- User activity statistics
- Beautiful, responsive HTML email template
- SQLite database for caching and offline access
- Customizable with your own logo and assets

## Requirements

- Python 3.x
- Tautulli server with API access
- Plex Media Server

## Installation

1. Clone the repository:
```bash
git clone https://github.com/bad-alien/plex-news.git
cd plex-news
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your Tautulli configuration:
```
TAUTULLI_URL=http://your.tautulli.server:port
TAUTULLI_API_KEY=your_api_key
```

5. (Optional) Add your logo:
- Place your logo in `assets/images/` as either `logo.png` or `logo.jpg`

## Usage

Generate a newsletter:
```bash
python generate_newsletter.py
```

The script will:
1. Connect to your Tautulli server
2. Gather statistics and media information
3. Generate an HTML newsletter
4. Save it as `newsletter_preview.html`

## Customization

### Assets
Place your custom assets in the `assets/images/` directory:
- `logo.png` or `logo.jpg` - Your server logo
- Section icons (optional):
  * `recently-added.png`
  * `trending.png`
  * `community.png`
  * `stats.png`
  * `play.png`
  * `users.png`

### Database
The application uses SQLite to cache data and reduce API calls. The database is automatically created at `data/plex_stats.db`.

## License

MIT License - See LICENSE file for details. 