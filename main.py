import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
import re

load_dotenv()

# Spotify API credentials (Set these as environment variables or paste directly here)
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
USB_PATH = os.getenv("USB_PATH", "/Volumes/SANDISK 32")

# Set up Spotify API client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

if not os.path.exists(USB_PATH):
    raise FileNotFoundError(f"USB drive not found at {USB_PATH}. Please plug it in.")

def sanitize_filename(name):
    # Remove or replace invalid characters for filesystem
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def get_playlist_info(playlist_url):
    # Get playlist metadata including name
    playlist = sp.playlist(playlist_url)
    return playlist['name'], playlist['tracks']['items']

def get_all_playlist_tracks(playlist_id):
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return tracks

def search_youtube(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch1',
        'extract_flat': 'in_playlist'
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if 'entries' in info:
            return info['entries'][0]['url']
        return info['webpage_url']

def download_audio(youtube_url, output_path, title):
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio',
        'outtmpl': os.path.join(output_path, f'{title}.%(ext)s'),
        'quiet': False,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

def main():
    playlist_url = input("Enter Spotify playlist URL: ")
    print("Fetching playlist...")

    # Get playlist name and tracks
    playlist_name, _ = get_playlist_info(playlist_url)
    tracks = get_all_playlist_tracks(playlist_url)

    # Create folder using sanitized playlist name
    sanitized_playlist_name = sanitize_filename(playlist_name)
    playlist_folder = os.path.join(USB_PATH, sanitized_playlist_name)
    os.makedirs(playlist_folder, exist_ok=True)

    print(f"Saving tracks to: {playlist_folder}")

    # Get list of already downloaded mp3 filenames (without extension)
    downloaded_files = {
        os.path.splitext(f)[0]
        for f in os.listdir(playlist_folder)
        if f.endswith(".mp3")
    }

    for idx, item in enumerate(tracks):
        track = item['track']
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        clean_title = sanitize_filename(f"{artist_name} - {track_name}")

        if clean_title in downloaded_files:
            print(f"[{idx+1}/{len(tracks)}] Skipping already downloaded: {clean_title}")
            continue

        search_query = f"{track_name} {artist_name} audio"
        print(f"\n[{idx+1}/{len(tracks)}] Searching: {search_query}")

        try:
            youtube_url = search_youtube(search_query)
            print(f"Found YouTube URL: {youtube_url}")
            download_audio(youtube_url, playlist_folder, clean_title)
        except Exception as e:
            print(f"Failed to download {track_name}: {e}")


if __name__ == "__main__":
    main()
