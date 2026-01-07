import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict
from .database import Database

# Load environment variables
load_dotenv(override=True)

class TautulliAPI:
    def __init__(self):
        self.base_url = os.getenv("TAUTULLI_URL", "").rstrip('/')
        self.api_key = os.getenv("TAUTULLI_API_KEY", "")
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

    def _sync_library_recursive(self, section_id, section_name, rating_key=None, level=0, grandparent_rating_key=None):
        """Recursively sync library items (for TV shows: show -> season -> episode)"""
        items_synced = 0

        offset = 0
        while True:
            params = {
                "section_id": section_id,
                "length": 1000,
                "start": offset,
                "refresh": "true"  # Force fresh data from Plex, not Tautulli cache
            }

            if rating_key:
                params["rating_key"] = rating_key

            result = self._make_request("get_library_media_info", **params)

            if not result or "response" not in result:
                break

            data = result["response"].get("data", {})
            items = data.get("data", [])
            total_records = data.get("recordsTotal", 0)

            if not items:
                break

            for item in items:
                media_type = item.get('media_type')
                item_rating_key = item.get('rating_key')

                # Store this item
                normalized_item = {
                    'rating_key': item_rating_key,
                    'title': item.get('title'),
                    'year': item.get('year'),
                    'media_type': media_type,
                    'thumb': item.get('thumb'),
                    'duration': item.get('duration'),
                    'file_size': item.get('file_size'),
                    'added_at': item.get('added_at'),
                    'grandparent_rating_key': grandparent_rating_key,
                }
                self.db.store_media_item(normalized_item)
                items_synced += 1

                # Recursively fetch children for shows and seasons
                if media_type == 'show':
                    # For shows, pass the show's rating_key as grandparent for episodes
                    child_count = self._sync_library_recursive(
                        section_id, section_name, item_rating_key, level + 1,
                        grandparent_rating_key=item_rating_key
                    )
                    items_synced += child_count
                elif media_type == 'season':
                    # For seasons, pass through the grandparent (show) rating_key
                    child_count = self._sync_library_recursive(
                        section_id, section_name, item_rating_key, level + 1,
                        grandparent_rating_key=grandparent_rating_key
                    )
                    items_synced += child_count

            offset += len(items)

            if offset >= total_records:
                break

        return items_synced

    def _sync_music_library_recursive(self, section_id, section_name, rating_key=None, level=0, grandparent_rating_key=None, parent_rating_key=None):
        """Recursively sync music library items (artist -> album -> track)"""
        items_synced = 0

        offset = 0
        while True:
            params = {
                "section_id": section_id,
                "length": 1000,
                "start": offset,
                "refresh": "true"
            }

            if rating_key:
                params["rating_key"] = rating_key

            result = self._make_request("get_library_media_info", **params)

            if not result or "response" not in result:
                break

            data = result["response"].get("data", {})
            items = data.get("data", [])
            total_records = data.get("recordsTotal", 0)

            if not items:
                break

            for item in items:
                media_type = item.get('media_type')
                item_rating_key = item.get('rating_key')

                # Store this item
                normalized_item = {
                    'rating_key': item_rating_key,
                    'title': item.get('title'),
                    'year': item.get('year'),
                    'media_type': media_type,
                    'thumb': item.get('thumb'),
                    'duration': item.get('duration'),
                    'file_size': item.get('file_size'),
                    'added_at': item.get('added_at'),
                    'grandparent_rating_key': grandparent_rating_key,
                    'parent_rating_key': parent_rating_key,
                }
                self.db.store_media_item(normalized_item)
                items_synced += 1

                # Recursively fetch children for artists (albums) and albums (tracks)
                if media_type == 'artist':
                    # For artists, get albums (pass artist's rating_key as grandparent for tracks)
                    child_count = self._sync_music_library_recursive(
                        section_id, section_name, item_rating_key, level + 1,
                        grandparent_rating_key=item_rating_key,
                        parent_rating_key=None  # Albums don't have a parent_rating_key
                    )
                    items_synced += child_count
                elif media_type == 'album':
                    # For albums, get tracks (pass album's rating_key as parent for tracks)
                    child_count = self._sync_music_library_recursive(
                        section_id, section_name, item_rating_key, level + 1,
                        grandparent_rating_key=grandparent_rating_key,
                        parent_rating_key=item_rating_key  # Pass album as parent for tracks
                    )
                    items_synced += child_count

            offset += len(items)

            if offset >= total_records:
                break

        return items_synced

    def _collect_all_rating_keys(self, libraries):
        """Collect all current rating_keys from Plex libraries for stale data cleanup."""
        all_keys = set()

        for library in libraries:
            section_id = library.get("section_id")
            section_type = library.get("section_type")

            # Get all top-level items from this library
            offset = 0
            while True:
                result = self._make_request(
                    "get_library_media_info",
                    section_id=section_id,
                    length=1000,
                    start=offset,
                    refresh="true"
                )

                if not result or "response" not in result:
                    break

                data = result["response"].get("data", {})
                items = data.get("data", [])

                if not items:
                    break

                for item in items:
                    all_keys.add(item.get('rating_key'))

                offset += len(items)
                if offset >= data.get("recordsTotal", 0):
                    break

            # For TV shows, also collect season and episode keys
            if section_type == 'show':
                # Get children recursively
                for item in items:
                    if item.get('media_type') == 'show':
                        self._collect_children_keys(item.get('rating_key'), all_keys)
            # For Music, also collect album and track keys
            elif section_type == 'artist':
                for item in items:
                    if item.get('media_type') == 'artist':
                        self._collect_music_children_keys(section_id, item.get('rating_key'), all_keys)

        return all_keys

    def _collect_music_children_keys(self, section_id, rating_key, keys_set):
        """Collect rating_keys for albums and tracks under an artist."""
        # Get albums for this artist
        result = self._make_request("get_library_media_info", section_id=section_id, rating_key=rating_key, length=1000)
        if result and "response" in result:
            albums = result["response"].get("data", {}).get("data", [])
            for album in albums:
                album_key = album.get('rating_key')
                if album_key:
                    keys_set.add(album_key)
                    # Get tracks for this album
                    tracks_result = self._make_request("get_library_media_info", section_id=section_id, rating_key=album_key, length=1000)
                    if tracks_result and "response" in tracks_result:
                        tracks = tracks_result["response"].get("data", {}).get("data", [])
                        for track in tracks:
                            track_key = track.get('rating_key')
                            if track_key:
                                keys_set.add(track_key)

    def _collect_children_keys(self, rating_key, keys_set):
        """Recursively collect rating_keys for all children of an item."""
        result = self._make_request("get_children_metadata", rating_key=rating_key)
        if result and "response" in result:
            children = result["response"].get("data", {}).get("children_list", [])
            for child in children:
                child_key = child.get('rating_key')
                if child_key:
                    keys_set.add(child_key)
                    # Recurse for seasons to get episodes
                    if child.get('media_type') == 'season':
                        self._collect_children_keys(child_key, keys_set)

    def sync_full_library(self, cleanup_stale=True):
        """Sync all media items from all libraries with file sizes.

        Args:
            cleanup_stale: If True, remove items from DB that no longer exist in Plex
        """
        try:
            # Get all libraries first (needed for both cleanup and sync)
            result = self._make_request("get_libraries")
            if not result or "response" not in result:
                print("Could not fetch libraries")
                return False

            libraries = result["response"].get("data", [])
            print(f"\nFound {len(libraries)} libraries to sync")

            # Cleanup stale data before syncing
            if cleanup_stale:
                print("\n" + "=" * 60)
                print("COLLECTING CURRENT LIBRARY DATA FOR CLEANUP")
                print("=" * 60)
                valid_keys = self._collect_all_rating_keys(libraries)
                print(f"Found {len(valid_keys)} valid rating_keys in Plex")
                self.db.remove_stale_media_items(valid_keys)

            self.db.begin_transaction()

            total_synced = 0

            for library in libraries:
                section_id = library.get("section_id")
                section_name = library.get("section_name")
                section_type = library.get("section_type")

                print(f"\nSyncing library: {section_name} ({section_type})")

                # For TV libraries, use recursive sync to get episodes
                if section_type == 'show':
                    library_total = self._sync_library_recursive(section_id, section_name)
                    print(f"✓ Completed {section_name}: {library_total} items (shows, seasons, episodes)")
                    total_synced += library_total
                # For Music libraries, use recursive sync to get albums and tracks
                elif section_type == 'artist':
                    library_total = self._sync_music_library_recursive(section_id, section_name)
                    print(f"✓ Completed {section_name}: {library_total} items (artists, albums, tracks)")
                    total_synced += library_total
                else:
                    # For other libraries (movies, music), use regular pagination
                    offset = 0
                    library_total = 0

                    while True:
                        result = self._make_request(
                            "get_library_media_info",
                            section_id=section_id,
                            length=1000,
                            start=offset,
                            refresh="true"  # Force fresh data from Plex
                        )

                        if not result or "response" not in result:
                            break

                        data = result["response"].get("data", {})
                        items = data.get("data", [])
                        total_records = data.get("recordsTotal", 0)

                        if not items:
                            break

                        # Store each item
                        for item in items:
                            normalized_item = {
                                'rating_key': item.get('rating_key'),
                                'title': item.get('title'),
                                'year': item.get('year'),
                                'media_type': item.get('media_type'),
                                'thumb': item.get('thumb'),
                                'duration': item.get('duration'),
                                'file_size': item.get('file_size'),
                                'added_at': item.get('added_at'),
                            }
                            self.db.store_media_item(normalized_item)

                        library_total += len(items)
                        total_synced += len(items)
                        offset += len(items)

                        print(f"  Synced {library_total}/{total_records} items from {section_name}...")

                        if offset >= total_records:
                            break

                    print(f"✓ Completed {section_name}: {library_total} items")

            self.db.commit_transaction()
            print(f"\n✓ Full library sync completed: {total_synced} total items synced")
            return True

        except Exception as e:
            print(f"Error during full library sync: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback_transaction()
            return False

    def sync_data(self, fetch_file_sizes=True, full_sync=False):
        """Sync data from Tautulli to local database"""

        # If full sync requested, sync entire library first
        if full_sync:
            print("=" * 60)
            print("FULL LIBRARY SYNC")
            print("=" * 60)
            if not self.sync_full_library():
                return False

        last_sync = self.db.get_last_sync_time()

        try:
            self.db.begin_transaction()

            print("\n" + "=" * 60)
            print("SYNCING PLAY HISTORY")
            print("=" * 60)

            # Get history with pagination (full history if full_sync, incremental otherwise)
            offset = 0
            total_history_synced = 0

            while True:
                params = {
                    "length": 1000,
                    "start": offset
                }

                # Only use start_date for incremental syncs
                if not full_sync and last_sync['history'] > 0:
                    params["start_date"] = last_sync['history']

                result = self._make_request("get_history", **params)

                if not result or "response" not in result:
                    break

                data = result["response"].get("data", {})
                history = data.get("data", [])
                total_records = data.get("recordsTotal", 0)

                if not history:
                    break

                # Store each history item
                for item in history:
                    self.db.store_play_history(item)
                    # Also store the media item if it doesn't exist
                    self.db.store_media_item(item)

                total_history_synced += len(history)
                offset += len(history)

                print(f"Synced {offset}/{total_records} play history records...")

                if offset >= total_records:
                    break

            self.db.commit_transaction()
            print(f"✓ Play history sync completed: {total_history_synced} records synced")
            return True

        except Exception as e:
            print(f"Error during sync: {e}")
            import traceback
            traceback.print_exc()
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

    def _get_file_size(self, rating_key):
        """Get file size for a media item from metadata"""
        try:
            result = self._make_request("get_metadata", rating_key=rating_key)
            if result and "response" in result:
                data = result["response"].get("data", {})
                media_info = data.get("media_info", [])

                # Get file size from first media item's first part
                if media_info and len(media_info) > 0:
                    parts = media_info[0].get("parts", [])
                    if parts and len(parts) > 0:
                        file_size = parts[0].get("file_size")
                        if file_size:
                            return int(file_size)
        except Exception as e:
            print(f"Error getting file size for rating_key {rating_key}: {e}")

        return None

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

 