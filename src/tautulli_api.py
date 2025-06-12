import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from .database import Database
import shutil
from PIL import Image, ImageDraw, ImageFont

# Load environment variables
load_dotenv(override=True)

class TautulliAPI:
    def __init__(self):
        self.base_url = os.getenv("TAUTULLI_URL", "").rstrip('/')
        self.api_key = os.getenv("TAUTULLI_API_KEY", "")
        self.db = Database()
        self.image_cache_dir = Path("assets/cache/images")
        self.image_cache_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        try:
            self.db.begin_transaction()
            
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
            
            self.db.commit_transaction()
            print(f"Data sync completed. {'Full sync' if force_full_sync else 'Incremental sync'}")
            return True
            
        except Exception as e:
            print(f"Error during sync: {e}")
            self.db.rollback_transaction()
            return False

    def _download_image(self, url, rating_key, img_type='thumb'):
        """Download and cache an image locally"""
        if not rating_key:
            print(f"Warning: No rating key provided for image download")
            return None
            
        # Check if image is already cached
        for ext in ['.jpg', '.png']:
            cached_path = self.image_cache_dir / f"{rating_key}_{img_type}{ext}"
            if cached_path.exists() and os.path.getsize(cached_path) > 0:
                return str(cached_path)
        
        try:
            # First try to get the Plex server URL and token from Tautulli
            server_info = self._make_request("get_server_info")
            if server_info and "response" in server_info:
                plex_url = server_info["response"].get("data", {}).get("pms_url", "")
                plex_token = server_info["response"].get("data", {}).get("pms_token", "")
                
                if plex_url and plex_token:
                    # Get metadata to find the correct image path
                    metadata_result = self._make_request("get_metadata")
                    if metadata_result and "response" in metadata_result:
                        metadata = metadata_result["response"].get("data", {})
                        
                        # Get the appropriate image URL based on type
                        if img_type == 'thumb':
                            image_path = metadata.get('thumb', '')
                        elif img_type == 'art':
                            image_path = metadata.get('art', '')
                        else:
                            image_path = metadata.get('banner', '')
                        
                        if image_path:
                            # Convert the path to a direct Plex URL
                            if image_path.startswith('/'):
                                direct_url = f"{plex_url}{image_path}?X-Plex-Token={plex_token}"
                            else:
                                direct_url = image_path
                            
                            try:
                                response = requests.get(direct_url, stream=True)
                                response.raise_for_status()
                                
                                # Only proceed if we got actual image data
                                if response.headers.get('content-type', '').startswith('image/'):
                                    # Determine file extension from content type
                                    content_type = response.headers.get('content-type', '')
                                    ext = '.jpg'  # default to jpg
                                    if 'png' in content_type:
                                        ext = '.png'
                                    elif 'jpeg' in content_type or 'jpg' in content_type:
                                        ext = '.jpg'
                                    
                                    # Create filename using rating_key and image type
                                    filename = f"{rating_key}_{img_type}{ext}"
                                    filepath = self.image_cache_dir / filename
                                    
                                    # Save the image
                                    with open(filepath, 'wb') as f:
                                        for chunk in response.iter_content(chunk_size=8192):
                                            if chunk:
                                                f.write(chunk)
                                    
                                    # Verify the file was written and has content
                                    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                                        return str(filepath)
                            except Exception as e:
                                print(f"Error downloading image from direct Plex URL for rating_key {rating_key}: {e}")
            
            # If all else fails, try the Tautulli proxy
            proxy_url = f"{self.base_url}/api/v2?apikey={self.api_key}&cmd=pms_image_proxy&rating_key={rating_key}&img={img_type}"
            response = requests.get(proxy_url, stream=True)
            response.raise_for_status()
            
            # Only proceed if we got actual image data
            if response.headers.get('content-type', '').startswith('image/'):
                # Determine file extension from content type
                content_type = response.headers.get('content-type', '')
                ext = '.jpg'  # default to jpg
                if 'png' in content_type:
                    ext = '.png'
                elif 'jpeg' in content_type or 'jpg' in content_type:
                    ext = '.jpg'
                
                # Create filename using rating_key and image type
                filename = f"{rating_key}_{img_type}{ext}"
                filepath = self.image_cache_dir / filename
                
                # Save the image
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Verify the file was written and has content
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    return str(filepath)
        except Exception as e:
            print(f"Error downloading image for rating_key {rating_key}: {e}")
        
        # If we get here, we failed to get the image - use a placeholder
        placeholder_path = self.image_cache_dir / f"{rating_key}_{img_type}.jpg"
        if not placeholder_path.exists() or os.path.getsize(placeholder_path) == 0:
            try:
                # Create a simple placeholder image using PIL
                # Create a new image with a dark background
                width, height = 150, 225  # Standard movie poster ratio
                img = Image.new('RGB', (width, height), color='#2C3E50')
                draw = ImageDraw.Draw(img)
                
                # Add some text
                text = "No Image"
                try:
                    # Try to load a nice font, fall back to default if not available
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
                except:
                    font = ImageFont.load_default()
                
                # Calculate text position to center it
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                x = (width - text_width) / 2
                y = (height - text_height) / 2
                
                # Draw the text in white
                draw.text((x, y), text, fill='#FFFFFF', font=font)
                
                # Save the image
                img.save(placeholder_path, 'JPEG', quality=85)
                return str(placeholder_path)
            except Exception as e:
                print(f"Error creating placeholder image: {e}")
                return None
        elif os.path.getsize(placeholder_path) > 0:
            return str(placeholder_path)
        
        return None

    def _process_image_path(self, path, rating_key=None):
        """Convert image paths to local cached versions"""
        if not path or not isinstance(path, str):
            return None
            
        if path.startswith('/'):
            # Extract image type
            img_type = 'thumb'
            if 'art' in path:
                img_type = 'art'
            elif 'banner' in path:
                img_type = 'banner'
            
            # If no rating_key provided, try to extract it from the path
            if not rating_key and '/metadata/' in path:
                try:
                    rating_key = path.split('/metadata/')[1].split('/')[0]
                except:
                    pass
            
            if not rating_key:
                print(f"Warning: Could not determine rating_key for path: {path}")
                return None
            
            # Check if image is already cached
            for ext in ['.jpg', '.png']:
                cached_path = self.image_cache_dir / f"{rating_key}_{img_type}{ext}"
                if cached_path.exists():
                    return str(cached_path)
            
            # Build API URL for image
            url = f"{self.base_url}/api/v2?apikey={self.api_key}&cmd=pms_image_proxy&rating_key={rating_key}&img={img_type}"
            return self._download_image(url, rating_key, img_type)
        
        return path

    def _process_media_item(self, item):
        """Process a media item to ensure all images are cached locally"""
        if not isinstance(item, dict):
            return item
        
        rating_key = item.get('rating_key')
        if not rating_key:
            return item
        
        # List of fields that might contain image paths
        image_fields = [
            ('thumb', 'thumb'),
            ('art', 'art'),
            ('banner', 'banner'),
            ('parent_thumb', 'parent_thumb'),
            ('grandparent_thumb', 'grandparent_thumb')
        ]
        
        for field, img_type in image_fields:
            if field in item and item[field]:
                item[field] = self._process_image_path(item[field], rating_key)
        
        return item

    def get_recently_added(self, count=5):
        """Get recently added media"""
        # First try to get from API
        result = self._make_request("get_recently_added", count=count)
        if result and "response" in result:
            items = result["response"].get("data", {}).get("recently_added", [])
            # Process items and store in database
            processed_items = [self._process_media_item(item) for item in items]
            for item in processed_items:
                self.db.store_media_item(item)
            return processed_items
        
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
                    
                    # Process image paths
                    thumb = self._process_image_path(
                        item.get('grandparent_thumb', item.get('thumb', ''))
                    )
                    
                    trending_items.append({
                        'title': title,
                        'year': item.get('year'),
                        'thumb': thumb,
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
                    thumb = self._process_image_path(item.get("grandparent_thumb", ""))
                else:
                    key = f"movie_{item.get('rating_key')}"
                    title = item.get("title", "Unknown Movie")
                    thumb = self._process_image_path(item.get("thumb", ""))
                
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

    def get_play_history(self, days=None, start_date=None, end_date=None):
        """
        Get detailed play history for visualization.
        
        Args:
            days (int, optional): Number of days of history to fetch
            start_date (str, optional): Start date in YYYY-MM-DD format
            end_date (str, optional): End date in YYYY-MM-DD format
            
        Returns:
            list: List of play history entries
        """
        params = {
            "length": 10000  # Get a large number of records
        }
        
        if days:
            params["days"] = days
        elif start_date and end_date:
            params["start_date"] = start_date
            params["end_date"] = end_date
        
        response = self._make_request("get_history", **params)
        if response and "response" in response:
            return response["response"].get("data", {}).get("data", [])
        return []

    def get_user_stats_by_media(self, days=30):
        """
        Get user statistics broken down by media type.
        
        Args:
            days (int): Number of days to analyze
            
        Returns:
            list: List of user activity records
        """
        # Get all users first
        users_response = self._make_request("get_users")
        if not users_response or "response" not in users_response:
            return []
        
        user_stats = []
        for user in users_response["response"]["data"]:
            # Get detailed history for each user
            history = self._make_request("get_history", user_id=user["user_id"], days=days, length=1000)
            if history and "response" in history and "data" in history["response"]:
                history_data = history["response"]["data"]
                if isinstance(history_data, dict) and "data" in history_data:
                    history_items = history_data["data"]
                elif isinstance(history_data, list):
                    history_items = history_data
                else:
                    continue
                
                # Group by media type
                media_types = {}
                for item in history_items:
                    if not isinstance(item, dict):
                        continue
                    
                    media_type = item.get("media_type", "unknown")
                    duration = int(item.get("duration", 0) or 0) // 60  # Convert to minutes
                    
                    if media_type not in media_types:
                        media_types[media_type] = {
                            "plays": 0,
                            "duration": 0
                        }
                    media_types[media_type]["plays"] += 1
                    media_types[media_type]["duration"] += duration
                
                # Add records for each media type that has activity
                for media_type, stats in media_types.items():
                    if stats["plays"] > 0:  # Only include media types with activity
                        user_stats.append({
                            "friendly_name": user["friendly_name"],
                            "media_type": media_type,
                            "total_plays": stats["plays"],
                            "duration": stats["duration"]
                        })
        
        return user_stats

    def full_library_sync(self):
        """Perform a full sync of all libraries from Tautulli."""
        print("Starting full library sync. This may take a while...")
        try:
            # Clear the database for a truly fresh start
            self.db.clear_all_data()

            sections_result = self._make_request("get_libraries")
            if not sections_result or "response" not in sections_result:
                print("Error: Could not fetch library sections.")
                return False
            
            libraries = sections_result["response"]["data"]
            print(f"Found {len(libraries)} libraries to sync.")

            self.db.begin_transaction()
            
            for lib in libraries:
                section_id = lib['section_id']
                section_name = lib['section_name']
                section_type = lib['section_type']
                
                print(f"--- Syncing '{section_name}' (Type: {section_type}) ---")

                if section_type == 'movie':
                    self._sync_movie_library(section_id)
                elif section_type == 'show':
                    self._sync_show_library(section_id)
                elif section_type == 'artist':
                    self._sync_music_library(section_id)
                else:
                    print(f"Skipping unsupported library type: {section_type}")

            self.db.commit_transaction()
            print("\nFull library sync completed.")
            return True

        except Exception as e:
            print(f"\nAn error occurred during full library sync: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback_transaction()
            return False

    def _sync_movie_library(self, section_id):
        """Sync all movies from a specific library section."""
        offset = 0
        total_synced = 0
        while True:
            media_result = self._make_request("get_library_media_info", section_id=section_id, start=offset, length=200)
            if not (data := media_result.get("response", {}).get("data", {})) or not (media_list := data.get("data", [])):
                break

            for item in media_list:
                if item.get('media_type') == 'movie':
                    self.db.store_media_item(item)
                    total_synced += 1
            
            print(f"  Synced {total_synced} movies...", end='\r')

            if len(media_list) < 200:
                break
            offset += 200
        print(f"  Finished syncing {total_synced} movies.")

    def _sync_show_library(self, section_id):
        """Sync all shows and their seasons from a TV library."""
        shows_result = self._make_request("get_library_media_info", section_id=section_id, length=10000)
        if not (all_items := shows_result.get("response", {}).get("data", {}).get("data", [])):
            print("  No items found in this library.")
            return
        
        shows = [item for item in all_items if item.get('media_type') == 'show']
        print(f"  Found {len(shows)} shows. Now fetching seasons...")
        total_seasons = 0

        for i, show in enumerate(shows):
            self.db.store_media_item(show)

            # 2. Get seasons for the show
            seasons_result = self._make_request("get_children_metadata", rating_key=show['rating_key'])
            if not (seasons := seasons_result.get("response", {}).get("data", {}).get("children_list", [])):
                continue

            for season in seasons:
                season['media_type'] = 'season' # API response doesn't include this

                # 3. Get episodes to find the season's true 'added_at' date
                episodes_result = self._make_request("get_children_metadata", rating_key=season['rating_key'])
                episodes = episodes_result.get('response', {}).get('data', {}).get('children_list', [])
                
                earliest_added_at = min(
                    (int(ep.get('added_at')) for ep in episodes if ep.get('added_at')),
                    default=None
                )
                
                if earliest_added_at:
                    season['added_at'] = earliest_added_at
                
                self.db.store_media_item(season)
                total_seasons += 1
            
            print(f"  Processed {i+1}/{len(shows)} shows, found {total_seasons} seasons so far...", end='\r')
        
        print(f"\n  Finished syncing {total_seasons} seasons from {len(shows)} shows.")

    def _sync_music_library(self, section_id):
        """Sync all albums from a music library."""
        artists_result = self._make_request("get_library_media_info", section_id=section_id, length=20000)
        if not (all_artists := artists_result.get("response", {}).get("data", {}).get("data", [])):
            print("  No artists found in this library.")
            return
        
        artists = [item for item in all_artists if item.get('media_type') == 'artist']
        print(f"  Found {len(artists)} artists. Now fetching albums...")
        total_albums = 0
        
        for i, artist in enumerate(artists):
            # 2. Get albums for the artist
            albums_result = self._make_request("get_children_metadata", rating_key=artist['rating_key'])
            if not (albums := albums_result.get('response', {}).get('data', {}).get('children_list', [])):
                continue
            
            for album in albums:
                if album.get('media_type') != 'album':
                    continue

                # 3. Get tracks to find the album's true 'added_at' date
                tracks_result = self._make_request("get_children_metadata", rating_key=album['rating_key'])
                tracks = tracks_result.get('response', {}).get('data', {}).get('children_list', [])
                
                earliest_added_at = min(
                    (int(tr.get('added_at')) for tr in tracks if tr.get('added_at')),
                    default=None
                )
                
                if earliest_added_at:
                    album['added_at'] = earliest_added_at
                    
                self.db.store_media_item(album)
                total_albums += 1

            print(f"  Processed {i+1}/{len(artists)} artists, found {total_albums} albums so far...", end='\r')
            
        print(f"\n  Finished syncing {total_albums} albums from {len(artists)} artists.") 