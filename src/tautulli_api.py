import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict

# Load environment variables
load_dotenv()

class TautulliAPI:
    def __init__(self):
        self.base_url = os.getenv("TAUTULLI_URL")
        self.api_key = os.getenv("TAUTULLI_API_KEY")
        
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
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to Tautulli API: {e}")
            return None

    def get_recently_added(self, count=5):
        """Get recently added media"""
        result = self._make_request("get_recently_added", count=count)
        if result and "response" in result:
            return result["response"].get("data", {}).get("recently_added", [])
        return []

    def test_connection(self):
        """Test the connection to Tautulli"""
        result = self._make_request("get_activity")
        return result is not None

    def get_home_stats(self, time_range=7, stats_type=0):
        """Get home statistics"""
        result = self._make_request("get_home_stats", time_range=time_range, stats_type=stats_type)
        if result and "response" in result:
            return result["response"].get("data", [])
        return []

    def get_history(self, length=50, grouping=0):
        """
        Get watch history
        length: number of items to return
        grouping: 0 for no grouping, 1 for grouped
        """
        result = self._make_request("get_history", length=length, grouping=grouping)
        if result and "response" in result:
            return result["response"].get("data", {}).get("data", [])
        return []

    def get_user_stats(self, days=7):
        """Get user statistics from watch history"""
        # Get history for the past X days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Convert dates to timestamps
        start_time = int(start_date.timestamp())
        
        result = self._make_request("get_history", length=1000, start_date=start_time)
        if not result or "response" not in result:
            return {
                "total_plays": 0,
                "total_duration": 0,
                "active_users": 0,
                "user_stats": []
            }
        
        history = result["response"].get("data", {}).get("data", [])
        
        # Process history
        user_stats = {}
        for item in history:
            user = item.get("friendly_name", "Unknown")
            duration = int(item.get("duration", 0))
            
            if user not in user_stats:
                user_stats[user] = {
                    "plays": 0,
                    "duration": 0
                }
            
            user_stats[user]["plays"] += 1
            user_stats[user]["duration"] += duration
        
        # Calculate totals
        total_plays = sum(stats["plays"] for stats in user_stats.values())
        total_duration = sum(stats["duration"] for stats in user_stats.values())
        active_users = len(user_stats)
        
        return {
            "total_plays": total_plays,
            "total_duration": total_duration,
            "active_users": active_users,
            "user_stats": [
                {"user": user, **stats}
                for user, stats in user_stats.items()
            ]
        }

    def get_activity(self):
        """Get current activity"""
        result = self._make_request("get_activity")
        if result and "response" in result:
            return result["response"].get("data", {})
        return {}

    def get_most_watched_by_users(self, days=7):
        """
        Get content that has been watched by the most unique users
        Returns a list of items sorted by number of unique viewers
        """
        # Get history for the past X days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_time = int(start_date.timestamp())
        
        # Get extended history to ensure we capture all users
        result = self._make_request("get_history", length=1000, start_date=start_time)
        if not result or "response" not in result:
            return []
        
        history = result["response"].get("data", {}).get("data", [])
        
        # Track viewers per media item
        media_viewers = defaultdict(set)
        media_info = {}
        
        for item in history:
            # Create a unique identifier for the media item
            rating_key = item.get("rating_key")
            if not rating_key:
                continue
                
            # Store user who watched this item
            user = item.get("friendly_name", "Unknown")
            media_viewers[rating_key].add(user)
            
            # Store media info if we haven't already
            if rating_key not in media_info:
                media_info[rating_key] = {
                    "title": item.get("full_title", item.get("title", "Unknown")),
                    "type": item.get("media_type", "unknown"),
                    "thumb": item.get("thumb", ""),
                    "year": item.get("year", ""),
                    "rating_key": rating_key,
                    "parent_title": item.get("parent_title", ""),  # For TV shows
                    "grandparent_title": item.get("grandparent_title", ""),  # For TV episodes
                    "media_index": item.get("media_index", ""),  # Episode/Season number
                    "parent_media_index": item.get("parent_media_index", ""),  # Season number for episodes
                }
        
        # Convert to list and sort by number of unique viewers
        watched_items = []
        for rating_key, viewers in media_viewers.items():
            info = media_info[rating_key]
            watched_items.append({
                **info,
                "unique_viewers": len(viewers),
                "viewers": sorted(list(viewers))
            })
        
        # Sort by number of unique viewers, then by title
        watched_items.sort(key=lambda x: (-x["unique_viewers"], x["title"]))
        
        return watched_items 