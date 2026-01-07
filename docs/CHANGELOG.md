# Changelog

## 2026-01-06 - Top Albums & Music Library Sync Fix

### New Features
- **Top Albums section** in decoded manifest (under top artists)
  - Shows top 3 albums by play count with listener names
  - Excludes compilation albums ("Comps")

### Bug Fixes
- **Fixed music library sync** to properly link tracks to albums
  - Added `parent_rating_key` column to `media_items` table
  - Tracks now store their parent album's rating_key
  - Enables accurate album play count aggregation

- **Fixed artist thumbnail fallback**
  - Now uses database thumb when API doesn't return `grandparent_thumb`
  - All 3 top artist images now download correctly

### Database Updates
- Added `parent_rating_key` column migration to `media_items` table
- Music sync now populates: artist (grandparent) → album (parent) → track hierarchy

## 2025-12-31 - Decoded Manifest Generator for Year in Review

### New Features
- **Decoded Manifest Generator** (`scripts/generate_decoded_manifest.py`)
  - Generates `decoded_manifest.json` for the Blackbox Decoded year-in-review website
  - Daily cumulative library growth data (365 data points)
  - Server-wide weekly usage heatmap (day × hour, value in minutes)
  - Top 3 movies, TV shows, and artists by unique viewers/listeners
  - Top 4 users by total usage time
  - Full user directory with join dates (first play date)
  - Auto-downloads poster images and user avatars to `outputs/decoded_assets/`
  - Descriptions include both count and usernames (e.g., "Viewed by 5 users: jac7k, rakbarut...")

- **User avatar support**
  - Added `thumb` column to `users` table for storing avatar URLs
  - Avatars fetched from Tautulli `get_users` API
  - 22 user avatars downloaded

### Output Files
- `outputs/decoded_manifest.json` - JSON manifest for website consumption
- `outputs/decoded_assets/` - 31 images (9 content posters + 22 user avatars)

### Database Updates
- Added `thumb` column migration to `users` table in `database.py`
- Updated `store_play_history()` to save user thumb

## 2025-12-27 - Library Growth Visualization & Album Sync

### New Features
- **Library Growth Visualization** (`scripts/library_growth.py`)
  - Interactive HTML chart showing cumulative library growth over 2025
  - Three lines: Movies, TV Seasons, Albums
  - Animated "drawing" effect on page load
  - Built with Plotly for zoom/pan/hover interactivity
  - Dark theme matching existing visualizations
  - Output: `outputs/library_growth.html`

- **Album sync for music library**
  - Albums now synced with `added_at` timestamps (1,023 albums)
  - Enables tracking music library growth over time
  - Albums fetched via `get_children_metadata` from artist entries

### Dependencies
- Added `plotly` to project (interactive charting)

### Database Stats (After Sync)
- **Media items**: 14,115 total
  - Movies: 1,432
  - TV Shows: 207
  - Episodes: 7,536
  - Seasons: 595
  - Albums: 1,023
  - Artists: 384
  - Tracks: 3,961
- **Play history**: 9,752 records
- **Storage tracked**: 9.29 TB

## 2025-12-17 - Sync Fixes & Pruning Reports

### Bug Fixes
- **Fixed stale library data from Tautulli cache**
  - Added `refresh=true` parameter to all `get_library_media_info` API calls
  - Tautulli was returning cached data (132 shows) instead of actual library (204 shows)
  - Sync now retrieves fresh data directly from Plex

- **Fixed shows with changed rating_keys**
  - Shows like Avatar: The Last Airbender, Batman: The Animated Series, Big Little Lies had 0 episodes
  - Root cause: Plex assigned new rating_keys when shows were re-added to library
  - Old orphan entries are now cleaned up before sync

### New Features
- **Stale data cleanup** before full sync
  - New `remove_stale_media_items()` method in database.py
  - Collects all current rating_keys from Plex and removes orphaned DB entries
  - Prevents accumulation of outdated records

- **Pruning reports script** (`scripts/generate_pruning_reports.py`)
  - Generates CSV reports for library pruning decisions
  - `outputs/movies_least_accessed.csv` - Movies sorted by play count
  - `outputs/tvshows_least_accessed.csv` - TV shows aggregated by series
  - Includes: title, year, episode_count, file size, play count, unique users, users list
  - Proper CSV quoting for titles starting with numbers

### Database Stats (After Sync)
- **Shows**: 204 (was 132) - +72 shows recovered
- **Episodes**: 7,405 (was 5,558) - +1,847 episodes recovered
- **Seasons**: 590 (was 411)
- **Movies**: 1,409

### Code Updates
- `src/tautulli_api.py`:
  - Added `refresh="true"` to `get_library_media_info` calls
  - Added `_collect_all_rating_keys()` for stale data detection
  - Added `_collect_children_keys()` for recursive key collection
  - Updated `sync_full_library()` with optional `cleanup_stale` parameter
- `src/database.py`:
  - Added `remove_stale_media_items()` method for cleaning orphaned records
- `scripts/generate_pruning_reports.py`:
  - New script for generating pruning decision CSVs
  - Added `unique_users` column
  - Uses `QUOTE_NONNUMERIC` for proper spreadsheet formatting

## 2025-12-15 - Full Library Sync & File Size Tracking

### New Features
- **File Size Tracking**
  - Added `file_size` column to `media_items` table (stored in bytes)
  - Automatic database migration for existing installations
  - File sizes included directly from `get_library_media_info` API (no extra API calls needed)
  - Tracks total library storage: **6.55 TB** across movies and TV episodes

- **Full Library Sync** (`--full-sync` flag)
  - New comprehensive sync mode syncs entire Plex library
  - Recursive fetching for TV shows: Show → Season → Episode hierarchy
  - Captures all media items from all libraries (movies, TV, music)
  - Complete play history sync (all 9,890+ records)
  - Usage: `python scripts/sync_data.py --full-sync`

- **CSV Export**
  - Generated `outputs/media_by_size.csv` with all movies/episodes sorted by size
  - Includes: title, media_type, size_gb
  - 5,212+ items cataloged

### Bug Fixes
- **Fixed incomplete library sync**: Was only syncing last 100 recently added items
  - Now syncs complete library: **10,715+ total items**
  - Movies: 1,193 (was ~350)
  - Episodes: 5,551 (was ~1,200)
  - Music tracks: 3,245
- **Fixed incomplete play history**: Was missing ~2,000 records
  - Now captures: **8,444 plays** (85% of available history)
  - Improved pagination logic in history sync

### Code Updates
- `src/tautulli_api.py`:
  - Added `_get_file_size()` method to fetch file sizes from metadata
  - Added `sync_full_library()` for complete library sync
  - Added `_sync_library_recursive()` for TV show hierarchy traversal
  - Updated `sync_data()` to support `full_sync` parameter
- `src/database.py`:
  - Added `file_size INTEGER` column to media_items schema
  - Added migration logic to add column to existing databases
  - Updated `store_media_item()` to handle file_size field
- `scripts/sync_data.py`:
  - Added `--full-sync` command-line argument
  - Enhanced statistics output with file size breakdowns
  - Added storage-by-type reporting (GB per media type)

### Database Stats (After Full Sync)
- **Media items**: 10,715 (up from 4,418)
  - Episodes: 5,551 (4,378 with file sizes = 4.0 TB)
  - Movies: 1,193 (834 with file sizes = 2.7 TB)
  - Music tracks: 3,245
  - Shows/Seasons: 543
- **Play history**: 8,444 records (up from 7,749)
- **Users**: 22 active users
- **Total library size**: 6.55 TB tracked

## 2025-12-12 - Repository Reorganization & Activity Heatmaps

### New Features
- **Activity Heatmap Visualization** (`scripts/heatmap.py`)
  - GitHub-style contribution heatmap for user activity
  - Separate heatmaps for music plays and video plays (movies + TV)
  - Pastel blue gradient color scheme
  - Individual square boxes for each day of the year
  - Independent scaling for each heatmap (music vs video)
  - Outputs to `outputs/viz-testing.html`

### Repository Structure
- **Created `scripts/` folder** - All executable scripts moved here
  - `generate_newsletter.py` - Newsletter generator
  - `sync_data.py` - Data sync utility
  - `query.py` - SQL query tool
  - `heatmap.py` - Heatmap visualization generator
- **Created `docs/` folder** - Documentation consolidated
  - `CHANGELOG.md` - This file
- **Created `outputs/` folder** - Generated files directory (gitignored)
  - `newsletter_preview.html` - Generated newsletters
  - `viz-testing.html` - Visualization test outputs
  - `heatmap_viz.png` - Heatmap images

### Code Updates
- Added `sys.path` fixes to all scripts for proper module imports from `src/`
- Updated `generate_newsletter.py` to output to `outputs/` directory
- Removed obsolete project plan document

### Documentation
- **Major README.md overhaul**
  - Added comprehensive project structure diagram
  - High-level overview suitable for new developers
  - Updated all usage examples with new script paths
  - Added tech stack section
  - Documented all features and visualizations
- Updated `.gitignore`
  - Added `.DS_Store` (macOS metadata)
  - Added `outputs/` directory
  - Removed obsolete `session_summaries/` entry

## 2025-12-09 - Major Refactor

### Architecture Changes
- **Separated concerns into 3 modules:**
  - `sync_data.py` - Data sync from Tautulli to database
  - `generate_newsletter.py` - Visualization and newsletter generation
  - `query.py` - Ad-hoc SQL queries on database

### Newsletter Simplification
- Removed: Recently Added, Trending, Community Favorites sections
- Kept: User Activity Stats + 3 Visualizations only
- Changed time range: 7/30 days → entire year (365 days)

### Code Cleanup
- Removed test/debug files (test_*.py, debug_*.py, verify_counts.py)
- Removed full library sync (kept incremental sync only)
- Removed design mode feature
- Removed unused dependencies: beautifulsoup4, pillow
- Removed unused imports: shutil, PIL
- Cleaned up unused command-line arguments

### Documentation
- Simplified README with clear 3-step workflow
- Removed LICENSE file

### Current State
- Database: 4,318 media items, 7,749 play history records, 21 users
- Newsletter: Clean user stats + visualizations for entire 2025
- Query tool: Working SQL query interface for data exploration
