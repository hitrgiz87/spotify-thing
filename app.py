from flask import Flask, redirect, request, session, url_for, jsonify
import requests
import base64
import os
import json
from urllib.parse import urlencode
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.urandom(24)

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = "http://localhost:5000/callback"
SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing"

def get_auth_url():
    auth_url = "https://accounts.spotify.com/authorize"
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE
    }
    return f"{auth_url}?{urlencode(params)}"

def get_token(code):
    token_url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    response = requests.post(token_url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()

def refresh_token(refresh_token):
    token_url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    response = requests.post(token_url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()

def save_token_info(token_info):
    session['token_info'] = token_info
    with open('token_info.json', 'w') as token_file:
        json.dump(token_info, token_file)

def load_token_info():
    if 'token_info' in session:
        return session['token_info']
    try:
        with open('token_info.json', 'r') as token_file:
            return json.load(token_file)
    except FileNotFoundError:
        return None

def ensure_token_validity(token_info):
    if 'expires_in' in token_info:
        expires_in = token_info['expires_in']
        if expires_in < 60:  # Refresh the token if it expires in less than a minute
            token_info = refresh_token(token_info['refresh_token'])
            save_token_info(token_info)
    return token_info

@app.route('/')
def login():
    return redirect(get_auth_url())

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = get_token(code)
    save_token_info(token_info)
    return redirect(url_for('index'))

@app.route('/index')
def index():
    token_info = load_token_info()
    if not token_info:
        return redirect(url_for('login'))

    token_info = ensure_token_validity(token_info)
    token = token_info['access_token']
    url = "https://api.spotify.com/v1/me/player/currently-playing"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("Currently Playing Data:", data)  # Debugging statement
        if data and data['is_playing']:
            return jsonify(data)
        else:
            return jsonify({"error": "No song is currently playing"})
    else:
        return jsonify({"error": response.json()}), response.status_code

@app.route('/play', methods=['PUT'])
def play():
    token_info = load_token_info()
    if not token_info:
        return redirect(url_for('login'))

    token_info = ensure_token_validity(token_info)
    token = token_info['access_token']
    url = "https://api.spotify.com/v1/me/player/play"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.put(url, headers=headers)
    if response.status_code == 204:
        return "Playback started", 204
    else:
        return jsonify({"error": response.json()}), response.status_code

@app.route('/pause', methods=['PUT'])
def pause():
    token_info = load_token_info()
    if not token_info:
        return redirect(url_for('login'))

    token_info = ensure_token_validity(token_info)
    token = token_info['access_token']
    url = "https://api.spotify.com/v1/me/player/pause"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.put(url, headers=headers)
    if response.status_code == 204:
        return "Playback paused", 204
    else:
        return jsonify({"error": response.json()}), response.status_code

@app.route('/next', methods=['PUT'])
def next():
    token_info = load_token_info()
    if not token_info:
        return redirect(url_for('login'))

    token_info = ensure_token_validity(token_info)
    token = token_info['access_token']
    url = "https://api.spotify.com/v1/me/player/next"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 204:
        return "Next track", 204
    else:
        return jsonify({"error": response.json()}), response.status_code

@app.route('/previous', methods=['PUT'])
def previous():
    token_info = load_token_info()
    if not token_info:
        return redirect(url_for('login'))

    token_info = ensure_token_validity(token_info)
    token = token_info['access_token']
    url = "https://api.spotify.com/v1/me/player/previous"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 204:
        return "Previous track", 204
    else:
        return jsonify({"error": response.json()}), response.status_code

def run_server():
    app.run()

if __name__ == "__main__":
    run_server()
