# Changelog

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
