import requests
import json
from tkinter import *
from urllib.request import urlopen
from PIL import Image, ImageTk
import threading
from requests import get, put
from app import run_server
import base64
import time
from dotenv import load_dotenv
import os

root = Tk()

current_track_id = None

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

def search_artist(token, artist):
    url = f"https://api.spotify.com/v1/search?q={artist}&type=artist"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    result = get(url, headers=headers)
    json_result = json.loads(result.content)["artists"]["items"]
    if not json_result:
        print("No artist found")
        return None
    return json_result[0]

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
    new_token_info = response.json()
    new_token_info['expires_at'] = int(time.time()) + new_token_info['expires_in']
    return new_token_info

def ensure_token_validity(token_info):
    expires_at = token_info.get('expires_at', 0)
    if expires_at - int(time.time()) < 60:  # Refresh the token if it expires in less than a minute
        refreshed_token_info = refresh_token(token_info['refresh_token'])
        save_token_info(refreshed_token_info)
        return refreshed_token_info
    return token_info

def save_token_info(token_info):
    with open('token_info.json', 'w') as token_file:
        json.dump(token_info, token_file)

def load_token_info():
    try:
        with open('token_info.json', 'r') as token_file:
            return json.load(token_file)
    except FileNotFoundError:
        return None


def display_currently_playing():
    global current_track_id, progress_label

    token_info = load_token_info()
    if not token_info:
        print("Token info not found. Please login again.")
        return

    token_info = ensure_token_validity(token_info)
    token = token_info['access_token']
    url = "http://localhost:5000/index"

    try:
        response = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        data = response.json()

        if 'error' in data:
            print(data['error'])
            for widget in root.winfo_children():
                widget.destroy()
            no_song_label = Label(root, text="No song is currently playing", bg="black", fg="white", font=("Helvetica", 16))
            no_song_label.pack(pady=20)
            play_button = Button(root, text="Play", command=play_music, bg="black", fg="white")
            play_button.pack(pady=10)
            refresh_button = Button(root, text="Refresh", command=display_currently_playing, bg="black", fg="white")
            refresh_button.pack(pady=10)
            return

        new_track_id = data['item']['id']
        if current_track_id != new_track_id:
            current_track_id = new_track_id

            # Clear existing widgets
            for widget in root.winfo_children():
                widget.destroy()

            artist_name = data['item']['artists'][0]['name']
            song_name = data['item']['name']
            img_url = data['item']['album']['images'][0]['url'] if data['item']['album']['images'] else None

            if img_url:
                img = Image.open(urlopen(img_url))
                img = img.resize((300, 300))
                img = ImageTk.PhotoImage(img)

                img_label = Label(root, image=img, bg="black")
                img_label.image = img  # Keep a reference to avoid garbage collection
                img_label.pack(pady=20)

                artist_label = Label(root, text=artist_name, bg="black", fg="white", font=("Helvetica", 24))
                artist_label.pack(pady=10)

                song_label = Label(root, text=song_name, bg="black", fg="white", font=("Helvetica", 16))
                song_label.pack(pady=10)

                button_frame = Frame(root, bg="black")
                button_frame.pack(pady=10)

                play_button = Button(button_frame, text="Play", command=play_music, bg="black", fg="white")
                play_button.pack(side="left", padx=5)

                pause_button = Button(button_frame, text="Pause", command=pause_music, bg="black", fg="white")
                pause_button.pack(side="left", padx=5)

                next_button = Button(button_frame, text="Next", command=next_song, bg="black", fg="white")
                next_button.pack(side="left", padx=5)

                previous_button = Button(button_frame, text="Previous", command=previous_song, bg="black", fg="white")
                previous_button.pack(side="left", padx=5)

                refresh_button = Button(root, text="Refresh", command=display_currently_playing, bg="black", fg="white")
                refresh_button.pack(pady=10)


        if not data['is_playing']:
            no_song_label = Label(root, text="Playback paused", bg="black", fg="white", font=("Helvetica", 16))
            no_song_label.pack(pady=20)

    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
    except json.decoder.JSONDecodeError as e:
        print("JSON decoding error:", e)

def get_songs_by_artist(token, artist_id):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=US"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    result = get(url, headers=headers)
    json_result = json.loads(result.content)
    return json_result["tracks"]

def display_album(artist_name, img_url):
    for widget in root.winfo_children():
        widget.destroy()

    img = Image.open(urlopen(img_url))
    img = img.resize((300, 300))
    img = ImageTk.PhotoImage(img)

    img_label = Label(root, image=img, bg="black")
    img_label.image = img  # Keep a reference to avoid garbage collection
    img_label.pack(pady=20)

    name_label = Label(root, text=artist_name, bg="black", fg="white", font=("Helvetica", 24))
    name_label.pack(pady=10)

    button_frame = Frame(root, bg="black")
    button_frame.pack(pady=10)

    play_button = Button(button_frame, text="Play", command=play_music, bg="black", fg="white")
    play_button.pack(side="left", padx=5)

    pause_button = Button(button_frame, text="Pause", command=pause_music, bg="black", fg="white")
    pause_button.pack(side="left", padx=5)

    next_button = Button(button_frame, text="Next", command=next_song, bg="black", fg="white")
    next_button.pack(side="left", padx=5)

    previous_button = Button(button_frame, text="Previous", command=previous_song, bg="black", fg="white")
    previous_button.pack(side="left", padx=5)

    refresh_button = Button(root, text="Refresh", command=display_currently_playing, bg="black", fg="white")
    refresh_button.pack(pady=10)

def play_music():
    token_info = ensure_token_validity(load_token_info())
    put('http://127.0.0.1:5000/play', headers={"Authorization": f"Bearer {token_info['access_token']}"})

def pause_music():
    token_info = ensure_token_validity(load_token_info())
    put('http://127.0.0.1:5000/pause', headers={"Authorization": f"Bearer {token_info['access_token']}"})

def next_song():
    token_info = ensure_token_validity(load_token_info())
    put('http://127.0.0.1:5000/next', headers={"Authorization": f"Bearer {token_info['access_token']}"})
    display_currently_playing()

def previous_song():
    token_info = ensure_token_validity(load_token_info())
    put('http://127.0.0.1:5000/previous', headers={"Authorization": f"Bearer {token_info['access_token']}"})
    display_currently_playing()

if __name__ == "__main__":
    threading.Thread(target=run_server).start()
    root.title("Spotify Player")
    root.geometry("800x600")
    root.config(bg="black")
    display_currently_playing()
    root.mainloop()
