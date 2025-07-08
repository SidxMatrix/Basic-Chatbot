from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import json
import re
import time
import pytz
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend-backend communication

# API Keys - In production, use environment variables
GOOGLE_API_KEY = "AIzaSyC4pQ9dKjOpFHG1aeYJ85pD2nqiuZNAg4s"
SEARCH_ENGINE_ID = "e5c15a1a34e1f447a"
WEATHER_API_KEY = "0830bba3c93b255d0bcc6323c3ee5c2a"

# Store chat history (in production, use a database)
chat_history = []

def search_google(query):
    """Search Google using Custom Search API"""
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": GOOGLE_API_KEY,  
            "cx": SEARCH_ENGINE_ID, 
            "q": query,
            "num": 5
        }
        response = requests.get(url, params=params)
        data = json.loads(response.text)
        snippets = []
        
        if "items" in data:
            for item in data["items"]:
                # Remove dates from response
                snippet = re.sub(r'(\d{1,2}/\d{1,2}/\d{2,4})|(\d{4}-\d{1,2}-\d{1,2})|([A-Za-z]+\s\d{1,2},\s\d{4})', '', item["snippet"])
                snippets.append(snippet)

        if snippets:
            # Combine snippets into paragraph
            full_text = " ".join(snippets)
            sentences = re.split(r'(?<=[.!?])\s+', full_text)
            
            complete_response = []
            for sentence in sentences:
                if len(complete_response) < 10:  # Response up to 5 sentences
                    if sentence.endswith(('.', '!', '?')) and len(sentence.strip()) > 5:
                        complete_response.append(sentence.strip())

            return " ".join(complete_response) if complete_response else "Sorry, I couldn't find any matching results."
        else:
            return "Sorry, I couldn't find any matching results."
    except Exception as e:
        print(f"Search error: {e}")
        return "Sorry, something went wrong with the search."

def get_weather(city):
    """Get weather information for a city"""
    try:
        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": WEATHER_API_KEY,
            "units": "metric"
        }
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if data.get("cod") == 200:
            weather_description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            feels_like = data["main"]["feels_like"]
            wind_speed = data.get("wind", {}).get("speed", "N/A")
            
            return f"🌤️ Weather in {city}: {weather_description.title()}. Temperature: {temperature}°C (feels like {feels_like}°C). Humidity: {humidity}%. Wind: {wind_speed} m/s."
        else:
            return "Sorry, I couldn't fetch the weather information for that location."
    except Exception as e:
        print(f"Weather error: {e}")
        return "Sorry, something went wrong while fetching weather data."
        
def translate_text(text, target_language):
    """Translate text to target language"""
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": text,
            "langpair": f"en|{target_language}",
        }
        response = requests.get(url, params=params)
        if response.ok:
            result = response.json().get("responseData", {}).get("translatedText", "Translation error.")
            return f"🌐 Translation ({target_language}): {result}"
        else:
            return "Translation error."
    except Exception as e:
        print(f"Translation error: {e}")
        return "Sorry, something went wrong with the translation."

def get_time(city):
    """Get current time for a city"""
    try:
        # This requires the timezonefinder library
        # For simplicity, we'll use a basic implementation
        geocode_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={WEATHER_API_KEY}"
        response = requests.get(geocode_url)
        data = response.json()
        
        if data:
            # For demo purposes, return a simplified time response
            # In production, use timezonefinder library
            current_time = datetime.now()
            return f"🕒 Current time information for {city}: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (Note: This is server time. For accurate local time, please use a timezone service.)"
        else:
            return "Sorry, I couldn't find the city information."
    except Exception as e:
        print(f"Time error: {e}")
        return "Sorry, something went wrong while fetching time information."
        
def get_definition(word):
    """Get definition of a word"""
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url)
        data = response.json()
        
        if isinstance(data, list) and "meanings" in data[0]:
            meanings = data[0]["meanings"]
            definitions = []
            
            # Get phonetic if available
            phonetic = data[0].get("phonetic", "")
            phonetic_text = f" ({phonetic})" if phonetic else ""
            
            for meaning in meanings[:3]:  # Limit to 3 meanings
                part_of_speech = meaning.get("partOfSpeech", "Unknown")
                for definition in meaning["definitions"][:2]:  # Limit to 2 definitions per meaning
                    def_text = definition['definition']
                    example = definition.get('example', '')
                    example_text = f" Example: '{example}'" if example else ""
                    definitions.append(f"({part_of_speech}) {def_text}{example_text}")
            
            result = f"📖 Definition of '{word}'{phonetic_text}:\n" + "\n".join(definitions)
            return result
        else:
            return "Sorry, I couldn't find the definition for that word."
    except Exception as e:
        print(f"Definition error: {e}")
        return "Sorry, something went wrong while fetching the definition."

def process_command(query):
    """Process different types of commands"""
    # Custom responses
    custom_responses = {
        "hello": "Hello there! How can I assist you today? 🤖",
        "hi": "Hi! I'm here to help you with anything you need! 👋",
        "how are you": "I'm functioning perfectly, thank you for asking! 😊",
        "thank you": "You're welcome! Happy to help! 🙏",
        "thanks": "You're welcome! 😊",
        "goodbye": "Goodbye! Have a great day! 👋",
        "bye": "See you later! Take care! 🌟"
    }
    
    query_lower = query.lower()
    
    # Check for custom responses
    for command, response in custom_responses.items():
        if command in query_lower:
            return response
            
    # Check for specific command patterns
    if query_lower.startswith("time in"):
        city = query_lower.replace("time in", "").strip()
        return get_time(city)
            
    if query_lower.startswith("weather in"):
        city = query_lower.replace("weather in", "").strip()
        return get_weather(city)
        
    if query_lower.startswith("meaning of") or query_lower.startswith("define"):
        word = re.sub(r'^(meaning of|define)\s+', '', query_lower).strip()
        return get_definition(word)
    
    # Default to Google search
    return search_google(query)

# Routes
@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def api_search():
    """Handle search requests"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        result = process_command(query)
        
        # Store in history
        chat_history.append({
            'query': query,
            'response': result,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'response': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"API Search error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/translate', methods=['POST'])
def api_translate():
    """Handle translation requests"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        target_language = data.get('target_language', 'en')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        result = translate_text(text, target_language)
        
        return jsonify({
            'success': True,
            'response': result,
            'original_text': text,
            'target_language': target_language
        })
        
    except Exception as e:
        print(f"API Translation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/weather', methods=['POST'])
def api_weather():
    """Handle weather requests"""
    try:
        data = request.get_json()
        city = data.get('city', '').strip()
        
        if not city:
            return jsonify({'error': 'No city provided'}), 400
        
        result = get_weather(city)
        
        return jsonify({
            'success': True,
            'response': result,
            'city': city
        })
        
    except Exception as e:
        print(f"API Weather error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/definition', methods=['POST'])
def api_definition():
    """Handle definition requests"""
    try:
        data = request.get_json()
        word = data.get('word', '').strip()
        
        if not word:
            return jsonify({'error': 'No word provided'}), 400
        
        result = get_definition(word)
        
        return jsonify({
            'success': True,
            'response': result,
            'word': word
        })
        
    except Exception as e:
        print(f"API Definition error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/history', methods=['GET'])
def api_history():
    """Get chat history"""
    return jsonify({
        'success': True,
        'history': chat_history[-50:]  # Return last 50 entries
    })

@app.route('/api/clear_history', methods=['POST'])
def api_clear_history():
    """Clear chat history"""
    global chat_history
    chat_history = []
    return jsonify({'success': True, 'message': 'History cleared'})

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("🚀 Starting Rex AI Assistant Server...")
    print("📍 Server will be available at: http://localhost:5000")
    print("🔧 Make sure to install required packages: pip install flask flask-cors requests pytz")
    
    app.run(debug=True, host='0.0.0.0', port=5000)