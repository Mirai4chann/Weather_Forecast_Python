from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

# IMPORTANT: Replace with your actual OpenWeatherMap API key
API_KEY = "fcbbe5a62e6f93ecf2d8f759d77c26e9"
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

@app.route('/')
def index():
    """Renders the main page"""
    return render_template('index.html')

@app.route('/weather', methods=['POST'])
def get_weather():
    """API endpoint to fetch weather data"""
    try:
        data = request.get_json()
        city = data.get('city', '').strip()
        
        if not city:
            return jsonify({'error': 'Please enter a city name'}), 400
        
        # Make API request
        params = {
            'q': city,
            'appid': API_KEY,
            'units': 'metric'
        }
        
        response = requests.get(BASE_URL, params=params, timeout=10)
        
        if response.status_code == 200:
            weather_data = response.json()
            
            # Parse the data
            result = {
                'city': weather_data['name'],
                'country': weather_data['sys']['country'],
                'temperature': round(weather_data['main']['temp'], 1),
                'feels_like': round(weather_data['main']['feels_like'], 1),
                'temp_min': round(weather_data['main']['temp_min'], 1),
                'temp_max': round(weather_data['main']['temp_max'], 1),
                'humidity': weather_data['main']['humidity'],
                'pressure': weather_data['main']['pressure'],
                'wind_speed': weather_data['wind']['speed'],
                'description': weather_data['weather'][0]['description'].title(),
                'icon': weather_data['weather'][0]['icon'],
                'sunrise': datetime.fromtimestamp(weather_data['sys']['sunrise']).strftime('%H:%M'),
                'sunset': datetime.fromtimestamp(weather_data['sys']['sunset']).strftime('%H:%M')
            }
            
            return jsonify(result), 200
            
        elif response.status_code == 404:
            return jsonify({'error': 'City not found'}), 404
        elif response.status_code == 401:
            return jsonify({'error': 'Invalid API key. Please check your API key.'}), 401
        else:
            return jsonify({'error': f'API Error: {response.status_code}'}), response.status_code
            
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Connection error. Check your internet.'}), 500
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timed out. Try again.'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

if __name__ == '__main__':
    print("🌤️  Weather App is running!")
    print("📱 Open your browser and go to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)