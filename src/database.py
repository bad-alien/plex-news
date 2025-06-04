import sqlite3
from datetime import datetime
from pathlib import Path
import time
from contextlib import contextmanager
import os

class Database:
    def __init__(self, db_path="data/plex_stats.db"):
        # Ensure the data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._connection = None
        self.init_db()

    @contextmanager
    def get_connection(self, new_connection=False):
        """Get a database connection with row factory"""
        if new_connection or self._connection is None:
            conn = sqlite3.connect(self.db_path, timeout=60)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
        else:
            yield self._connection

    def execute_with_retry(self, cursor, query, params=()):
        """Execute a query with retry logic"""
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                return cursor.execute(query, params)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    print(f"Database is locked, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise

    def begin_transaction(self):
        """Start a new transaction"""
        if self._connection is not None:
            self._connection.close()
        self._connection = sqlite3.connect(self.db_path, timeout=60)
        self._connection.row_factory = sqlite3.Row

    def commit_transaction(self):
        """Commit the current transaction and close the connection"""
        if self._connection is not None:
            self._connection.commit()
            self._connection.close()
            self._connection = None

    def rollback_transaction(self):
        """Rollback the current transaction and close the connection"""
        if self._connection is not None:
            self._connection.rollback()
            self._connection.close()
            self._connection = None

    def init_db(self):
        """Initialize the database schema"""
        with self.get_connection(new_connection=True) as conn:
            cursor = conn.cursor()
            
            # Create tables
            self.execute_with_retry(cursor, """
                CREATE TABLE IF NOT EXISTS media_items (
                    rating_key TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    year INTEGER,
                    media_type TEXT NOT NULL,
                    thumb TEXT,
                    thumb_cached_path TEXT,
                    art TEXT,
                    art_cached_path TEXT,
                    banner TEXT,
                    banner_cached_path TEXT,
                    summary TEXT,
                    duration INTEGER,
                    added_at INTEGER,
                    updated_at INTEGER
                )
            """)
            
            self.execute_with_retry(cursor, """
                CREATE TABLE IF NOT EXISTS play_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rating_key TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    watched_at INTEGER NOT NULL,
                    duration INTEGER,
                    FOREIGN KEY (rating_key) REFERENCES media_items (rating_key)
                )
            """)
            
            self.execute_with_retry(cursor, """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    friendly_name TEXT,
                    last_seen INTEGER
                )
            """)
            
            # Add sync_status table
            self.execute_with_retry(cursor, """
                CREATE TABLE IF NOT EXISTS sync_status (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_history_sync INTEGER,
                    last_library_sync INTEGER,
                    total_items_synced INTEGER DEFAULT 0
                )
            """)
            
            # Create indexes
            self.execute_with_retry(cursor, "CREATE INDEX IF NOT EXISTS idx_history_watched_at ON play_history (watched_at)")
            self.execute_with_retry(cursor, "CREATE INDEX IF NOT EXISTS idx_history_user ON play_history (user_id)")
            self.execute_with_retry(cursor, "CREATE INDEX IF NOT EXISTS idx_media_type ON media_items (media_type)")
            
            # Initialize sync status if not exists
            self.execute_with_retry(cursor, """
                INSERT OR IGNORE INTO sync_status (id, last_history_sync, last_library_sync)
                VALUES (1, 0, 0)
            """)
            
            conn.commit()

    def get_last_sync_time(self):
        """Get the timestamp of the last successful sync"""
        with self.get_connection(new_connection=True) as conn:
            cursor = conn.cursor()
            self.execute_with_retry(cursor, "SELECT last_history_sync, last_library_sync FROM sync_status WHERE id = 1")
            result = cursor.fetchone()
            return {
                'history': result['last_history_sync'],
                'library': result['last_library_sync']
            }

    def update_sync_time(self, sync_type='both'):
        """Update the last sync timestamp"""
        current_time = int(datetime.now().timestamp())
        if self._connection is None:
            self.begin_transaction()
        
        cursor = self._connection.cursor()
        if sync_type == 'history' or sync_type == 'both':
            self.execute_with_retry(cursor, 
                "UPDATE sync_status SET last_history_sync = ? WHERE id = 1", 
                (current_time,)
            )
        if sync_type == 'library' or sync_type == 'both':
            self.execute_with_retry(cursor, 
                "UPDATE sync_status SET last_library_sync = ? WHERE id = 1", 
                (current_time,)
            )
        self.execute_with_retry(cursor, 
            "UPDATE sync_status SET total_items_synced = total_items_synced + 1 WHERE id = 1"
        )

    def store_media_item(self, item):
        """Store a media item in the database"""
        if self._connection is None:
            self.begin_transaction()
        
        cursor = self._connection.cursor()
        try:
            # For TV shows, we want to store both show and episode info
            if item.get('media_type') == 'episode':
                # Store the show
                show_key = f"show_{item.get('grandparent_rating_key', '')}"
                self.execute_with_retry(cursor, """
                    INSERT OR REPLACE INTO media_items (
                        rating_key, title, year, media_type, 
                        thumb, thumb_cached_path,
                        art, art_cached_path,
                        banner, banner_cached_path,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    show_key,
                    item.get('grandparent_title', 'Unknown Show'),
                    item.get('year'),
                    'show',
                    item.get('grandparent_thumb', ''),
                    item.get('grandparent_thumb_cached', ''),
                    item.get('grandparent_art', ''),
                    item.get('grandparent_art_cached', ''),
                    item.get('grandparent_banner', ''),
                    item.get('grandparent_banner_cached', ''),
                    int(datetime.now().timestamp())
                ))
                
                # Store the episode
                self.execute_with_retry(cursor, """
                    INSERT OR REPLACE INTO media_items (
                        rating_key, title, year, media_type,
                        thumb, thumb_cached_path,
                        art, art_cached_path,
                        banner, banner_cached_path,
                        duration, summary, added_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get('rating_key'),
                    item.get('title'),
                    item.get('year'),
                    'episode',
                    item.get('thumb', ''),
                    item.get('thumb_cached', ''),
                    item.get('art', ''),
                    item.get('art_cached', ''),
                    item.get('banner', ''),
                    item.get('banner_cached', ''),
                    item.get('duration', 0),
                    item.get('summary', ''),
                    int(item.get('added_at', datetime.now().timestamp())),
                    int(datetime.now().timestamp())
                ))
            else:
                # Store movie or music
                self.execute_with_retry(cursor, """
                    INSERT OR REPLACE INTO media_items (
                        rating_key, title, year, media_type,
                        thumb, thumb_cached_path,
                        art, art_cached_path,
                        banner, banner_cached_path,
                        duration, summary, added_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get('rating_key'),
                    item.get('title'),
                    item.get('year'),
                    item.get('media_type', 'movie'),
                    item.get('thumb', ''),
                    item.get('thumb_cached', ''),
                    item.get('art', ''),
                    item.get('art_cached', ''),
                    item.get('banner', ''),
                    item.get('banner_cached', ''),
                    item.get('duration', 0),
                    item.get('summary', ''),
                    int(item.get('added_at', datetime.now().timestamp())),
                    int(datetime.now().timestamp())
                ))
            
            # Update sync status
            self.update_sync_time('library')
        except Exception as e:
            print(f"Error storing media item: {e}")
            self.rollback_transaction()
            raise

    def store_play_history(self, history_item):
        """Store a play history item"""
        if self._connection is None:
            self.begin_transaction()
        
        cursor = self._connection.cursor()
        try:
            # Store or update user
            self.execute_with_retry(cursor, """
                INSERT OR REPLACE INTO users (
                    user_id, username, friendly_name, last_seen
                ) VALUES (?, ?, ?, ?)
            """, (
                history_item.get('user_id', 'unknown'),
                history_item.get('user', 'unknown'),
                history_item.get('friendly_name', ''),
                int(history_item.get('date', datetime.now().timestamp()))
            ))
            
            # Check if this history item already exists
            self.execute_with_retry(cursor, """
                SELECT id FROM play_history 
                WHERE rating_key = ? AND user_id = ? AND watched_at = ?
            """, (
                history_item.get('rating_key'),
                history_item.get('user_id', 'unknown'),
                int(history_item.get('date', datetime.now().timestamp()))
            ))
            
            if not cursor.fetchone():
                # Only insert if it's a new history item
                self.execute_with_retry(cursor, """
                    INSERT INTO play_history (
                        rating_key, user_id, watched_at, duration
                    ) VALUES (?, ?, ?, ?)
                """, (
                    history_item.get('rating_key'),
                    history_item.get('user_id', 'unknown'),
                    int(history_item.get('date', datetime.now().timestamp())),
                    history_item.get('duration', 0)
                ))
                
                # Update sync status
                self.update_sync_time('history')
        except Exception as e:
            print(f"Error storing play history: {e}")
            self.rollback_transaction()
            raise

    def _process_image_path(self, path):
        """Convert relative image paths to full URLs with authentication"""
        if not path or not isinstance(path, str):
            return None
        
        base_url = os.getenv("TAUTULLI_URL", "").rstrip('/')
        api_key = os.getenv("TAUTULLI_API_KEY", "")
        
        if path.startswith('/'):
            # Convert /library/metadata/XXX/thumb/YYY to API endpoint
            if path.startswith('/library/metadata/'):
                # Extract rating key and image type
                parts = path.split('/')
                if len(parts) >= 4:
                    rating_key = parts[3]
                    img_type = 'thumb'  # Default to thumb
                    if 'art' in path:
                        img_type = 'art'
                    elif 'banner' in path:
                        img_type = 'banner'
                    
                    # Use the pms_image_proxy endpoint
                    return f"{base_url}/api/v2?apikey={api_key}&cmd=pms_image_proxy&rating_key={rating_key}&img={img_type}"
            
            # Fallback for other paths
            return f"{base_url}{path}?apikey={api_key}"
        return path

    def get_recently_added(self, days=7, limit=5, media_types=None):
        """Get recently added items"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM media_items 
                WHERE added_at >= ?
            """
            params = [int((datetime.now().timestamp() - (days * 86400)))]
            
            if media_types:
                query += f" AND media_type IN ({','.join('?' * len(media_types))})"
                params.extend(media_types)
            
            query += " ORDER BY added_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            items = [dict(row) for row in cursor.fetchall()]
            
            # Process image paths
            for item in items:
                for field in ['thumb', 'parent_thumb', 'grandparent_thumb', 'art', 'banner']:
                    if item.get(field):
                        item[field] = self._process_image_path(item[field])
            
            return items

    def get_most_watched(self, days=7, limit=5, media_types=None):
        """Get most watched content"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    m.*, 
                    COUNT(DISTINCT p.user_id) as unique_viewers,
                    COUNT(*) as play_count
                FROM media_items m
                JOIN play_history p ON m.rating_key = p.rating_key
                WHERE p.watched_at >= ?
            """
            params = [int((datetime.now().timestamp() - (days * 86400)))]
            
            if media_types:
                query += f" AND m.media_type IN ({','.join('?' * len(media_types))})"
                params.extend(media_types)
            
            query += """
                GROUP BY m.rating_key
                HAVING unique_viewers > 1
                ORDER BY unique_viewers DESC, play_count DESC
                LIMIT ?
            """
            params.append(limit)
            
            cursor.execute(query, params)
            items = [dict(row) for row in cursor.fetchall()]
            
            # Process image paths
            for item in items:
                for field in ['thumb', 'parent_thumb', 'grandparent_thumb', 'art', 'banner']:
                    if item.get(field):
                        item[field] = self._process_image_path(item[field])
            
            return items

    def get_user_stats(self, days=7):
        """Get user statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get overall stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_plays,
                    COUNT(DISTINCT user_id) as active_users,
                    SUM(duration) as total_duration
                FROM play_history
                WHERE watched_at >= ?
            """, [int((datetime.now().timestamp() - (days * 86400)))])
            
            overall_stats = dict(cursor.fetchone())
            
            # Get per-user stats
            cursor.execute("""
                SELECT 
                    u.friendly_name,
                    COUNT(*) as plays,
                    SUM(p.duration) as duration
                FROM play_history p
                JOIN users u ON p.user_id = u.user_id
                WHERE p.watched_at >= ?
                GROUP BY p.user_id
                ORDER BY plays DESC
            """, [int((datetime.now().timestamp() - (days * 86400)))])
            
            user_stats = [dict(row) for row in cursor.fetchall()]
            
            return {
                "total_plays": overall_stats["total_plays"],
                "total_duration": overall_stats["total_duration"] // 60,  # Convert to minutes
                "active_users": overall_stats["active_users"],
                "user_stats": user_stats
            } 