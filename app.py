import os
from typing import Counter
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Load environment variables
load_dotenv()

app = Flask(__name__)

base_url = 'https://suno-api-1-ruby.vercel.app'

# Spotify API credentials
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Initialize Spotify client
spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

def custom_generate_audio(payload):
    url = f"{base_url}/api/custom_generate"
    response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
    return response.json()

@app.route('/api/recommend', methods=['POST'])
def recommend_songs():
    try:
        # Get the list of songs from the request
        songs = request.json

        if not songs:
            return jsonify([])

        # Validate input data
        for song in songs:
            required_fields = ['song_name', 'mood_relevance_score', 'activity_relevance_score', 'personal_relevance_score']
            if not all(field in song for field in required_fields):
                return jsonify({"error": "Invalid input: missing required fields"}), 400

            # Validate score ranges
            for score_field in ['mood_relevance_score', 'activity_relevance_score', 'personal_relevance_score']:
                if not 0 <= song[score_field] <= 10:
                    return jsonify({"error": f"Invalid input: {score_field} must be between 0 and 10"}), 400

        # Sort the songs based on the criteria: mood > personal_relevance > activity
        sorted_songs = sorted(
            songs,
            key=lambda x: (
                x['mood_relevance_score'],
                x['personal_relevance_score'],
                x['activity_relevance_score']
            ),
            reverse=True
        )

        # Get the top 5 songs
        top_5_songs = sorted_songs[:5]

        # Extract only the song names for the response
        recommended_songs = [song['song_name'] for song in top_5_songs]

        return jsonify(recommended_songs)

    except KeyError as e:
        return jsonify({"error": f"Invalid input: missing key {str(e)}"}), 400
    except TypeError:
        return jsonify({"error": "Invalid input: expected a list of dictionaries"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/generate-song', methods=['POST'])
def generate_song():
    try:
        data = request.json
        
        # Validate input
        required_fields = ['mood', 'activity', 'personal_details']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Invalid input: missing required fields"}), 400

        # Extract data
        mood = data['mood']
        activity = data['activity']
        personal_details = data['personal_details']

        # Compile prompt
        prompt = f"A song that captures the mood of {mood}, while doing {activity}. {personal_details}"

        # Generate song
        payload = {
            "prompt": prompt,
            "make_instrumental": False,
            "wait_audio": False
        }
        
        response = custom_generate_audio(payload)

        # Extract relevant information
        if response and len(response) > 0:
            song_data_0 = response[0].get('0', {})
            song_data_1 = response[0].get('1', {})
            
            return jsonify({
                "id_0": song_data_0.get('id', ''),
                "audio_url_0": song_data_0.get('audio_url', ''),
                "id_1": song_data_1.get('id', ''),
                "audio_url_1": song_data_1.get('audio_url', '')
            })
        else:
            return jsonify({"error": "Failed to generate song"}), 500

    except KeyError as e:
        return jsonify({"error": f"Invalid input: missing key {str(e)}"}), 400
    except requests.RequestException as e:
        return jsonify({"error": f"API request failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/playlist-genres', methods=['POST'])
def playlist_genres():
    try:
        data = request.json
        
        # Validate input
        if 'playlist_url' not in data:
            return jsonify({"error": "Invalid input: missing playlist_url"}), 400

        playlist_url = data['playlist_url']
        
        # Extract playlist ID from URL
        playlist_id = playlist_url.split('/')[-1].split('?')[0]

        # Get playlist tracks
        results = spotify.playlist_tracks(playlist_id)
        tracks = results['items']

        # Get more tracks if the playlist has more than 100 songs
        while results['next']:
            results = spotify.next(results)
            tracks.extend(results['items'])

        # Extract artist IDs
        artist_ids = set()
        for track in tracks:
            for artist in track['track']['artists']:
                artist_ids.add(artist['id'])

        # Get genres for all artists
        all_genres = []
        for i in range(0, len(artist_ids), 50):
            artists = spotify.artists(list(artist_ids)[i:i+50])
            for artist in artists['artists']:
                all_genres.extend(artist['genres'])

        # Count genre occurrences
        genre_counts = Counter(all_genres)

        # Sort genres by count and get the top 10
        top_10_genres = dict(sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:10])

        return jsonify({
            "playlist_id": playlist_id,
            "total_tracks": len(tracks),
            "genres": top_10_genres
        })

    except spotipy.SpotifyException as e:
        return jsonify({"error": f"Spotify API error: {str(e)}"}), 500
    except KeyError as e:
        return jsonify({"error": f"Invalid input: missing key {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
if __name__ == '__main__':
    app.run(debug=True)