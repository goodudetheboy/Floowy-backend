import os
import unittest
import json
from unittest.mock import MagicMock, patch
from app import app
import requests
import spotipy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TestMusicRecommendationAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_recommend_songs(self):
        # Test data
        test_songs = [
            {"song_name": "Happy", "mood_relevance_score": 8, "activity_relevance_score": 6, "personal_relevance_score": 7},
            {"song_name": "Sad", "mood_relevance_score": 3, "activity_relevance_score": 4, "personal_relevance_score": 2},
            {"song_name": "Energetic", "mood_relevance_score": 9, "activity_relevance_score": 8, "personal_relevance_score": 6},
            {"song_name": "Calm", "mood_relevance_score": 5, "activity_relevance_score": 3, "personal_relevance_score": 8},
            {"song_name": "Focused", "mood_relevance_score": 7, "activity_relevance_score": 9, "personal_relevance_score": 5},
            {"song_name": "Relaxed", "mood_relevance_score": 6, "activity_relevance_score": 2, "personal_relevance_score": 9},
            {"song_name": "Upbeat", "mood_relevance_score": 9, "activity_relevance_score": 7, "personal_relevance_score": 8}
        ]

        # Expected result (top 5 songs sorted by mood > personal_relevance > activity)
        expected_result = ["Upbeat", "Energetic", "Happy", "Focused", "Relaxed"]

        # Send POST request to the /api/recommend endpoint
        response = self.app.post('/api/recommend',
                                 data=json.dumps(test_songs),
                                 content_type='application/json')

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Check if the response data matches the expected result
        self.assertEqual(json.loads(response.data), expected_result)

    def test_empty_input(self):
        # Test with an empty list
        response = self.app.post('/api/recommend',
                                 data=json.dumps([]),
                                 content_type='application/json')

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Check if the response is an empty list
        self.assertEqual(json.loads(response.data), [])

    def test_missing_field(self):
        # Test with missing field
        invalid_data = [{"song_name": "Invalid", "mood_relevance_score": 5, "activity_relevance_score": 5}]
        response = self.app.post('/api/recommend',
                                 data=json.dumps(invalid_data),
                                 content_type='application/json')

        # Check if the response status code is 400 (Bad Request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("missing required fields", json.loads(response.data)["error"])

    def test_invalid_score_range(self):
        # Test with invalid score range
        invalid_data = [{"song_name": "Invalid", "mood_relevance_score": 11, "activity_relevance_score": 5, "personal_relevance_score": 5}]
        response = self.app.post('/api/recommend',
                                 data=json.dumps(invalid_data),
                                 content_type='application/json')

        # Check if the response status code is 400 (Bad Request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("must be between 0 and 10", json.loads(response.data)["error"])

    def test_invalid_input_type(self):
        # Test with invalid input type (not a list)
        invalid_data = {"song_name": "Invalid", "mood_relevance_score": 5, "activity_relevance_score": 5, "personal_relevance_score": 5}
        response = self.app.post('/api/recommend',
                                 data=json.dumps(invalid_data),
                                 content_type='application/json')

        # Check if the response status code is 400 (Bad Request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid input: missing required fields", json.loads(response.data)["error"])

    @patch('app.custom_generate_audio')
    def test_generate_song(self, mock_generate_audio):
        # Mock the API response
        mock_generate_audio.return_value = [{
            "0": {
                "id": "9578af8b-1acd-40de-b3a0-3b5f30aff23f",
                "audio_url": "https://audiopipe.suno.ai/?item_id=9578af8b-1acd-40de-b3a0-3b5f30aff23f"
            },
            "1": {
                "id": "351cfc17-7fa9-4a89-b133-750b4e67e885",
                "audio_url": "https://audiopipe.suno.ai/?item_id=351cfc17-7fa9-4a89-b133-750b4e67e885"
            }
        }]

        # Test data
        test_data = {
            "mood": "happy",
            "activity": "running",
            "personal_details": "Feeling energetic and motivated"
        }

        # Send POST request to the /api/generate-song endpoint
        response = self.app.post('/api/generate-song',
                                 data=json.dumps(test_data),
                                 content_type='application/json')

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Check if the response data contains ids and audio_urls for both songs
        response_data = json.loads(response.data)
        self.assertIn('id_0', response_data)
        self.assertIn('audio_url_0', response_data)
        self.assertIn('id_1', response_data)
        self.assertIn('audio_url_1', response_data)
        self.assertEqual(response_data['id_0'], '9578af8b-1acd-40de-b3a0-3b5f30aff23f')
        self.assertEqual(response_data['audio_url_0'], 'https://audiopipe.suno.ai/?item_id=9578af8b-1acd-40de-b3a0-3b5f30aff23f')
        self.assertEqual(response_data['id_1'], '351cfc17-7fa9-4a89-b133-750b4e67e885')
        self.assertEqual(response_data['audio_url_1'], 'https://audiopipe.suno.ai/?item_id=351cfc17-7fa9-4a89-b133-750b4e67e885')

    def test_generate_song_missing_fields(self):
        # Test with missing fields
        invalid_data = {"mood": "happy"}
        response = self.app.post('/api/generate-song',
                                 data=json.dumps(invalid_data),
                                 content_type='application/json')

        # Check if the response status code is 400 (Bad Request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("missing required fields", json.loads(response.data)["error"])

    @patch('app.custom_generate_audio')
    def test_generate_song_api_failure(self, mock_generate_audio):
        # Mock an API failure
        mock_generate_audio.side_effect = requests.RequestException("API request failed")

        # Test data
        test_data = {
            "mood": "sad",
            "activity": "resting",
            "personal_details": "Feeling under the weather"
        }

        # Send POST request to the /api/generate-song endpoint
        response = self.app.post('/api/generate-song',
                                 data=json.dumps(test_data),
                                 content_type='application/json')

        # Check if the response status code is 500 (Internal Server Error)
        self.assertEqual(response.status_code, 500)
        self.assertIn("API request failed", json.loads(response.data)["error"])
    @patch('app.spotify')
    def test_playlist_genres(self, mock_spotify):
        # Mock Spotify API responses
        mock_spotify.playlist_tracks.return_value = {
            'items': [
                {'track': {'artists': [{'id': 'artist1'}, {'id': 'artist2'}]}},
                {'track': {'artists': [{'id': 'artist3'}]}},
            ],
            'next': None
        }
        mock_spotify.artists.return_value = {
            'artists': [
                {'id': 'artist1', 'genres': ['pop', 'rock']},
                {'id': 'artist2', 'genres': ['rock', 'alternative']},
                {'id': 'artist3', 'genres': ['hip-hop', 'rap']},
            ]
        }

        # Test data
        test_data = {
            "playlist_url": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        }

        # Send POST request to the /api/playlist-genres endpoint
        response = self.app.post('/api/playlist-genres',
                                 data=json.dumps(test_data),
                                 content_type='application/json')

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Check if the response data contains the expected information
        response_data = json.loads(response.data)
        self.assertIn('playlist_id', response_data)
        self.assertIn('total_tracks', response_data)
        self.assertIn('genres', response_data)
        self.assertEqual(response_data['playlist_id'], '37i9dQZF1DXcBWIGoYBM5M')
        self.assertEqual(response_data['total_tracks'], 2)
        self.assertEqual(response_data['genres'], {'rock': 2, 'pop': 1, 'alternative': 1, 'hip-hop': 1, 'rap': 1})
        
        # Check if the number of genres is at most 10
        self.assertLessEqual(len(response_data['genres']), 10)

    def test_playlist_genres_missing_url(self):
        # Test with missing playlist URL
        invalid_data = {}
        response = self.app.post('/api/playlist-genres',
                                 data=json.dumps(invalid_data),
                                 content_type='application/json')

        # Check if the response status code is 400 (Bad Request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("missing playlist_url", json.loads(response.data)["error"])

    @patch('app.spotify')
    def test_playlist_genres_spotify_error(self, mock_spotify):
        # Mock a Spotify API error
        mock_spotify.playlist_tracks.side_effect = spotipy.SpotifyException(400, -1, "Invalid playlist")

        # Test data
        test_data = {
            "playlist_url": "https://open.spotify.com/playlist/invalid"
        }

        # Send POST request to the /api/playlist-genres endpoint
        response = self.app.post('/api/playlist-genres',
                                 data=json.dumps(test_data),
                                 content_type='application/json')

        # Check if the response status code is 500 (Internal Server Error)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Spotify API error", json.loads(response.data)["error"])

    def test_playlist_genres_real_api(self):
        # Ensure Spotify credentials are set
        if not os.getenv('SPOTIFY_CLIENT_ID') or not os.getenv('SPOTIFY_CLIENT_SECRET'):
            self.skipTest("Spotify credentials not set in .env file")

        # Test data
        test_data = {
            "playlist_url": "https://open.spotify.com/playlist/37i9dQZF1DXdPec7aLTmlC"
        }

        # Send POST request to the /api/playlist-genres endpoint
        response = self.app.post('/api/playlist-genres',
                                 data=json.dumps(test_data),
                                 content_type='application/json')

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Check if the response data contains the expected information
        response_data = json.loads(response.data)
        self.assertIn('playlist_id', response_data)
        self.assertIn('total_tracks', response_data)
        self.assertIn('genres', response_data)
        self.assertEqual(response_data['playlist_id'], '37i9dQZF1DXdPec7aLTmlC')
        
        # Check if the total_tracks is greater than 0
        self.assertGreater(response_data['total_tracks'], 0)
        
        # Check if genres is not empty and has at most 10 genres
        self.assertGreater(len(response_data['genres']), 0)
        self.assertLessEqual(len(response_data['genres']), 10)
        
        # Print out the genres for manual verification
        print("\nGenres found in the playlist:")
        for genre, count in response_data['genres'].items():
            print(f"{genre}: {count}")

    @patch('app.spotify')
    @patch('app.get_song_lyrics')
    @patch('app.openai.ChatCompletion.create')
    def test_analyze_songs(self, mock_openai, mock_get_lyrics, mock_spotify):
        # Mock Spotify API response
        mock_spotify.search.return_value = {
            'tracks': {
                'items': [
                    {
                        'id': 'track1',
                        'name': 'Song 1',
                        'artists': [{'name': 'Artist 1'}],
                        'external_urls': {'spotify': 'https://open.spotify.com/track/1'}
                    },
                    {
                        'id': 'track2',
                        'name': 'Song 2',
                        'artists': [{'name': 'Artist 2'}],
                        'external_urls': {'spotify': 'https://open.spotify.com/track/2'}
                    }
                ]
            }
        }

        # Mock lyrics retrieval
        mock_get_lyrics.return_value = "Mock lyrics"

        # Mock OpenAI API response
        mock_openai.return_value = MagicMock(
            choices=[MagicMock(message={'content': json.dumps({
                'mood_relevance_score': 8,
                'activity_relevance_score': 7,
                'personal_relevance_score': 6,
                'summary': 'This is a mock summary.',
                'mood_explanation': 'This is a mock mood explanation.',
                'activity_explanation': 'This is a mock activity explanation.',
                'personal_explanation': 'This is a mock personal explanation.'
            })})]
        )

        # Test data
        test_data = {
            "genres": ["pop", "rock"],
            "mood": "happy",
            "activity": "running",
            "personal_status": "feeling motivated"
        }

        # Send POST request to the /api/analyze-songs endpoint
        response = self.app.post('/api/analyze-songs',
                                 data=json.dumps(test_data),
                                 content_type='application/json')

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Check if the response data contains the expected information
        response_data = json.loads(response.data)
        self.assertEqual(len(response_data), 2)  # We expect 2 tracks in this test case
        for track in response_data:
            self.assertIn('track_name', track)
            self.assertIn('artist_name', track)
            self.assertIn('spotify_url', track)
            self.assertIn('mood_relevance_score', track)
            self.assertIn('activity_relevance_score', track)
            self.assertIn('personal_relevance_score', track)
            self.assertIn('summary', track)
            self.assertIn('mood_explanation', track)
            self.assertIn('activity_explanation', track)
            self.assertIn('personal_explanation', track)

            # Check if all scores are integers between 0 and 10
            for score_field in ['mood_relevance_score', 'activity_relevance_score', 'personal_relevance_score']:
                self.assertIsInstance(track[score_field], int)
                self.assertTrue(0 <= track[score_field] <= 10)

            # Check if spotify_url is a valid Spotify track URL
            self.assertTrue(track['spotify_url'].startswith('https://open.spotify.com/track/'))

            # Check if summary and all explanations are non-empty strings
            for text_field in ['summary', 'mood_explanation', 'activity_explanation', 'personal_explanation']:
                self.assertIsInstance(track[text_field], str)
                self.assertTrue(len(track[text_field]) > 0)

    def test_analyze_songs_missing_fields(self):
        # Test with missing fields
        invalid_data = {"genres": ["pop"]}
        response = self.app.post('/api/analyze-songs',
                                 data=json.dumps(invalid_data),
                                 content_type='application/json')

        # Check if the response status code is 400 (Bad Request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("missing required fields", json.loads(response.data)["error"])

    @patch('app.spotify')
    def test_analyze_songs_spotify_error(self, mock_spotify):
        # Mock a Spotify API error
        mock_spotify.search.side_effect = spotipy.SpotifyException(400, -1, "Invalid search")

        # Test data
        test_data = {
            "genres": ["invalid_genre"],
            "mood": "happy",
            "activity": "running",
            "personal_status": "feeling good"
        }

        # Send POST request to the /api/analyze-songs endpoint
        response = self.app.post('/api/analyze-songs',
                                 data=json.dumps(test_data),
                                 content_type='application/json')

        # Check if the response status code is 500 (Internal Server Error)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Spotify API error", json.loads(response.data)["error"])
    @unittest.skip("Only needed when debugging")
    def test_analyze_songs_real(self):
        # Test data
        test_data = {
            "genres": ["pop", "rock", "hip-hop", "electronic", "r&b"],
            "mood": "energetic",
            "activity": "workout",
            "personal_status": "feeling motivated and ready to push limits"
        }

        # Send POST request to the /api/analyze-songs endpoint
        response = self.app.post('/api/analyze-songs',
                                 data=json.dumps(test_data),
                                 content_type='application/json')

        # Check if the response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Parse the response data
        response_data = json.loads(response.data)

        # Check if we got 10 tracks
        self.assertEqual(len(response_data), 10)

        # Check the structure of each track in the response
        for track in response_data:
            self.assertIn('track_name', track)
            self.assertIn('artist_name', track)
            self.assertIn('spotify_url', track)
            self.assertIn('mood_relevance_score', track)
            self.assertIn('activity_relevance_score', track)
            self.assertIn('personal_relevance_score', track)
            self.assertIn('summary', track)
            self.assertIn('mood_explanation', track)
            self.assertIn('activity_explanation', track)
            self.assertIn('personal_explanation', track)

            # Check if all scores are integers between 0 and 10
            for score_field in ['mood_relevance_score', 'activity_relevance_score', 'personal_relevance_score']:
                self.assertIsInstance(track[score_field], int)
                self.assertTrue(0 <= track[score_field] <= 10)

            # Check if spotify_url is a valid Spotify track URL
            self.assertTrue(track['spotify_url'].startswith('https://open.spotify.com/track/'))

            # Check if summary and all explanations are non-empty strings
            for text_field in ['summary', 'mood_explanation', 'activity_explanation', 'personal_explanation']:
                self.assertIsInstance(track[text_field], str)
                self.assertTrue(len(track[text_field]) > 0)

        print("Response data:")
        print(json.dumps(response_data, indent=2))

if __name__ == '__main__':
    unittest.main()