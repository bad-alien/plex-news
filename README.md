# Plex Newsletter Generator

Automatically generate and send personalized newsletters to your Plex users featuring recently added content, trending media, and community insights.

## Features

- 📺 Recently added movies and TV shows
- 🔥 Trending content based on play count
- 👥 Community favorites (most watched by unique users)
- 📊 User activity statistics
- 📧 Beautiful, responsive email design

## Prerequisites

- Python 3.x
- Plex Media Server
- Tautulli installed and configured
- Gmail account (for sending newsletters)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/plex-news.git
   cd plex-news
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your configuration:
   ```
   TAUTULLI_URL=http://your-tautulli-ip:8181
   TAUTULLI_API_KEY=your_api_key_here
   ```

## Usage

Generate a newsletter preview:
```bash
python generate_newsletter.py
```

This will create a `newsletter_preview.html` file that you can open in your browser.

## Project Structure

```
plex-news/
├── src/
│   ├── __init__.py
│   └── tautulli_api.py    # Tautulli API interaction
├── templates/
│   └── newsletter.html    # Newsletter template
├── .env                   # Configuration (not in repo)
├── .gitignore
├── README.md
├── requirements.txt
└── generate_newsletter.py # Main script
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 