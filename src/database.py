import sqlite3
from datetime import datetime
from pathlib import Path

class Database:
    def __init__(self, db_path="data/plex_stats.db"):
        # Ensure the data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Get a database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize the database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media_items (
                    rating_key TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    year INTEGER,
                    media_type TEXT NOT NULL,
                    thumb TEXT,
                    summary TEXT,
                    duration INTEGER,
                    added_at INTEGER,
                    updated_at INTEGER
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS play_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rating_key TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    watched_at INTEGER NOT NULL,
                    duration INTEGER,
                    FOREIGN KEY (rating_key) REFERENCES media_items (rating_key)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    friendly_name TEXT,
                    last_seen INTEGER
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_watched_at ON play_history (watched_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON play_history (user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_type ON media_items (media_type)")
            
            conn.commit()

    def store_media_item(self, item):
        """Store a media item in the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # For TV shows, we want to store both show and episode info
            if item.get('media_type') == 'episode':
                # Store the show
                show_key = f"show_{item.get('grandparent_rating_key', '')}"
                cursor.execute("""
                    INSERT OR REPLACE INTO media_items (
                        rating_key, title, year, media_type, thumb, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    show_key,
                    item.get('grandparent_title', 'Unknown Show'),
                    item.get('year'),
                    'show',
                    item.get('grandparent_thumb', ''),
                    int(datetime.now().timestamp())
                ))
                
                # Store the episode
                cursor.execute("""
                    INSERT OR REPLACE INTO media_items (
                        rating_key, title, year, media_type, thumb, duration, 
                        summary, added_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get('rating_key'),
                    item.get('title'),
                    item.get('year'),
                    'episode',
                    item.get('thumb', ''),
                    item.get('duration', 0),
                    item.get('summary', ''),
                    int(item.get('added_at', datetime.now().timestamp())),
                    int(datetime.now().timestamp())
                ))
            else:
                # Store movie or music
                cursor.execute("""
                    INSERT OR REPLACE INTO media_items (
                        rating_key, title, year, media_type, thumb, duration,
                        summary, added_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get('rating_key'),
                    item.get('title'),
                    item.get('year'),
                    item.get('media_type', 'movie'),
                    item.get('thumb', ''),
                    item.get('duration', 0),
                    item.get('summary', ''),
                    int(item.get('added_at', datetime.now().timestamp())),
                    int(datetime.now().timestamp())
                ))

    def store_play_history(self, history_item):
        """Store a play history item"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Store or update user
            cursor.execute("""
                INSERT OR REPLACE INTO users (
                    user_id, username, friendly_name, last_seen
                ) VALUES (?, ?, ?, ?)
            """, (
                history_item.get('user_id', 'unknown'),
                history_item.get('user', 'unknown'),
                history_item.get('friendly_name', ''),
                int(history_item.get('date', datetime.now().timestamp()))
            ))
            
            # Store play history
            cursor.execute("""
                INSERT INTO play_history (
                    rating_key, user_id, watched_at, duration
                ) VALUES (?, ?, ?, ?)
            """, (
                history_item.get('rating_key'),
                history_item.get('user_id', 'unknown'),
                int(history_item.get('date', datetime.now().timestamp())),
                history_item.get('duration', 0)
            ))

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
            return [dict(row) for row in cursor.fetchall()]

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
            return [dict(row) for row in cursor.fetchall()]

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