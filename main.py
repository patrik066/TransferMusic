# For working without HTTPS (YT)

import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Spotify

import json
import requests
import urllib.parse

from flask import Flask, render_template, redirect, request, jsonify, session
from datetime import datetime
from tinydb import Query, TinyDB

# YouTube

import google.oauth2.credentials
import google_auth_oauthlib.flow
import secrets

from googleapiclient.discovery import build

if 'PYTHONANYWHERE_DOMAIN' in os.environ:
    BASE_URL = "https://transfermusic.pythonanywhere.com"
else:
    BASE_URL = "http://localhost:5000"

# Set dynamic redirect URIs
SPOTIFY_REDIRECT_URI = f"{BASE_URL}/callback"
YOUTUBE_REDIRECT_URI = f"{BASE_URL}/yt_callback"

# Set these as environment variables
os.environ["REDIRECT_URI"] = SPOTIFY_REDIRECT_URI
os.environ["YT_REDIRECT_URI"] = YOUTUBE_REDIRECT_URI

# Spremenljivke

from dotenv import load_dotenv

load_dotenv()

# Data Base

app = Flask(__name__)
db_spotify = TinyDB('db_spotify.json')
User = Query()

# Spotify

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key')

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

# YouTube

YT_SCOPES = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/youtube.force-ssl"]
YT_SECRET_FILE = os.getenv('YT_SECRET_FILE')
YT_REDIRECT_URI = os.getenv('YT_REDIRECT_URI')

API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

print(REDIRECT_URI)
print(YT_REDIRECT_URI)

################### Spotify (podprogrami) ################################

def get_user_id():
    if 'user_id' not in session:
        if 'access_token' not in session:
            return redirect('/login')

        headers = {
            'Authorization': f"Bearer {session['access_token']}"
        }

        response = requests.get('https://api.spotify.com/v1/me', headers=headers)

        if response.status_code != 200:
            return {'error': 'Failed to fetch user data'}, 400

        user_data = response.json()
        session['user_id'] = user_data['id']  # Spotify user ID
    
    return session['user_id']

def check_token():
    if 'access_token' not in session or datetime.now().timestamp() > session['expires_at']:
        return refresh_token()
    return True

def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')
    
    req_body = {
        'grant_type': 'refresh_token',
        'refresh_token': session['refresh_token'],
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    response = requests.post(TOKEN_URL, data=req_body)
    new_token_info = response.json()
    session['access_token'] = new_token_info['access_token']
    session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']

    return True

################### YouTube (podprogrami) ################################

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

################### Spotify ################################

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    scope = 'playlist-read-collaborative playlist-read-private playlist-modify-private playlist-modify-public'
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True  # vedno se rabš logirat v Spotify (True) -- Lih obratn (False)
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        return jsonify({'error': request.args['error']})
    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()
        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']

        return redirect('/playlists')

@app.route('/playlists')
def get_playlists():
    if not check_token():
        return redirect('/login')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    response = requests.get(API_BASE_URL + 'me/playlists', headers=headers)

    data = response.json()

    user_id = get_user_id()

    existing_data = db_spotify.search(User.user_id == user_id)

    if existing_data:
        # Update new data
        db_spotify.update({'playlists_data': data}, User.user_id == user_id)
    else:
        # Insert new data
        db_spotify.insert({'user_id': user_id, 'playlists_data': data})

    playlists = [{'name': playlist['name'], 'id': playlist['id']} for playlist in data['items']]

    return render_template('playlists.html', playlists=playlists)

@app.route('/select_playlist')
def select_playlist():
    session['playlist_ID'] = request.args.get('playlist')
    return redirect('/songs')

@app.route('/songs')
def get_songs():
    if not check_token():
        return redirect('/login')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    # Gets playlist ID from TinyDB
    playlist_ID = session.get('playlist_ID')
    if not playlist_ID:
        return jsonify({'error': 'No playlist selected'}), 404

    # Page
    page = int(request.args.get('page', 1))
    page_size = 50
    offset = (page - 1) * page_size
    
    response = requests.get(API_BASE_URL + f'playlists/{playlist_ID}/tracks?offset={offset}&limit={page_size}', headers=headers)
    data = response.json()

    songs = [item['track']['name'] for item in data['items']]
    total_songs = data['total']
    
    return render_template('songs.html', songs=songs, page=page, total_songs=total_songs, page_size=page_size)

################### YouTube ################################

@app.route('/yt_login')
def yt_login():
    state = secrets.token_urlsafe(16)
    session['state'] = state

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(YT_SECRET_FILE, scopes=YT_SCOPES)
    flow.redirect_uri = YT_REDIRECT_URI

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=state,
        prompt='consent')
    
    return redirect(authorization_url)

@app.route('/yt_callback')
def yt_callback():
    state_stored = session['state']
    state_received = request.args.get('state')

    if state_received != state_stored:
        return 'State parameter does not match!', 400
    
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        YT_SECRET_FILE,
        scopes=YT_SCOPES
    )
    flow.redirect_uri = YT_REDIRECT_URI
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    session['yt_credentials'] = credentials_to_dict(credentials)

    return redirect('/yt')

@app.route('/yt')
def yt():
    return render_template('yt.html')

@app.route('/yt_playlists')
def yt_playlists():
    # Get YouTube credentials from the session
    credentials = session.get('yt_credentials')

    # Redirect to YouTube login if credentials are not found
    if not credentials:
        return redirect('/yt_login')
    
    # Build YouTube API service
    youtube = build(API_SERVICE_NAME, API_VERSION, credentials=google.oauth2.credentials.Credentials(**credentials))
    
    # Fetch the user's playlists
    try:
        playlists_response = youtube.playlists().list(
            part='snippet',  # You can include more parts like 'contentDetails' if needed
            mine=True,  # This specifies that we want the authenticated user's playlists
            maxResults=25  # Adjust this number if you want more playlists
        ).execute()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Extract playlist information
    playlists_data = playlists_response.get('items', [])
    
    if not playlists_data:
        return jsonify({'error': 'No playlists found'}), 404
    
    # Prepare playlist information to display
    playlists = [{
        'title': playlist['snippet']['title'],
        'id': playlist['id'],
        'thumbnail': playlist['snippet']['thumbnails']['default']['url'] if 'thumbnails' in playlist['snippet'] else None
    } for playlist in playlists_data]
    
    return render_template('yt_playlists.html', playlists=playlists)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)