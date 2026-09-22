from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import os
import json
import requests
import urllib.parse
from flask import Flask, render_template, redirect, request, jsonify, session
from flask_cors import cross_origin
from datetime import datetime
import google_auth_oauthlib.flow
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import secrets
import time
import logging
import re


logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key')

BASE_URL = "https://transfermusic.pythonanywhere.com" if 'PYTHONANYWHERE_DOMAIN' in os.environ else "http://localhost:5000"
REDIRECT_URI = f"{BASE_URL}/callback"
YT_REDIRECT_URI = f"{BASE_URL}/yt_callback"

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

YT_SCOPES = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/youtube.force-ssl"]
YT_SECRET_FILE = os.getenv('YT_SECRET_FILE')
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

# Spotify helpers

def get_user_id():
    if 'user_id' not in session:
        if not check_token():
            return None
        headers = {'Authorization': f"Bearer {session['access_token']}"}
        try:
            response = requests.get('https://api.spotify.com/v1/me', headers=headers)
            response.raise_for_status()
            user_data = response.json()
            session['user_id'] = user_data['id']
            logger.info(f"Retrieved Spotify user ID: {session['user_id']}")
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Spotify user ID: {e}")
            return None
    return session['user_id']

def check_token():
    if 'access_token' not in session or 'expires_at' not in session:
        logger.warning("Spotify access token missing.")
        return False
    if datetime.now().timestamp() > session['expires_at']:
        logger.info("Spotify token expired. Attempting to refresh.")
        return refresh_token()
    return True

def refresh_token():
    if 'refresh_token' not in session:
        logger.warning("No Spotify refresh token.")
        return False
    
    req_body = {
        'grant_type': 'refresh_token',
        'refresh_token': session['refresh_token'],
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    try:
        response = requests.post(TOKEN_URL, data=req_body)
        response.raise_for_status()
        new_token_info = response.json()
        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']
        logger.info("Spotify token refreshed successfully.")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to refresh Spotify token: {e}")
        session.pop('refresh_token', None)
        session.pop('access_token', None)
        session.pop('expires_at', None)
        return False

def get_spotify_playlist_name(playlist_id):
    if not check_token():
        return "Transferred Playlist"
    headers = {'Authorization': f"Bearer {session['access_token']}"}
    try:
        response = requests.get(f"{API_BASE_URL}playlists/{playlist_id}", headers=headers)
        response.raise_for_status()
        return response.json().get('name', 'Transferred Playlist')
    except requests.RequestException as e:
        logger.error(f"Failed to get Spotify playlist name: {e}")
        return "Transferred Playlist"

def get_spotify_songs(playlist_id):
    if not check_token():
        return []
    spotify_songs = []
    next_url = f"{API_BASE_URL}playlists/{playlist_id}/tracks"
    headers = {'Authorization': f"Bearer {session['access_token']}"}

    while next_url:
        try:
            response = requests.get(next_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            for item in data.get('items', []):
                track = item.get('track')
                if track and track.get('name') and track.get('artists'):
                    song_name = track['name']
                    artist_name = track['artists'][0]['name'] if track['artists'] else "Unknown Artist"
                    spotify_songs.append({'name': song_name, 'artist': artist_name})
            next_url = data.get('next')
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Spotify songs: {e}")
            break

    logger.info(f"Total Spotify songs found: {len(spotify_songs)}")
    return spotify_songs

def search_spotify_bulk(songs):
    if not check_token():
        return {}
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    song_map = {}

    for song in songs:
        query = f"{song['name']} {song['artist']}"
        logger.info(f"Searching Spotify for: {query}")
        try:
            response = requests.get(
                f"{API_BASE_URL}search",
                headers=headers,
                params={"q": query, "type": "track", "limit": 1}
            )
            response.raise_for_status()
            data = response.json()
            tracks = data.get("tracks", {}).get("items", [])
            if tracks:
                track_id = tracks[0]["id"]
                song_map[song["name"]] = track_id
                logger.info(f"Matched: {song['name']} -> {track_id}")
        except requests.RequestException as e:
            logger.error(f"Spotify search error: {e}")

    return song_map

def create_spotify_playlist_and_add_songs(title, song_ids):
    if not check_token():
        return None
    headers = {"Authorization": f"Bearer {session['access_token']}", "Content-Type": "application/json"}
    user_id = get_user_id()
    if not user_id:
        return None

    try:
        playlist_data = {"name": title, "description": "Playlist transferred with TransferMusic", "public": False}
        response = requests.post(f"{API_BASE_URL}users/{user_id}/playlists", headers=headers, json=playlist_data)
        response.raise_for_status()
        playlist_id = response.json()["id"]
        logger.info(f"Created Spotify Playlist: {title} (ID: {playlist_id})")

        if song_ids:
            requests.post(
                f"{API_BASE_URL}playlists/{playlist_id}/tracks",
                headers=headers,
                json={"uris": [f"spotify:track:{track_id}" for track_id in song_ids]}
            )
            logger.info(f"Added {len(song_ids)} songs to Spotify playlist")
        return playlist_id
    except requests.RequestException as e:
        logger.error(f"Failed to create Spotify playlist: {e}")
        return None

# YouTube helpers

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def validate_youtube_credentials():
    """Validate and refresh YouTube credentials; return None if they are invalid."""
    yt_credentials_dict = session.get('yt_credentials')
    if not yt_credentials_dict:
        logger.warning("No YouTube credentials in session. Redirecting to login.")
        return None

    try:
        yt_credentials = Credentials(
            token=yt_credentials_dict['token'],
            refresh_token=yt_credentials_dict['refresh_token'],
            token_uri=yt_credentials_dict['token_uri'],
            client_id=yt_credentials_dict['client_id'],
            client_secret=yt_credentials_dict['client_secret'],
            scopes=yt_credentials_dict['scopes']
        )
    except Exception as e:
        logger.error(f"Failed to initialize YouTube credentials: {e}")
        session.pop('yt_credentials', None)
        return None

    if yt_credentials.expired and yt_credentials.refresh_token:
        try:
            logger.info("YouTube token expired. Refreshing...")
            yt_credentials.refresh(Request())
            session['yt_credentials'] = credentials_to_dict(yt_credentials)
            logger.info("YouTube token refreshed successfully.")
        except RefreshError as e:
            logger.error(f"Failed to refresh YouTube token: {e}")
            session.pop('yt_credentials', None)
            return None
    elif not yt_credentials.valid:
        logger.warning("YouTube token invalid and cannot be refreshed.")
        session.pop('yt_credentials', None)
        return None

    logger.info("YouTube token is valid.")
    return yt_credentials

def fuzzy_match(song_name, title):
    song_words = re.findall(r'\w+', song_name.lower())
    title_words = re.findall(r'\w+', title.lower())
    match_count = sum(1 for word in song_words if word in title_words)
    return match_count >= max(1, len(song_words) // 2)

def search_youtube_bulk(songs):
    yt_credentials = validate_youtube_credentials()
    if not yt_credentials:
        logger.warning("Invalid YouTube credentials. Redirecting to login.")
        return None

    youtube = build("youtube", "v3", credentials=yt_credentials)
    video_map = {}

    for song in songs:
        query = f"{song['name']} {song['artist']}"
        logger.info(f"Searching YouTube for: {query}")
        try:
            search_response = youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=5
            ).execute()
            for item in search_response.get("items", []):
                title = item["snippet"]["title"].lower()
                video_id = item["id"]["videoId"]
                channel_title = item["snippet"]["channelTitle"].lower()
                song_name = song["name"].lower()
                artist_name = song["artist"].lower()
                if fuzzy_match(song_name, title) or fuzzy_match(song_name, channel_title):
                    video_map[song["name"]] = video_id
                    logger.info(f"Matched: {song['name']} -> {video_id}")
                    break
        except HttpError as e:
            logger.error(f"YouTube API Error: {e}")
            if e.resp.status == 401:  # Unauthorized request.
                logger.warning("Received 401 Unauthorized. Token may be invalid.")
                return None
            elif e.resp.status == 403:
                logger.warning("YouTube API Quota Exceeded!")
                return {}
            else:
                return None  # Other API errors are handled as authentication failures.
        except Exception as e:
            logger.error(f"Unexpected error in YouTube search: {e}")
            return None

    return video_map

def add_video(youtube, playlist_id, video_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id}
                    }
                }
            ).execute()
            logger.info(f"Added: {response['snippet']['title']} (ID: {video_id})")
            return True
        except HttpError as e:
            logger.error(f"Error adding video {video_id}: {e}")
            if e.resp.status == 409:
                logger.warning(f"Retry {attempt + 1}: YouTube API Service Unavailable")
                time.sleep(5)
            else:
                return False
    return False

def create_youtube_playlist_and_add_songs(title, song_ids):
    yt_credentials = validate_youtube_credentials()
    if not yt_credentials:
        return None
    youtube = build("youtube", "v3", credentials=yt_credentials)
    try:
        playlist_response = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title, "description": "Playlist transferred with TransferMusic"},
                "status": {"privacyStatus": "private"}
            }
        ).execute()
        playlist_id = playlist_response["id"]
        logger.info(f"Created YouTube Playlist: {title} (ID: {playlist_id})")

        for vid in song_ids:
            add_video(youtube, playlist_id, vid)
        return playlist_id
    except HttpError as e:
        logger.error(f"Failed to create YouTube playlist: {e}")
        return None

def get_youtube_playlist_songs(playlist_id):
    yt_credentials = validate_youtube_credentials()
    if not yt_credentials:
        return []
    youtube = build("youtube", "v3", credentials=yt_credentials)
    youtube_songs = []
    next_page_token = None

    while True:
        try:
            response = youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()
            for item in response.get("items", []):
                title = item["snippet"]["title"]
                artist = item["snippet"].get("videoOwnerChannelTitle", "Unknown Artist").replace(" - Topic", "")
                song_name = title.split(" - ")[-1] if " - " in title else title
                youtube_songs.append({"name": song_name, "artist": artist})
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
        except HttpError as e:
            logger.error(f"Error fetching YouTube playlist: {e}")
            break

    logger.info(f"Total YouTube songs found: {len(youtube_songs)}")
    return youtube_songs

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/reset_session')
def reset_session():
    session.clear()
    logger.info("Session cleared.")
    return redirect('/')

@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/terms_of_service')
def terms_of_service():
    return render_template('terms_of_service.html')

# Spotify routes

@app.route('/login')
def login():
    scope = 'playlist-read-collaborative playlist-read-private playlist-modify-private playlist-modify-public'
    # Store the return URL in the session.
    return_url = request.args.get('return_url', '/playlists')
    session['sp_return_url'] = return_url
    logger.info(f"Storing return URL in session: {return_url}")
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    logger.info("Redirecting to Spotify login.")
    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        logger.error(f"Spotify login error: {request.args['error']}")
        return jsonify({'error': request.args['error']})

    if 'code' not in request.args:
        logger.error("No authorization code received from Spotify.")
        return jsonify({'error': 'No authorization code provided'}), 400

    req_body = {
        'code': request.args['code'],
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    logger.info(f"Sending token request to Spotify with redirect_uri: {REDIRECT_URI}")

    try:
        response = requests.post(TOKEN_URL, data=req_body, timeout=10)
        response.raise_for_status()
        token_info = response.json()
        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']
        logger.info("Spotify login successful.")
        # Redirect to the stored return URL after authentication.
        return_url = session.pop('sp_return_url', '/playlists')
        # Restore the appropriate playlist page after authentication.
        if return_url.startswith('/transfer_playlist') or return_url.startswith('/transfer_youtube_to_spotify'):
            playlist_id = urllib.parse.parse_qs(urllib.parse.urlparse(return_url).query).get('playlist_id', [''])[0]
            target = '/playlists' if return_url.startswith('/transfer_playlist') else '/yt_playlists'
            return redirect(f"{target}?playlist_id={playlist_id}")
        logger.info(f"Redirecting to {return_url}")
        return redirect(return_url)
    except requests.exceptions.HTTPError as e:
        logger.error(f"Spotify callback HTTP error: {e} - Status: {response.status_code} - Response: {response.text}")
        return jsonify({'error': f"Authentication failed: {response.text}"}), response.status_code
    except requests.exceptions.Timeout:
        logger.error("Spotify callback timed out.")
        return jsonify({'error': 'Request to Spotify timed out'}), 504
    except requests.RequestException as e:
        logger.error(f"Spotify callback error: {e}")
        return jsonify({'error': 'Authentication failed due to network error'}), 500

@app.route('/playlists')
def get_playlists():
    if not check_token():
        logger.warning("Spotify authentication required.")
        return redirect('/login')
    
    headers = {'Authorization': f"Bearer {session['access_token']}"}
    try:
        response = requests.get(f"{API_BASE_URL}me/playlists", headers=headers)
        response.raise_for_status()
        playlists_data = response.json().get('items', [])
        logger.info(f"Retrieved {len(playlists_data)} Spotify playlists.")
        return render_template('playlists.html', playlists=playlists_data)
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Spotify playlists: {e}")
        return jsonify({'error': 'Failed to fetch playlists'}), 500

@app.route('/transfer_playlist')
def transfer_playlist():
    playlist_id = request.args.get('playlist_id')
    if not playlist_id:
        logger.error("No playlist selected.")
        return jsonify({'error': 'No playlist selected'}), 400
    
    if not check_token():
        logger.warning("Spotify authentication failed.")
        return_url = f"/transfer_playlist?playlist_id={playlist_id}"
        return jsonify({'redirect': f"/login?return_url={urllib.parse.quote(return_url)}"}), 401

    if not validate_youtube_credentials():
        logger.warning("YouTube authentication failed or missing.")
        return_url = f"/transfer_playlist?playlist_id={playlist_id}"
        return jsonify({'redirect': f"/yt_login?return_url={urllib.parse.quote(return_url)}"}), 401

    logger.info(f"Fetching songs for Spotify playlist ID: {playlist_id}")
    spotify_songs = get_spotify_songs(playlist_id)
    if not spotify_songs:
        logger.warning("No songs found in Spotify playlist.")
        return jsonify({'error': 'No songs found in Spotify playlist'}), 404

    spotify_playlist_title = get_spotify_playlist_name(playlist_id)
    logger.info(f"Found {len(spotify_songs)} songs. Searching YouTube...")
    
    video_map = search_youtube_bulk(spotify_songs)
    if video_map is None:
        logger.warning("YouTube credentials invalid during transfer.")
        return_url = f"/transfer_playlist?playlist={playlist_id}"
        return jsonify({'redirect': f"/yt_login?return_url={urllib.parse.quote(return_url)}"}), 401
    
    video_ids = [video_map.get(song['name']) for song in spotify_songs if song['name'] in video_map]
    if not video_ids:
        logger.warning("No matching songs found on YouTube.")
        return jsonify({'error': 'No matching songs found on YouTube'}), 404

    logger.info(f"Adding {len(video_ids)} videos to YouTube playlist...")
    yt_playlist_id = create_youtube_playlist_and_add_songs(spotify_playlist_title, video_ids)
    if yt_playlist_id:
        logger.info("Playlist transferred successfully.")
        return jsonify({
            'message': 'Playlist transferred successfully',
            'playlist_id': yt_playlist_id,
            'playlist_name': spotify_playlist_title
        })
    else:
        logger.error("Failed to create YouTube playlist.")
        return jsonify({'error': 'Failed to create YouTube playlist'}), 500

# YouTube routes

@app.route('/yt_login')
@cross_origin()
def yt_login():
    state = secrets.token_urlsafe(16)
    session['state'] = state
    print(state)
    # Store the return URL in the session.
    return_url = request.args.get('return_url', '/yt_playlists')
    session['yt_return_url'] = return_url
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(YT_SECRET_FILE, scopes=YT_SCOPES)
    flow.redirect_uri = YT_REDIRECT_URI
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=state,
        prompt='consent'
    )
    logger.info("Redirecting to YouTube login.")
    return redirect(authorization_url)

@app.route('/yt_callback')
def yt_callback():
    state_stored = session.get('state')
    state_received = request.args.get('state')
    print(state_stored)
    print(state_received)
    if state_received != state_stored:
        logger.error("State parameter mismatch.")
        return 'State parameter does not match!', 400
    
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(YT_SECRET_FILE, scopes=YT_SCOPES)
    flow.redirect_uri = YT_REDIRECT_URI
    try:
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        session['yt_credentials'] = credentials_to_dict(credentials)
        logger.info("YouTube login successful.")
        # Redirect to the stored return URL after authentication.
        return_url = session.pop('yt_return_url', '/yt_playlists')
        # Restore the appropriate playlist page after authentication.
        if return_url.startswith('/transfer_youtube_to_spotify') or return_url.startswith('/transfer_playlist'):
            playlist_id = urllib.parse.parse_qs(urllib.parse.urlparse(return_url).query).get('playlist_id', [''])[0]
            target = '/yt_playlists' if return_url.startswith('/transfer_youtube_to_spotify') else '/playlists'
            return redirect(f"{target}?playlist_id={playlist_id}")
        return redirect(return_url)
    except Exception as e:
        logger.error(f"YouTube callback error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

@app.route('/yt_playlists')
def yt_playlists():
    if not validate_youtube_credentials():
        logger.warning("YouTube authentication required.")
        return redirect('/yt_login')
    
    credentials = session.get('yt_credentials')
    youtube = build(API_SERVICE_NAME, API_VERSION, credentials=Credentials(**credentials))
    try:
        playlists_response = youtube.playlists().list(part='snippet', mine=True, maxResults=25).execute()
        playlists_data = playlists_response.get('items', [])
        if not playlists_data:
            logger.warning("No YouTube playlists found.")
            return jsonify({'error': 'No playlists found'}), 404

        playlists = [{
            'title': p['snippet']['title'],
            'id': p['id'],
            'thumbnail': p['snippet']['thumbnails']['default']['url'] if 'thumbnails' in p['snippet'] else None
        } for p in playlists_data]
        logger.info(f"Retrieved {len(playlists)} YouTube playlists.")
        return render_template('yt_playlists.html', playlists=playlists)
    except HttpError as e:
        logger.error(f"Failed to fetch YouTube playlists: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/transfer_youtube_to_spotify')
def transfer_youtube_to_spotify():
    playlist_id = request.args.get("playlist_id")
    if not playlist_id:
        logger.error("No playlist selected.")
        return jsonify({'error': 'No playlist selected'}), 400
    if not validate_youtube_credentials():
        logger.warning("YouTube authentication failed or missing.")
        # Preserve the selected playlist while re-authenticating.
        return_url = f"/transfer_youtube_to_spotify?playlist_id={playlist_id}"
        return redirect(f"/yt_login?return_url={urllib.parse.quote(return_url)}"), 401
    if not check_token():
        logger.warning("Spotify authentication failed.")
        # Preserve the selected playlist while re-authenticating.
        return_url = f"/transfer_youtube_to_spotify?playlist_id={playlist_id}"
        return jsonify({'redirect': f"/login?return_url={urllib.parse.quote(return_url)}"}), 401

    logger.info(f"Fetching YouTube playlist ID: {playlist_id}")
    youtube_songs = get_youtube_playlist_songs(playlist_id)
    if not youtube_songs:
        logger.warning("No songs found in YouTube playlist.")
        return jsonify({'error': 'No songs found in YouTube playlist'}), 404

    yt_credentials = session['yt_credentials']
    youtube = build("youtube", "v3", credentials=Credentials(**yt_credentials))
    try:
        playlist_response = youtube.playlists().list(part="snippet", id=playlist_id).execute()
        playlist_title = playlist_response["items"][0]["snippet"]["title"]
    except HttpError as e:
        logger.error(f"Failed to get YouTube playlist title: {e}")
        playlist_title = "Transferred Playlist"

    spotify_song_map = search_spotify_bulk(youtube_songs)
    song_ids = [spotify_song_map.get(song['name']) for song in youtube_songs if song['name'] in spotify_song_map]
    if not song_ids:
        logger.warning("No matching songs found on Spotify.")
        return jsonify({'error': 'No matching songs found on Spotify'}), 404

    spotify_playlist_id = create_spotify_playlist_and_add_songs(playlist_title, song_ids)
    if spotify_playlist_id:
        logger.info("Playlist transferred successfully.")
        return jsonify({
            'message': 'Playlist transferred successfully',
            'playlist_id': spotify_playlist_id,
            'playlist_name': playlist_title
        })
    else:
        logger.error("Failed to create Spotify playlist.")
        return jsonify({'error': 'Failed to create Spotify playlist'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)