import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

TAUTULLI_URL = os.getenv("TAUTULLI_URL", "").rstrip('/')
TAUTULLI_API_KEY = os.getenv("TAUTULLI_API_KEY", "")

def _make_request(cmd, **params):
    """Make a request to the Tautulli API and return the raw response."""
    if not TAUTULLI_URL or not TAUTULLI_API_KEY:
        print("Error: TAUTULLI_URL and TAUTULLI_API_KEY must be set in .env file")
        return None
    
    url = f"{TAUTULLI_URL}/api/v2"
    params = {
        "apikey": TAUTULLI_API_KEY,
        "cmd": cmd,
        **params
    }
    
    try:
        print(f"\n--- Making API request ---")
        print(f"URL: {url}")
        print(f"Params: {params}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        print(f"Status Code: {response.status_code}")
        print("--------------------------\n")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request to Tautulli API: {e}")
        if 'response' in locals():
            print(f"Response content: {response.text}")
        return None

def print_json(data):
    """Prints formatted JSON."""
    if data:
        print(json.dumps(data, indent=4))
    else:
        print("No data returned from API.")

def list_libraries():
    """Fetches and prints all configured libraries."""
    print(">>> Fetching all libraries...")
    data = _make_request("get_libraries")
    print_json(data)

def get_library_content(section_id, start=0, length=5):
    """Fetches and prints a snippet of content from a specific library."""
    print(f">>> Fetching content for Library ID: {section_id} (start={start}, length={length})")
    data = _make_request("get_library_media_info", section_id=section_id, start=start, length=length)
    print_json(data)

def get_children(rating_key):
    """Fetches and prints the children of a specific media item."""
    print(f">>> Fetching children for Rating Key: {rating_key}")
    data = _make_request("get_children_metadata", rating_key=rating_key)
    print_json(data)

def main():
    """Main function to guide the user through API debugging."""
    print("--- Tautulli API Debugger ---")
    print("This script helps inspect the raw data from your Tautulli API.")
    
    while True:
        print("\nWhat would you like to do?")
        print("1. List all libraries (to find Section IDs)")
        print("2. Get content for a specific library (e.g., see your movies)")
        print("3. Get children metadata for a specific item (e.g., seasons of a show)")
        print("4. Exit")
        
        choice = input("Enter your choice (1-4): ")
        
        if choice == '1':
            list_libraries()
        elif choice == '2':
            section_id = input("Enter the Section ID for the library: ")
            get_library_content(section_id)
        elif choice == '3':
            rating_key = input("Enter the Rating Key for the parent item (e.g., a TV Show): ")
            get_children(rating_key)
        elif choice == '4':
            break
        else:
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    main() 