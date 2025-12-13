# Changelog

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
