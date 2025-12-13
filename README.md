# Plex Newsletter Generator

A Python-based tool for generating visual newsletters from Plex Media Server usage data via Tautulli. Syncs play history and library data to a local SQLite database, then generates HTML newsletters with activity visualizations.

## Project Structure

```
plex-news/
├── scripts/              # Executable scripts
│   ├── sync_data.py           # Sync data from Tautulli to local DB
│   ├── generate_newsletter.py # Generate HTML newsletter with charts
│   ├── query.py               # Run SQL queries on database
│   └── heatmap.py            # Generate activity heatmaps (testing)
├── src/                  # Core library modules
│   ├── database.py           # SQLite database interface
│   ├── tautulli_api.py       # Tautulli API client
│   └── visualizations.py     # Chart generation functions
├── templates/            # Jinja2 HTML templates
│   └── newsletter.html       # Newsletter template
├── assets/               # Static assets
│   ├── images/              # Generated charts and logos
│   └── cache/               # Cached media thumbnails
├── outputs/              # Generated files (gitignored)
│   ├── newsletter_preview.html
│   └── viz-testing.html
├── data/                 # SQLite database (gitignored)
│   └── plex_stats.db
└── docs/                 # Documentation
    └── CHANGELOG.md
```

## Setup

1. **Install dependencies:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure Tautulli connection:**
Create `.env` file:
```
TAUTULLI_URL=http://your.tautulli.server:port
TAUTULLI_API_KEY=your_api_key
```

## Usage

### Sync Data from Tautulli
```bash
python scripts/sync_data.py              # Incremental sync
python scripts/sync_data.py --clear      # Full sync (clears DB first)
```

### Generate Newsletter
```bash
python scripts/generate_newsletter.py
```
Output: `outputs/newsletter_preview.html`

### Query Database
```bash
python scripts/query.py                  # Run custom SQL query
python scripts/query.py --schema         # View database schema
```
Edit the SQL query in `scripts/query.py` to explore your data.

### Generate Activity Heatmaps (Testing)
```bash
python scripts/heatmap.py
```
Output: `outputs/viz-testing.html`

## Features

- **Automated Data Collection**: Incremental sync from Tautulli API
- **SQLite Database**: Local storage for play history, media items, and users
- **Rich Visualizations**:
  - Daily usage density plots (when server is most active by day)
  - User content engagement scatter plots
  - Library growth over time
  - Activity heatmaps (GitHub-style contribution graphs)
- **HTML Newsletter**: Jinja2-templated, styled with inline CSS

## Tech Stack

- **Python 3.x** with pandas, matplotlib, seaborn
- **SQLite** for local data storage
- **Jinja2** for HTML templating
- **Tautulli API** for Plex usage data
