import json
import os
import random
from typing import Counter
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import openai
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

# OpenAI API key

client = openai.OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)

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


def get_song_lyrics(track_name, artist_name):
    # This is a placeholder function. In a real-world scenario, you would use a lyrics API or web scraping to get the lyrics.
    # For this example, we'll return a dummy lyrics string.
    return f"This is a placeholder for the lyrics of {track_name} by {artist_name}."

def analyze_lyrics(lyrics, mood, activity):
    prompt = f"""
    Analyze the following song lyrics in the context of the given mood and activity:

    Lyrics: {lyrics}

    Mood: {mood}
    Activity: {activity}

    Please provide your analysis in JSON format with the following structure:
    {{
        "mood_score": <int between 0 and 10>,
        "relevance_score": <int between 0 and 10>,
        "summary": "<brief summary of the lyrics, max 50 words>",
        "mood_explanation": "<brief explanation of the mood score>",
        "relevance_explanation": "<brief explanation of the relevance score>"
    }}
    """

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that analyzes song lyrics and provides responses in JSON format."},
            {"role": "user", "content": prompt}
        ]
    )

    try:
        analysis = json.loads(response.choices[0].message.content)
        return analysis
    except json.JSONDecodeError:
        return {
            "mood_score": 0,
            "relevance_score": 0,
            "summary": "Error parsing ChatGPT response",
            "mood_explanation": "Error parsing ChatGPT response",
            "relevance_explanation": "Error parsing ChatGPT response"
        }

@app.route('/api/analyze-songs', methods=['POST'])
def analyze_songs():
    try:
        data = request.json
        
        # Validate input
        required_fields = ['genres', 'mood', 'activity']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Invalid input: missing required fields"}), 400

        genres = data['genres'][:5]  # Limit to top 5 genres
        mood = data['mood']
        activity = data['activity']

        # Get tracks for each genre
        all_tracks = []
        for genre in genres:
            results = spotify.search(q=f'genre:"{genre}"', type='track', limit=50)
            all_tracks.extend(results['tracks']['items'])

        # Shuffle and select 10 unique tracks
        random.shuffle(all_tracks)
        selected_tracks = []
        seen_tracks = set()
        for track in all_tracks:
            track_id = track['id']
            if track_id not in seen_tracks and len(selected_tracks) < 10:
                selected_tracks.append(track)
                seen_tracks.add(track_id)
            if len(selected_tracks) == 10:
                break

        # Analyze each track
        analyzed_tracks = []
        for track in selected_tracks:
            track_name = track['name']
            artist_name = track['artists'][0]['name']
            lyrics = get_song_lyrics(track_name, artist_name)
            analysis = analyze_lyrics(lyrics, mood, activity)

            analyzed_tracks.append({
                "track_name": track_name,
                "artist_name": artist_name,
                "spotify_url": track['external_urls']['spotify'],
                "mood_score": analysis['mood_score'],
                "relevance_score": analysis['relevance_score'],
                "summary": analysis['summary'],
                "mood_explanation": analysis['mood_explanation'],
                "relevance_explanation": analysis['relevance_explanation']
            })

        return jsonify(analyzed_tracks)

    except spotipy.SpotifyException as e:
        return jsonify({"error": f"Spotify API error: {str(e)}"}), 500
    except openai.error.OpenAIError as e:
        return jsonify({"error": f"OpenAI API error: {str(e)}"}), 500
    except KeyError as e:
        return jsonify({"error": f"Invalid input: missing key {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)