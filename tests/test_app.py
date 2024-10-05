import unittest
import json
from app import app

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

    def test_invalid_input(self):
        # Test with invalid input (missing required fields)
        invalid_data = [{"song_name": "Invalid"}]
        response = self.app.post('/api/recommend',
                                 data=json.dumps(invalid_data),
                                 content_type='application/json')

        # Check if the response status code is 400 (Bad Request)
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()