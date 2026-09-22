# TransferMusic

TransferMusic is a Flask web application created as my final secondary-school project and submitted as part of my matura. The project received a grade of **5**.

The project was built to explore working with music-platform APIs, OAuth authentication, playlists, and a small Flask-based web interface. It integrates with the **Spotify Web API** and **YouTube Data API v3**.

> **Project status:** Portfolio / educational project. The application worked during its original development period. Since then, Spotify has changed its Web API access rules and parts of the API, so some functionality may require adaptation before the project can be used again today.

## What the project demonstrates

The current version of the project includes:

- Spotify OAuth authentication
- loading the authenticated user's Spotify playlists
- selecting a Spotify playlist
- displaying songs from the selected playlist
- pagination for Spotify playlist tracks
- Google / YouTube OAuth authentication
- loading the authenticated user's YouTube playlists
- displaying YouTube playlist titles and thumbnails
- storing selected Spotify playlist data locally with TinyDB
- Flask sessions for authentication data
- HTML templates with CSS and a small amount of JavaScript
- separate configuration for local development and PythonAnywhere hosting

The original goal of TransferMusic was to work with playlists across Spotify and YouTube. This repository is preserved primarily as a portfolio and learning project showing the API integration, authentication flow, and web-development work completed for the final project.

## Technologies

- Python
- Flask
- Spotify Web API
- YouTube Data API v3
- Google OAuth 2.0
- TinyDB
- Requests
- HTML
- CSS
- JavaScript
- Jinja templates
- python-dotenv

## Project structure

```text
TransferMusic/
├── static/
│   ├── CSS/
│   └── js/
├── templates/
│   ├── index.html
│   ├── playlists.html
│   ├── songs.html
│   ├── yt.html
│   └── yt_playlists.html
├── .env.example
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

Runtime files containing credentials or local user data are intentionally excluded from the public repository.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/patrik066/TransferMusic.git
cd TransferMusic
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the environment file

Copy `.env.example` to `.env` and enter your own credentials.

Example:

```env
CLIENT_ID=your_spotify_client_id
CLIENT_SECRET=your_spotify_client_secret
YT_SECRET_FILE=secrets/yt_client_secret.json
FLASK_SECRET_KEY=replace_with_a_random_secret
```

Do **not** commit `.env` to Git.

### 5. Configure Google OAuth

Create a Google Cloud project with access to the YouTube Data API v3 and create an OAuth client for a web application.

Place the downloaded OAuth client JSON file at:

```text
secrets/yt_client_secret.json
```

The `secrets/` directory is ignored by Git so credentials are not published.

For local development, the callback used by the project is:

```text
http://localhost:5000/yt_callback
```

### 6. Configure Spotify

Create an application in the Spotify Developer Dashboard and add the local redirect URI:

```text
http://localhost:5000/callback
```

Put the application's Client ID and Client Secret in `.env`.

### 7. Run the application

```bash
python main.py
```

Then open:

```text
http://localhost:5000
```

## Current Spotify compatibility

TransferMusic was developed before Spotify's 2026 Development Mode changes.

Spotify currently requires the owner of a Development Mode application to have an active **Spotify Premium** subscription for the app to function. Spotify has also changed parts of its Web API and playlist-related behavior since this project was originally written.

Because of these external platform changes, this repository should be viewed as a preserved educational/portfolio project unless the API integration is updated and tested against the current Spotify Web API.

Current Spotify documentation:

- https://developer.spotify.com/documentation/web-api/concepts/quota-modes
- https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide

## Security

No API secrets, OAuth client secrets, `.env` files, or local playlist database files are intended to be stored in this public repository.

The following are excluded through `.gitignore`:

```text
.env
.env.*
secrets/
db_spotify.json
```

Only `.env.example` is included to document which environment variables are required.

## Background

This project was developed as my final secondary-school project. It gave me practical experience with:

- REST APIs
- OAuth 2.0 authentication
- access and refresh tokens
- HTTP requests
- Flask routing
- sessions
- external API integration
- JSON data
- local data storage
- frontend templates
- deployment to PythonAnywhere
- handling credentials through environment variables

The finished project received a grade of **5** as part of my matura work.

## Author

**Patrik Gašperlin**

GitHub: [patrik066](https://github.com/patrik066)

## Note

This repository documents a student project and its original implementation. Spotify and Google APIs are external services and their requirements can change independently of this code.
