# Plex Newsletter Generator

Generates a simple newsletter with Plex server user activity stats and visualizations.

## Setup

1. Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Create a `.env` file with your Tautulli credentials:
```
TAUTULLI_URL=http://your.tautulli.server:port
TAUTULLI_API_KEY=your_api_key
```

## Usage

### 1. Sync Data from Tautulli
Pull and sync data from Tautulli to local database:
```bash
python sync_data.py              # Incremental sync (new data only)
python sync_data.py --clear      # Clear database and full sync
```

### 2. Generate Newsletter
Create newsletter with visualizations from database:
```bash
python generate_newsletter.py
```
Output: `newsletter_preview.html`

### 3. Query Data
Run custom SQL queries on your data:
```bash
python query.py                  # Run the query in query.py
python query.py --schema         # View database structure
```

Edit the SQL query at the top of `query.py` to explore your data.

## What's Included

- **User Activity Stats**: Total plays, watch time, active users (entire year)
- **Visualizations**:
  - Server usage patterns (when server is most active)
  - User content engagement (how users interact with different content types)
  - Library growth over time
