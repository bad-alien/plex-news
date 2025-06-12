import sqlite3
from pathlib import Path

def verify_library_counts():
    """
    Connects to the database and prints the total counts for
    movies, seasons, shows, and albums.
    """
    db_path = Path("data/plex_stats.db")

    if not db_path.exists():
        print("Error: Database file not found at data/plex_stats.db")
        print("Please run the --force-full-sync first.")
        return

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            print("--- Verifying Library Counts in Database ---")

            # Count Movies
            cursor.execute("SELECT COUNT(*) FROM media_items WHERE media_type = 'movie'")
            movie_count = cursor.fetchone()[0]
            print(f"Total Movies: {movie_count}")

            # Count TV Seasons
            cursor.execute("SELECT COUNT(*) FROM media_items WHERE media_type = 'season'")
            season_count = cursor.fetchone()[0]
            print(f"Total TV Seasons: {season_count}")

            # Count TV Shows
            cursor.execute("SELECT COUNT(*) FROM media_items WHERE media_type = 'show'")
            show_count = cursor.fetchone()[0]
            print(f"Total TV Shows: {show_count} (Note: The chart plots growth by Season)")

            # Count Music Albums
            cursor.execute("SELECT COUNT(*) FROM media_items WHERE media_type = 'album'")
            album_count = cursor.fetchone()[0]
            print(f"Total Music Albums: {album_count}")
            
            print("--------------------------------------------")

    except sqlite3.Error as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    verify_library_counts() 