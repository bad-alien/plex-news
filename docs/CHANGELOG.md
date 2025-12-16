# Changelog

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
