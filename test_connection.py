from src.tautulli_api import TautulliAPI

def main():
    try:
        # Initialize the API
        api = TautulliAPI()
        
        # Test connection
        print("Testing connection to Tautulli...")
        if api.test_connection():
            print("✅ Successfully connected to Tautulli!")
            
            # Try to get recently added items
            print("\nFetching recently added items...")
            recent_items = api.get_recently_added(count=3)
            
            if recent_items:
                print("\nRecently added items:")
                for item in recent_items:
                    print(f"- {item.get('title')} ({item.get('year', 'N/A')})")
            else:
                print("No recently added items found.")
        else:
            print("❌ Failed to connect to Tautulli. Please check your configuration.")
            
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    main() 