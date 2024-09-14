#!/usr/bin/env python
# coding: utf-8

import spotipy
import requests
import os
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
from flask import Flask, send_file, abort

app = Flask(__name__)

# Initialize Spotify API client
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

if not all([SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI]):
    raise ValueError("Missing one or more environment variables for Spotify API credentials.")

# Spotify scope
scope = 'user-read-currently-playing'

# Initialize Spotify client
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope=scope))


# Get current track
def get_current_track():
    try:
        current_track = sp.currently_playing()
        if not current_track or not current_track.get('item'):
            print("No track currently playing.")
            return None
        return current_track['item']
    except Exception as e:
        print(f"Error fetching track: {e}")
        return None


# Helper function to create rounded corners for an image
def add_rounded_corners(image, radius):
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)
    image_with_corners = ImageOps.fit(image, image.size, centering=(0.5, 0.5))
    image_with_corners.putalpha(mask)
    return image_with_corners


# Helper function to calculate optimal font size for text
def calculate_font_size(draw, text, font, max_width):
    while True:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width or font.size <= 10:  # Limit min font size
            break
        font = ImageFont.truetype(font.path, font.size - 1)
    return font


# Create the image of the now playing track
def create_now_playing_image(track):
    if not track:
        return None

    # Get track details
    track_name = track['name']
    track_album = track['album']['name']
    artists = ', '.join([artist['name'] for artist in track['artists']])
    album_art_url = track['album']['images'][1]['url']
    release_year = track['album']['release_date'].split('-')[0]  # Extract year

    # Fetch the album artwork
    try:
        response = requests.get(album_art_url)
        response.raise_for_status() # Ensure we notice bad responses
        album_art = Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"Error fetching album art: {e}")
        return None

    # Create a canvas (adjusted for additional text)
    img = Image.new('RGB', (320, 84), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Paste the album art onto the canvas with rounded corners
    album_art = album_art.resize((64, 64))
    album_art_rounded = add_rounded_corners(album_art, radius=10)
    img.paste(album_art_rounded, (10, 10), album_art_rounded)

    # Load font (with fallback)
    try:
        font = ImageFont.truetype(r'font/NotoSansCJKjp-Regular.otf', 14)
    except IOError:
        font = ImageFont.load_default()

    # Adjust font size based on available space
    font = calculate_font_size(draw, track_name, font, max_width=220)

    # Draw track details on the canvas
    draw.text((90, 15), track_name, font=font, fill=(0, 0, 0))
    draw.text((90, 35), artists, font=font, fill=(0, 0, 0))
    draw.text((90, 55), f"{track_album} ({release_year})", font=font, fill=(0, 0, 0))

    # Save image to BytesIO object
    output = BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    return output


@app.route('/now_playing')
def now_playing_image():
    track = get_current_track()
    image_output = create_now_playing_image(track)
    if image_output:
        return send_file(image_output, mimetype='image/png', as_attachment=False, download_name='now_playing.png')
    else:
        abort(404, description="No track currently playing or error generating image")


if __name__ == '__main__':
    app.run(debug=False)
