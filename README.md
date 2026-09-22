# TransferMusic

TransferMusic is a Flask web application developed as my final secondary-school project in 2025. The project received the highest grade (5).

The application was created to solve a problem I had myself: moving music playlists between Spotify and YouTube.

TransferMusic integrates with the **Spotify Web API** and **YouTube Data API v3** and was built to transfer playlists in both directions:

- Spotify → YouTube
- YouTube → Spotify

The project combines OAuth 2.0 authentication, REST APIs, playlist processing, song matching, Flask backend development, and a simple web interface.

> **Project status:** This repository preserves the original implementation of my 2025 final secondary-school project. The application worked during its original development and presentation period. Since then, Spotify has changed parts of its Web API and Development Mode requirements, so some functionality may no longer work without adapting the original code to the current API.

---

## Features

The final version of TransferMusic includes:

- Spotify OAuth authentication
- Google / YouTube OAuth authentication
- Spotify and YouTube access-token refresh handling
- loading the authenticated user's Spotify playlists
- loading the authenticated user's YouTube playlists
- transferring Spotify playlists to YouTube
- transferring YouTube playlists to Spotify
- retrieving songs from source playlists
- searching for corresponding songs or videos on the destination platform
- basic fuzzy matching for YouTube search results
- creating new playlists on Spotify
- creating new playlists on YouTube
- adding matched songs or videos to newly created playlists
- pagination when retrieving playlist contents
- error handling for external API requests
- application logging
- AJAX-based playlist transfers and status updates
- Flask sessions for authentication and transfer state
- Privacy Policy and Terms of Service pages
- configuration for both local development and the original PythonAnywhere deployment

---

## How it works

### Spotify → YouTube

When a user chooses a Spotify playlist, TransferMusic:

1. retrieves the playlist name and songs from Spotify,
2. processes all pages of the playlist,
3. searches YouTube using the song title and artist,
4. performs basic matching against the returned YouTube results,
5. creates a new private YouTube playlist,
6. adds the matched videos to the new playlist.

Songs for which a suitable match is not found are skipped.

### YouTube → Spotify

When a user chooses a YouTube playlist, TransferMusic:

1. retrieves the videos from the selected playlist,
2. extracts song and artist information from the video metadata,
3. searches Spotify for corresponding tracks,
4. creates a new private Spotify playlist,
5. adds the matched Spotify tracks to the playlist.

Because song and video names can differ between platforms, matching is not guaranteed to be perfect.

---

## Technologies

### Backend

- Python
- Flask
- Flask-Cors
- Requests
- python-dotenv

### APIs and authentication

- Spotify Web API
- YouTube Data API v3
- Spotify OAuth 2.0
- Google OAuth 2.0
- google-auth
- google-auth-oauthlib
- google-api-python-client
- oauthlib

### Frontend

- HTML
- CSS
- JavaScript
- jQuery / AJAX
- Jinja templates

### Deployment

- PythonAnywhere

---

## Project structure

```text
TransferMusic/
├── static/
│   ├── CSS/
│   │   └── style.css
│   └── logo/
│       ├── logo.png
│       └── logo1.png
│
├── templates/
│   ├── index.html
│   ├── playlists.html
│   ├── privacy_policy.html
│   ├── terms_of_service.html
│   └── yt_playlists.html
│
├── .env.example
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

Credentials, OAuth client secrets, local environment files, and local user data are intentionally excluded from the public repository.

---

## Setup

The following setup describes how the original project is configured.

Because Spotify changed its Development Mode API in 2026, completing these steps does not guarantee that the original Spotify integration will work without adapting the old API endpoints. See the **Current Spotify compatibility** section below.

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

Copy `.env.example` to `.env`.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux / macOS:

```bash
cp .env.example .env
```

The file contains the following configuration:

```env
FLASK_SECRET_KEY=replace_with_a_new_random_secret

CLIENT_ID=your_spotify_client_id
CLIENT_SECRET=your_spotify_client_secret

YT_SECRET_FILE=secrets/yt_client_secret.json
```

A random Flask secret can be generated with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Never commit the completed `.env` file.

---

## Spotify configuration

Create an application in the Spotify Developer Dashboard.

For local development, the project uses this callback URI:

```text
http://localhost:5000/callback
```

Place the application's Spotify Client ID and Client Secret in `.env`:

```env
CLIENT_ID=your_spotify_client_id
CLIENT_SECRET=your_spotify_client_secret
```

The application requests permissions required to read and modify playlists.

---

## Google / YouTube configuration

Create a Google Cloud project and enable the **YouTube Data API v3**.

Create an OAuth 2.0 client for a web application.

For local development, the project uses this callback URI:

```text
http://localhost:5000/yt_callback
```

Create the local secrets directory:

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force secrets
```

Linux / macOS:

```bash
mkdir -p secrets
```

Place the downloaded Google OAuth client JSON file at:

```text
secrets/yt_client_secret.json
```

The `secrets/` directory is excluded from Git and must never be committed.

---

## Running the application

Start the Flask application with:

```bash
python main.py
```

Then open:

```text
http://localhost:5000
```

From the home page, the user can authenticate with either Spotify or YouTube and view playlists associated with the authenticated account.

---

## Playlist transfer process

TransferMusic does not copy audio files between services.

Instead, it reads metadata from the source playlist and searches for corresponding content on the destination platform.

During a Spotify → YouTube transfer, the application uses the Spotify song name and artist to search YouTube. When a suitable video is found, its video ID is added to a newly created YouTube playlist.

The reverse process extracts information from YouTube playlist items, searches Spotify for corresponding tracks, and adds the matched Spotify track IDs to a newly created playlist.

This means that transfer accuracy depends on search results and on differences in song naming between Spotify and YouTube.

---

## Song matching

One of the main challenges of the project was matching songs between two different platforms.

A track may appear as:

```text
Artist - Song Name
```

on one platform and:

```text
Song Name (Official Audio)
```

on another.

TransferMusic therefore combines search queries with basic text matching to determine whether a YouTube search result is likely to represent the requested song.

This is intentionally a relatively simple matching system and can occasionally select an incorrect result or fail to find a match.

Improving song matching was one of the possible future improvements identified during the original project.

---

## OAuth and token handling

Both Spotify and YouTube require OAuth authentication.

The project handles:

- access tokens
- refresh tokens
- token expiration
- token refresh
- OAuth callbacks
- authentication redirects
- preserving the selected playlist during re-authentication

The YouTube OAuth flow also uses a generated state value to validate the authentication callback.

---

## Current Spotify compatibility

TransferMusic was developed against the Spotify Web API available during the original development of the project in 2025.

Spotify introduced significant Development Mode changes in 2026. For Development Mode applications, Spotify currently requires the application owner to have an active **Spotify Premium** subscription.

Spotify also replaced playlist endpoints used by the original TransferMusic implementation.

The original project uses endpoints such as:

```text
GET  /playlists/{id}/tracks
POST /playlists/{id}/tracks
POST /users/{user_id}/playlists
```

In Spotify's updated Development Mode API, these endpoints have replacements such as:

```text
GET  /playlists/{id}/items
POST /playlists/{id}/items
POST /me/playlists
```

The original source code has intentionally not been rewritten to use the 2026 endpoints because this repository is intended to preserve the final project as it was originally implemented.

As a result, the Spotify transfer functionality may require API migration before it can work with a current Development Mode application.

Official Spotify documentation:

- https://developer.spotify.com/documentation/web-api/concepts/quota-modes
- https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide

---

## YouTube API considerations

TransferMusic searches YouTube separately for songs being transferred from Spotify and then adds matched videos to a playlist.

The YouTube Data API applies quotas to API operations. Search and playlist modification requests therefore limit how many operations an application can perform within the available quota.

Large playlist transfers may consequently be affected by YouTube API quota limits.

---

## Original deployment

The project was originally deployed on PythonAnywhere at:

https://transfermusic.pythonanywhere.com

The deployment URL is preserved here as part of the project's history.

Availability or full functionality of the original deployment is not guaranteed because the external APIs and their access requirements have changed since the project was developed.

---

## Security

No real API credentials or OAuth client secrets are intended to be stored in this public repository.

The repository excludes local configuration and secret files such as:

```text
.env
secrets/
db_spotify.json
```

Only `.env.example` is included to document the required environment variables.

The original credentials used during development have been removed from the public portfolio version.

Anyone running the project must create their own Spotify and Google applications and provide their own credentials.

---

## Historical implementation

This repository is intended to represent the final version of the project as it was developed for school.

The transfer logic has intentionally been preserved rather than silently rewriting the project to follow newer API designs.

Minor repository cleanup has been performed for the public portfolio version, including:

- removing credentials and local user data
- providing `.env.example`
- translating code comments to English
- removing an unused empty JavaScript file
- documenting the dependencies required by the final version
- improving the project documentation

These changes do not alter the original playlist-transfer logic.

---

## What I learned

Developing TransferMusic gave me practical experience with:

- designing a Flask web application
- REST API integration
- OAuth 2.0 authentication
- access and refresh tokens
- HTTP requests and responses
- JSON data processing
- API pagination
- handling external API errors
- playlist and song metadata
- matching data from different platforms
- asynchronous requests with AJAX
- frontend and backend integration
- environment variables and credential management
- application deployment with PythonAnywhere

One of the most interesting challenges was dealing with the fact that Spotify tracks and YouTube videos often use different titles and artist naming conventions.

---

## Project background

TransferMusic was developed as my final secondary-school project.

The original idea came from a personal problem: manually recreating the same playlists across Spotify and YouTube was slow and repetitive.

The goal was therefore to build a web application that could automate as much of that process as possible using the APIs provided by both platforms.

The completed project received the **highest grade (5)**.

---

## Author

**Patrik Gašperlin**

GitHub: [patrik066](https://github.com/patrik066)

---

## Note

TransferMusic is an educational and portfolio project preserved from its original 2025 implementation.

Spotify, Google, and YouTube are external services whose APIs, quotas, authentication requirements, and access policies can change independently of this repository.
