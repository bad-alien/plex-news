## Project Plan: Plex User Newsletter Automation on Unraid

**Project Vision:** To create an automated system that generates and emails a periodic newsletter to Plex users. The newsletter will feature personalized and server-wide insights, including recently added media, user activity trends, and community highlights, fostering engagement within your Plex community.

**Target User:** A junior developer eager to learn and implement a full-stack mini-project involving data handling, automation, and modern development practices.

**Core Goals:**

1. **Automated Data Collection:** Periodically fetch data from Tautulli regarding Plex server activity.
2. **Insightful Content Generation:** Process raw data to extract meaningful insights:
    - Recently added media.
    - Commonly watched/listened to media among different users.
    - Shoutouts for most active and (optionally, handled sensitively) least active users.
3. **Dynamic Newsletter Creation:** Generate an engaging HTML newsletter using templates.
4. **Automated Email Distribution:** Send the newsletter to Plex users.
5. **Unraid Deployment:** Host and schedule the entire process on an Unraid server.
6. **Modern & Impressive Stack:** Utilize the specified technologies to build a robust and well-engineered solution.

---

### 1. Prerequisites

- **Unraid Server:** Operational with Docker and User Scripts plugin installed.
- **Plex Media Server:** Running, preferably in a Docker container on Unraid.
- **Tautulli:** Installed (ideally as a Docker container on Unraid) and configured to monitor your Plex server. You'll need its API key.
- **Basic Python Knowledge:** Understanding of Python syntax, data structures, functions, and package management (pip).
- **Command Line Familiarity:** Comfortable working in a terminal for Git commands, Docker operations, and script execution.
- **Git & GitHub Account:** For version control and code hosting.
- **Email Account for Sending:** A Gmail account is specified. Be aware of sending limits and security implications (consider creating an App Password).
- **(Optional but Recommended) Code Editor:** VS Code with Python extension, or similar.

---

### 2. Tooling & Technology Choices (Rationale)

You've selected an excellent, modern stack. Here's why these choices are great and will impress:

- **Data Extraction & Analysis:**
    - **Tautulli API:** The canonical source for Plex metadata and user statistics. Direct API interaction is efficient.
    - **Python:** The glue for the entire project. Its extensive libraries for web requests (`requests`), data manipulation (`pandas` - highly recommended to add for analysis), and general scripting make it ideal.
- **Database:**
    - **SQLite:** Lightweight, serverless, file-based. Perfect for this scale. It simplifies setup (no separate database server needed initially) and integrates seamlessly with Python. Using a schema similar to Plex's own (if known and relevant) is a thoughtful touch for data consistency.
- **Newsletter Creation & Styling:**
    - **HTML & CSS:** The fundamental building blocks for email content.
    - **Beautiful Soup:** Useful if you need to parse or clean up HTML fragments, though Jinja2 will handle most of the generation.
    - **Jinja2:** A powerful templating engine. It allows you to separate presentation (HTML structure) from logic (Python data), which is crucial for maintainable and dynamic content generation. This is a very professional approach.
    - **Bootstrap or Tailwind CSS:**
        - **Bootstrap:** Component-rich, easier for quick, good-looking layouts. Good for rapid development.
        - **Tailwind CSS:** Utility-first, offering more granular control and potentially smaller final CSS. Steeper learning curve but highly regarded for custom designs.
        - **Recommendation for Email:** Email clients have notoriously tricky CSS support. Often, inline CSS is required. Tools exist to "inline" your CSS before sending. For simplicity, start with basic CSS or a battle-tested email framework/template that handles responsiveness. Bootstrap might be easier to adapt for email if you use its pre-built components cautiously.
- **Image/Content Generation (AI Tools - _Exploratory & Advanced_):**
    - **Midjourney/DALL-E 2:** For generating unique images (e.g., a header banner, or even abstract art related to a movie). This is an advanced feature that adds a "wow" factor. Integration would involve using their APIs.
    - **Jasper/Copy.ai:** For generating text snippets (e.g., witty intros, summaries). Also API-based.
    - **Note:** These are ambitious for a junior dev's first pass. Suggest focusing on the core data-driven content first, then exploring these as enhancements.
- **Data Visualization:**
    - **Matplotlib/Seaborn (for static graphs):** Excellent for creating simple charts (bar charts for active users, line charts for library growth) that can be saved as images and embedded in the email.
    - **Plotly/Bokeh (for interactive/animated graphs, exporting as GIFs):** Can create more engaging visuals. Exporting to GIF is key for email compatibility, as interactive JS won't work in most email clients. This is a definite "impressive" feature.
    - **NetworkX (for network graphs):** Visualizing connections between users and common media (e.g., "Users A, B, and C all watched Movie X") can be incredibly cool and insightful. Export as an image.
- **Email Sending:**
    - **Python `smtplib`:** Standard library for sending emails. Works well for basic needs.
    - **Security Note for Gmail:** Emphasize using an **App Password** instead of the main account password. Mention Gmail's sending limits for free accounts. For more robust sending, a transactional email service (e.g., SendGrid, Mailgun - often have free tiers) would be a next step.
- **Scheduling & Orchestration:**
    - **Cron (via Unraid User Scripts):** Simple, effective, and readily available on Unraid for scheduling recurring tasks. Ideal for a single, well-defined script.
    - **Apache Airflow:** Extremely powerful for defining, scheduling, and monitoring complex workflows (DAGs - Directed Acyclic Graphs). While listed, it's likely overkill for this initial project for a junior developer. The complexity of setting up and managing Airflow (even in Docker) might overshadow the core newsletter task.
    - **Recommendation:** Start with Cron. If the project grows significantly in complexity (multiple interdependent scripts, complex error handling, backfills needed), then consider Airflow as a future upgrade.
- **Deployment:**
    - **Docker:** Essential for packaging the Python script, its dependencies, and any necessary environment configurations. Ensures consistency between development and Unraid. This is a non-negotiable best practice.
- **Version Control:**
    - **Git & GitHub:** Standard for tracking changes, collaboration, and showcasing the project. Excellent habit for a junior developer.
- **Server Environment:**
    - **Unraid Server:** The target deployment platform, well-suited for Docker containers and custom scripts.

---

### 3. Step-by-Step Implementation Guide

#### Phase 1: Setup & Initial Tautulli API Exploration

1. **Environment Setup:**
    - Create a project directory on your local machine.
    - Initialize a Git repository: `git init`
    - Create a Python virtual environment: `python -m venv venv` and activate it.
    - Create a `requirements.txt` file. Add initial libraries: `requests`, `python-dotenv` (for managing API keys).
    - Install them: `pip install -r requirements.txt`
    - Create a `.gitignore` file (e.g., from gitignore.io, for Python, venv).
2. **Tautulli API Familiarization:**
    - Locate your Tautulli API key (Settings -> Web Interface -> API). **Store this securely!** (e.g., in a `.env` file, loaded by `python-dotenv`, and add `.env` to `.gitignore`).
    - Consult the Tautulli API documentation (usually accessible via your Tautulli instance, e.g., `http://<your-tautulli-ip>:<port>/api/v2?apikey=<yourkey>&cmd=get_api_doc`).
    - Write a simple Python script (`test_tautulli.py`) to fetch basic data using the `requests` library:
        - Get server status (`get_activity`).
        - Get recently added media (`get_recently_added`).
        - _Why:_ This verifies API access and helps understand the data structures returned.
    - Example snippet for fetching recently added:
        
        Python
        
        ```
        import requests
        import os
        from dotenv import load_dotenv
        
        load_dotenv() # Load environment variables from .env file
        
        TAUTULLI_URL = os.getenv("TAUTULLI_URL") # e.g., http://localhost:8181
        TAUTULLI_API_KEY = os.getenv("TAUTULLI_API_KEY")
        
        def get_recently_added(count=5):
            params = {
                "apikey": TAUTULLI_API_KEY,
                "cmd": "get_recently_added",
                "count": count
            }
            try:
                response = requests.get(f"{TAUTULLI_URL}/api/v2", params=params)
                response.raise_for_status() # Raises an exception for bad status codes
                data = response.json()
                # print(json.dumps(data, indent=4)) # For inspecting the structure
                return data.get('response', {}).get('data', {}).get('recently_added', [])
            except requests.exceptions.RequestException as e:
                print(f"Error fetching recently added: {e}")
                return []
        
        if __name__ == "__main__":
            recent = get_recently_added()
            if recent:
                print("Recently Added:")
                for item in recent:
                    print(f"- {item.get('title')} ({item.get('year')})")
            else:
                print("Could not fetch recently added items.")
        ```
        
3. **SQLite Setup:**
    - Add `sqlite3` (built-in) to your mental checklist. No separate install needed.
    - Define a basic schema for tables you might need. Initially, perhaps tables for `users`, `media`, `watch_history`. This can evolve.
    - Write a small script to create the database and tables if they don't exist.

#### Phase 2: Data Extraction & Processing

1. **Identify Key Data Points from Tautulli:**
    - **Recently Added:** `get_recently_added` (title, year, type, posters, summary).
    - **User Activity:** `get_history` (filter by date range for "this week/month"). This will give `user`, `media_type`, `title`, `platform`, `player`.
    - **User List:** `get_users` or `get_user_names` to get Plex user details.
    - **Most Active Users:** Analyze `get_history` data, grouping by user and counting play duration or play count. Tautulli's `get_home_stats` might also provide this.
    - **Common Media:** This is the trickiest.
        - Fetch watch history for relevant users over a period.
        - For each piece of media, list users who watched it.
        - Identify media watched by multiple users.
        - _Consider using Pandas DataFrames here for easier manipulation._
2. **Develop Python Functions for Each Data Point:**
    - Create modular functions (e.g., `fetch_recent_media()`, `fetch_user_activity()`, `calculate_active_users()`, `find_common_media()`).
    - These functions will call the Tautulli API, process the JSON response, and return structured data (e.g., lists of dictionaries).
3. **Store/Cache Data in SQLite (Optional but Recommended):**
    - For complex calculations like "common media" or historical trends, regularly pulling all history can be slow.
    - You can periodically sync new watch history from Tautulli into your SQLite DB.
    - _Why:_ Improves performance and allows for more complex local queries without constantly hitting the Tautulli API.
    - Example: A table `plays` with `user_id`, `media_id`, `watched_at`.

#### Phase 3: Content & Visualization Generation

1. **Text Content:**
    - Define the sections of your newsletter (e.g., "New This Week," "Community Watchlist," "Top Streamers").
    - Write Python functions to format the data from Phase 2 into human-readable strings.
    - **(Advanced) AI Text Generation:**
        - If exploring Jasper/Copy.ai, identify small, specific text pieces to generate (e.g., a short, engaging summary for a popular new movie based on its Tautulli plot).
        - Make API calls to the chosen service. This will be an asynchronous task or done beforehand.
2. **Visualizations:**
    - **Matplotlib/Seaborn for Static Images:**
        - Example: Bar chart of top 5 most active users (play count/duration).
        - Save charts as PNG files: `plt.savefig('active_users.png')`.
        - Add `matplotlib` and `seaborn` to `requirements.txt`.
    - **Plotly/Bokeh for GIFs (Advanced):**
        - Example: Animated bar chart race of weekly user activity.
        - These libraries can export to HTML (not email friendly) or sometimes directly to image/GIF, or you might need an intermediary tool like `kaleido` for Plotly static image export. Research GIF export capabilities carefully.
        - Add `plotly` (and `kaleido`) or `bokeh` to `requirements.txt`.
    - **NetworkX for Connection Graphs:**
        - Model users and media items as nodes, and viewing relationships as edges.
        - Use a layout algorithm (e.g., `spring_layout`) and draw the graph.
        - Save as a PNG. This can be a very compelling visual.
        - Add `networkx` to `requirements.txt`.
    - **(Advanced) AI Image Generation (Midjourney/DALL-E 2):**
        - Concept: Generate a unique banner image for each newsletter or images for specific media items if high-quality posters aren't available.
        - Requires API calls and handling the returned images.
        - This adds significant complexity and cost; treat as a future enhancement.

#### Phase 4: Newsletter Templating & Assembly (HTML/CSS/Jinja2)

1. **Choose a CSS Approach:**
    - **Basic Inline CSS:** Simplest for email, but tedious.
    - **CSS Framework (Bootstrap/Tailwind):** Design your template, then use a tool like Premailer or Mailchimp's Inliner to convert CSS rules to inline styles before sending. This is highly recommended for better compatibility.
    - Add `jinja2` and `beautifulsoup4` (if needed for parsing/inlining) to `requirements.txt`.
2. **Create Jinja2 Templates:**
    - Create a `templates` directory in your project.
    - Develop a base HTML template (`base_newsletter.html`) with common structure (header, footer).
    - Create specific templates or include partials for different sections (e.g., `recent_media_section.html`, `user_stats_section.html`).
    - Use Jinja2 syntax (e.g., `{{ variable }}`, `{% for item in items %}`) to insert dynamic data.
    - Example `newsletter.html` (simplified):
        
        HTML
        
        ```
        <!DOCTYPE html>
        <html>
        <head>
            <title>Plex Newsletter</title>
            <style> /* Basic CSS, to be inlined later */
                body { font-family: sans-serif; }
                .media-item { border: 1px solid #ddd; margin-bottom: 10px; padding: 10px; }
            </style>
        </head>
        <body>
            <h1>Plex Weekly Digest</h1>
            <img src="cid:network_graph_cid" alt="User Connections" /> <h2>New This Week!</h2>
            {% for item in recently_added %}
                <div class="media-item">
                    <h3>{{ item.title }} ({{ item.year }})</h3>
                    <p>{{ item.summary }}</p>
                </div>
            {% endfor %}
        
            <h2>Community Corner</h2>
            <p>Most Active User: {{ most_active_user.name }} with {{ most_active_user.hours_watched }} hours!</p>
        
            <h2>Commonly Watched</h2>
            <ul>
            {% for common_item in common_media %}
                <li>{{ common_item.title }} - watched by: {{ common_item.users_list|join(', ') }}</li>
            {% endfor %}
            </ul>
        </body>
        </html>
        ```
        
3. **Render the Template in Python:**
    - Use Jinja2's `Environment` and `FileSystemLoader` to load templates.
    - Pass all your collected and processed data as context to the `render()` method.
    - The output will be a single HTML string.
    - Example snippet:
        
        Python
        
        ```
        from jinja2 import Environment, FileSystemLoader
        
        # ... (collect all your data into variables like recently_added_data, etc.)
        
        # In your main script
        env = Environment(loader=FileSystemLoader('templates/')) # Assuming templates are in a 'templates' subdir
        template = env.get_template('newsletter.html')
        
        html_content = template.render(
            recently_added=recently_added_data,
            most_active_user=most_active_user_data,
            common_media=common_media_data,
            # ... any other data for the template
            network_graph_cid="network_graph_cid" # Content-ID for embedded image
        )
        
        # (Optional, but recommended) Inline CSS here using a library like premailer
        # from premailer import transform
        # html_content = transform(html_content)
        ```
        

#### Phase 5: Email Sending Logic

1. **Configure `smtplib` for Gmail:**
    - **Crucial:** Enable 2-Step Verification on your Gmail account and generate an **App Password**. Do NOT use your main Gmail password in the script.
    - Store the App Password securely (e.g., in the `.env` file).
    - Add `EMAIL_ADDRESS` and `EMAIL_APP_PASSWORD` to your `.env`.
2. **Construct the Email:**
    - Use Python's `email.mime` modules (`MIMEMultipart`, `MIMEText`, `MIMEImage`) to create a multipart email. This allows embedding images and sending HTML.
    - Set `From`, `To`, `Subject` headers.
    - Attach the generated HTML content as `MIMEText('html')`.
    - Attach any generated images (charts, graphs) as `MIMEImage`, ensuring you set the `Content-ID` header if you referenced them via `cid:` in your HTML template.
3. **Send the Email:**
    - Connect to Gmail's SMTP server (`smtp.gmail.com`, port 587).
    - Start TLS encryption.
    - Log in with your email address and App Password.
    - Send the email.
    - Example snippet:
        
        Python
        
        ```
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.image import MIMEImage
        import os # For .env
        
        def send_email(subject, html_body, recipient_emails, image_paths=None):
            # image_paths can be a dict like {"network_graph_cid": "path/to/graph.png"}
            sender_email = os.getenv("EMAIL_ADDRESS")
            app_password = os.getenv("EMAIL_APP_PASSWORD")
        
            msg = MIMEMultipart('related') # 'related' for embedding images
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = ", ".join(recipient_emails) # Can send to multiple
        
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
        
            # Attach HTML part
            msg_text = MIMEText(html_body, 'html')
            msg_alternative.attach(msg_text)
        
            # Attach images
            if image_paths:
                for cid, img_path in image_paths.items():
                    try:
                        with open(img_path, 'rb') as fp:
                            img = MIMEImage(fp.read())
                        img.add_header('Content-ID', f'<{cid}>') # Matches cid: in HTML
                        img.add_header('Content-Disposition', 'inline', filename=os.path.basename(img_path))
                        msg.attach(img)
                    except FileNotFoundError:
                        print(f"Warning: Image {img_path} not found for embedding.")
        
        
            try:
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login(sender_email, app_password)
                    server.sendmail(sender_email, recipient_emails, msg.as_string())
                print("Newsletter sent successfully!")
            except Exception as e:
                print(f"Error sending email: {e}")
        
        # In main script, after generating html_content:
        # plex_user_emails = get_plex_user_emails_from_tautulli() # You'll need a function for this
        # image_files_to_embed = {"network_graph_cid": "path/to/your/network_graph.png"}
        # send_email("Your Plex Weekly Digest!", html_content, plex_user_emails, image_files_to_embed)
        ```
        
4. **Get User Emails:** Decide how to get Plex user emails. Tautulli might have them if users have linked accounts or if you manually entered them. _Privacy is key here; ensure you have consent._ If Tautulli doesn't have them directly, this might require a manual list.

#### Phase 6: Scheduling & Deployment on Unraid

1. **Dockerize the Application:**
    - Create a `Dockerfile`:
        
        Dockerfile
        
        ```
        # Use an official Python runtime as a parent image
        FROM python:3.9-slim
        
        # Set the working directory in the container
        WORKDIR /app
        
        # Copy the requirements file into the container at /app
        COPY requirements.txt .
        
        # Install any needed packages specified in requirements.txt
        # Add build dependencies for libraries like Pillow (for Matplotlib/Plotly image export) if needed
        RUN apt-get update && apt-get install -y --no-install-recommends \
            libgomp1 \ # Example: if a library needs it
            # Add other system dependencies here if specific Python packages require them for image generation
            # e.g., for Matplotlib on headless: libgl1-mesa-glx or similar
            && rm -rf /var/lib/apt/lists/*
        RUN pip install --no-cache-dir -r requirements.txt
        
        # Copy the rest of the application code into the container at /app
        COPY . .
        
        # Make port 80 available to the world outside this container (if you were running a web service)
        # Not strictly necessary for a script, but good practice if it ever evolves.
        # EXPOSE 80
        
        # Define environment variables (can be overridden at runtime)
        # ENV TAUTULLI_URL="http://your-tautulli-ip:port"
        # ENV TAUTULLI_API_KEY="yourkey"
        # ENV EMAIL_ADDRESS="youremail"
        # ENV EMAIL_APP_PASSWORD="yourapppassword"
        # Better to pass these via Docker run command or docker-compose.yml
        
        # Command to run the script
        CMD ["python", "main_newsletter_script.py"]
        ```
        
    - Ensure `main_newsletter_script.py` is your main executable Python file.
    - Build the Docker image: `docker build -t plex-newsletter-generator .`
    - Test run it locally: `docker run --rm -v $(pwd)/output_images:/app/output_images --env-file .env plex-newsletter-generator` (map a volume for images if they are saved to disk).
2. **Scheduling on Unraid:**
    - **Using User Scripts Plugin:**
        - Navigate to User Scripts in your Unraid web UI.
        - Create a new script.
        - Set the schedule (e.g., once a week on Sunday morning).
        - The script content will be a `docker run` command:
            
            Bash
            
            ```
            #!/bin/bash
            # Ensure your .env file is accessible or pass variables directly
            # Best practice: Mount .env file or specify env vars in the command
            # Assuming your script and Dockerfile are in /mnt/user/appdata/plex-newsletter/
            # And your .env file is also in /mnt/user/appdata/plex-newsletter/.env
            # And you want to save images to a subfolder also mapped to Unraid storage
            
            # Path to your project on Unraid where Dockerfile and .env are
            PROJECT_PATH="/mnt/user/appdata/plex-newsletter"
            # Path for SQLite DB and any images generated (ensure this path exists on Unraid)
            DATA_PATH="${PROJECT_PATH}/data"
            mkdir -p "${DATA_PATH}" # Ensure data directory exists
            
            docker run --rm \
                --env-file "${PROJECT_PATH}/.env" \
                -v "${DATA_PATH}:/app/data" \
                plex-newsletter-generator
            ```
            
        - **Important for Unraid Paths:** Docker paths are inside the container (`/app/data`). Unraid paths (`/mnt/user/...`) are on the host and get mapped.
        - Make sure your Python script saves/loads the SQLite DB and images to a path that's mapped in the Docker volume (e.g., `/app/data/newsletter.db`, `/app/data/active_users.png`).
3. **Logging and Error Handling:**
    - Implement robust logging within your Python script (using the `logging` module). Output to `stdout/stderr` so Docker can capture it.
    - Check Docker container logs via Unraid UI if the script fails.

---

### 4. Basic Verification/Testing

- **Manual Script Runs:** During development, run `python main_newsletter_script.py` locally to test each component.
- **Test Emails:** Send emails to your own address first to check formatting and content. Test on various email clients (Gmail, Outlook, mobile).
- **Docker Container Test:** Build and run the Docker container locally, ensuring it can access Tautulli and send emails.
- **Unraid Script Test:** Trigger the User Script manually from the Unraid UI to verify it runs correctly in the server environment. Check logs.
- **Data Accuracy:** Cross-reference generated stats (e.g., recent additions, active users) with what you see in Plex and Tautulli directly.

---

### 5. Security & Privacy Considerations

- **API Keys & Credentials:**
    - **NEVER** commit API keys, email passwords, or other secrets directly into your Git repository.
    - Use `.env` files for local development (add `.env` to `.gitignore`).
    - For Docker on Unraid, pass secrets as environment variables via the `docker run` command in the User Script or use Docker secrets if you scale up.
- **Email Privacy:**
    - Ensure you have consent from Plex users before sending them newsletters.
    - Provide an option to unsubscribe (though this adds complexity like managing a subscription list). For a private server, this might be less formal.
- **Tautulli Access:** Ensure your Tautulli instance is secured, especially if it's exposed to the internet.
- **Error Handling:** Implement try-except blocks for API calls, file operations, and email sending to handle failures gracefully.

---

### 6. Next Steps / Further Considerations

- **CSS Inlining Automation:** Integrate a Python library like `premailer` to automatically inline CSS for better email client compatibility.
- **Advanced AI Integration:** Fully implement the Midjourney/DALL-E 2 or Jasper/Copy.ai integrations if desired.
- **User Preferences:** Allow users to customize what sections they see (very advanced).
- **Unsubscribe Link:** If scaling or sending to a wider audience, implement a simple unsubscribe mechanism.
- **Web Interface (Major Expansion):** Create a small Flask/Django web app to show past newsletters or manage settings (this is a much larger project).
- **Transition to Airflow:** If the workflow becomes very complex with multiple dependent tasks, retries, and complex scheduling, migrating the orchestration to Airflow (run in Docker on Unraid) could be a valuable learning experience.
- **Transactional Email Service:** For better deliverability and analytics, switch from `smtplib`/Gmail to a service like SendGrid, Mailgun, or Amazon SES. Many offer free tiers sufficient for this project.