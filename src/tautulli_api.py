import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict
from .database import Database

# Load environment variables
load_dotenv()

class TautulliAPI:
    def __init__(self):
        self.base_url = os.getenv("TAUTULLI_URL")
        self.api_key = os.getenv("TAUTULLI_API_KEY")
        self.db = Database()
        
        if not self.base_url or not self.api_key:
            raise ValueError("TAUTULLI_URL and TAUTULLI_API_KEY must be set in .env file")

    def _make_request(self, cmd, **params):
        """Make a request to the Tautulli API"""
        url = f"{self.base_url}/api/v2"
        params = {
            "apikey": self.api_key,
            "cmd": cmd,
            **params
        }
        
        try:
            print(f"Making API request: {cmd}")  # Debug logging
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print(f"Error making request to Tautulli API: {e}")
            return None

    def sync_data(self, force_full_sync=False):
        """Sync data from Tautulli to local database"""
        last_sync = self.db.get_last_sync_time()
        
        # Get recently added items
        result = self._make_request("get_recently_added", count=100)
        if result and "response" in result:
            items = result["response"].get("data", {}).get("recently_added", [])
            for item in items:
                self.db.store_media_item(item)
        
        # Get history with pagination
        offset = 0
        while True:
            # If not a force sync, only get items since last sync
            params = {
                "length": 1000,
                "start": offset
            }
            
            if not force_full_sync and last_sync['history'] > 0:
                params["start_date"] = last_sync['history']
            
            result = self._make_request("get_history", **params)
            
            if not result or "response" not in result:
                break
                
            data = result["response"].get("data", {})
            history = data.get("data", [])
            if not history:
                break
                
            # Store each history item
            for item in history:
                self.db.store_play_history(item)
                # Also store the media item if it doesn't exist
                self.db.store_media_item(item)
            
            offset += len(history)
            total_records = data.get("recordsTotal", 0)
            if offset >= total_records:
                break
        
        print(f"Data sync completed. {'Full sync' if force_full_sync else 'Incremental sync'}")
        return True

    def get_recently_added(self, count=5):
        """Get recently added media"""
        # First try to get from API
        result = self._make_request("get_recently_added", count=count)
        if result and "response" in result:
            items = result["response"].get("data", {}).get("recently_added", [])
            # Store in database
            for item in items:
                self.db.store_media_item(item)
            return items
        
        # Fallback to database
        print("Falling back to database for recently added items")
        return self.db.get_recently_added(limit=count)

    def test_connection(self):
        """Test the connection to Tautulli"""
        result = self._make_request("get_activity")
        return result is not None

    def get_home_stats(self, time_range=7, stats_type=0):
        """
        Get home statistics
        time_range: number of days
        stats_type: 0 for plays, 1 for duration
        """
        result = self._make_request(
            "get_home_stats",
            time_range=time_range,
            stats_type=stats_type,
            stats_count=10
        )
        
        if result and "response" in result:
            stats = result["response"].get("data", [])
            trending_items = []
            
            # Process all media types
            for stat in stats:
                stat_id = stat.get('id', '')
                
                # Skip non-media stats
                if not any(x in stat_id for x in ['movies', 'tv']):  # Removed 'music' to exclude it
                    continue
                    
                # Determine media type and stat type
                if 'movies' in stat_id:
                    media_type = 'Movie'
                else:
                    media_type = 'TV Show'
                    
                stat_type = 'Popular' if 'popular' in stat_id else 'Most Played'
                
                for item in stat.get('rows', []):
                    # Get the appropriate title
                    if media_type == 'TV Show':
                        title = item.get('grandparent_title', item.get('title', 'Unknown Show'))
                    else:
                        title = item.get('title', 'Unknown')
                    
                    trending_items.append({
                        'title': title,
                        'year': item.get('year'),
                        'thumb': item.get('grandparent_thumb', item.get('thumb', '')),
                        'play_count': item.get('total_plays', 0),
                        'users_watched': item.get('users_watched', 0),
                        'media_type': media_type,
                        'stat_type': stat_type,
                        'rating_key': item.get('rating_key'),
                        'last_play': item.get('last_play', 0)
                    })
            
            # Sort by play count and users watched
            trending_items.sort(key=lambda x: (x.get('users_watched', 0), x.get('play_count', 0)), reverse=True)
            
            # Remove duplicates (same title might appear in both popular and most played)
            seen = set()
            unique_items = []
            for item in trending_items:
                key = (item['title'], item['media_type'])
                if key not in seen:
                    seen.add(key)
                    unique_items.append(item)
            
            return unique_items
        return []

    def get_history(self, length=1000, grouping=0):
        """
        Get watch history with pagination support
        """
        params = {
            "length": length,
            "grouping": grouping,
            "order_column": "date",
            "order_dir": "desc"
        }
        
        result = self._make_request("get_history", **params)
        if result and "response" in result:
            return result["response"].get("data", {}).get("data", [])
        return []

    def get_user_stats(self, days=7):
        """Get user statistics from watch history"""
        # Try to get from API first
        all_history = []
        offset = 0
        while True:
            result = self._make_request(
                "get_history",
                length=1000,
                start=offset
            )
            
            if not result or "response" not in result:
                break
                
            data = result["response"].get("data", {})
            history = data.get("data", [])
            if not history:
                break
                
            # Store data in database
            for item in history:
                self.db.store_play_history(item)
                self.db.store_media_item(item)
            
            # Filter items within our date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            start_time = int(start_date.timestamp())
            
            filtered_history = [
                item for item in history 
                if int(item.get("date", 0)) >= start_time
            ]
            
            all_history.extend(filtered_history)
            offset += len(history)
            
            total_records = data.get("recordsTotal", 0)
            if offset >= total_records:
                break
        
        if all_history:
            # Process API data
            user_stats = {}
            for item in all_history:
                user = item.get("friendly_name", "Unknown")
                duration = int(item.get("duration", 0))
                
                if user not in user_stats:
                    user_stats[user] = {
                        "plays": 0,
                        "duration": 0
                    }
                
                user_stats[user]["plays"] += 1
                user_stats[user]["duration"] += duration
            
            total_plays = sum(stats["plays"] for stats in user_stats.values())
            total_duration = sum(stats["duration"] for stats in user_stats.values())
            active_users = len(user_stats)
            
            return {
                "total_plays": total_plays,
                "total_duration": total_duration // 60,
                "active_users": active_users,
                "user_stats": [
                    {"user": user, "plays": stats["plays"], "duration": stats["duration"] // 60}
                    for user, stats in sorted(user_stats.items(), key=lambda x: x[1]["plays"], reverse=True)
                ]
            }
        
        # Fallback to database
        print("Falling back to database for user stats")
        return self.db.get_user_stats(days=days)

    def get_activity(self):
        """Get current activity"""
        result = self._make_request("get_activity")
        if result and "response" in result:
            return result["response"].get("data", {})
        return {}

    def get_most_watched_by_users(self, days=7):
        """Get content that has been watched by the most unique users"""
        # Try to get from API first
        all_history = []
        offset = 0
        while True:
            result = self._make_request(
                "get_history",
                length=1000,
                start=offset
            )
            
            if not result or "response" not in result:
                break
                
            data = result["response"].get("data", {})
            history = data.get("data", [])
            if not history:
                break
                
            # Store data in database
            for item in history:
                self.db.store_play_history(item)
                self.db.store_media_item(item)
            
            # Filter items within our date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            start_time = int(start_date.timestamp())
            
            filtered_history = [
                item for item in history 
                if int(item.get("date", 0)) >= start_time
            ]
            
            all_history.extend(filtered_history)
            offset += len(history)
            
            total_records = data.get("recordsTotal", 0)
            if offset >= total_records:
                break
        
        if all_history:
            # Process API data
            media_viewers = defaultdict(set)
            media_info = {}
            
            for item in all_history:
                # Skip music items
                if item.get("media_type") == "track":
                    continue
                
                # For TV shows, group by show rather than individual episodes
                if item.get("media_type") == "episode":
                    key = f"show_{item.get('grandparent_rating_key', item.get('rating_key'))}"
                    title = item.get("grandparent_title", "Unknown Show")
                    thumb = item.get("grandparent_thumb", "")
                else:
                    key = f"movie_{item.get('rating_key')}"
                    title = item.get("title", "Unknown Movie")
                    thumb = item.get("thumb", "")
                
                # Store user who watched this item
                user = item.get("friendly_name", "Unknown")
                media_viewers[key].add(user)
                
                # Store media info if we haven't already
                if key not in media_info:
                    media_info[key] = {
                        "title": title,
                        "type": "TV Show" if item.get("media_type") == "episode" else "Movie",
                        "thumb": thumb,
                        "year": item.get("year", ""),
                        "rating_key": item.get("rating_key"),
                    }
            
            # Convert to list and sort by number of unique viewers
            watched_items = []
            for key, viewers in media_viewers.items():
                if len(viewers) > 1:  # Only include items watched by multiple users
                    info = media_info[key]
                    watched_items.append({
                        **info,
                        "unique_viewers": len(viewers),
                        "viewers": sorted(list(viewers))
                    })
            
            # Sort by number of unique viewers, then by title
            watched_items.sort(key=lambda x: (-x["unique_viewers"], x["title"]))
            
            return watched_items
        
        # Fallback to database
        print("Falling back to database for most watched items")
        return self.db.get_most_watched(days=days, media_types=['movie', 'show', 'episode']) 