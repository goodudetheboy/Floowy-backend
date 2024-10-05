from flask import Flask, request, jsonify

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True)