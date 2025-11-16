from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# IMPORTANT: Replace with your actual OpenWeatherMap API key
API_KEY = "fcbbe5a62e6f93ecf2d8f759d77c26e9"
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast"

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
        
        params = {
            'q': city,
            'appid': API_KEY,
            'units': 'metric'
        }
        
        response = requests.get(BASE_URL, params=params, timeout=10)
        
        if response.status_code != 200:
            return jsonify({'error': 'City not found'}), 404
        
        weather_data = response.json()
        
        result = {
            'city': weather_data['name'],
            'country': weather_data['sys']['country'],
            'temperature': weather_data['main']['temp'],
            'feels_like': weather_data['main']['feels_like'],
            'humidity': weather_data['main']['humidity'],
            'pressure': weather_data['main']['pressure'],
            'temp_min': weather_data['main']['temp_min'],
            'temp_max': weather_data['main']['temp_max'],
            'wind_speed': weather_data['wind']['speed'],
            'description': weather_data['weather'][0]['description'],
            'icon': weather_data['weather'][0]['icon'],
            'lat': weather_data['coord']['lat'],
            'lon': weather_data['coord']['lon'],
            'sunrise': datetime.fromtimestamp(weather_data['sys']['sunrise']).strftime('%H:%M'),
            'sunset': datetime.fromtimestamp(weather_data['sys']['sunset']).strftime('%H:%M')
        }
        
        return jsonify(result), 200
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Connection error. Please try again.'}), 500
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout. Please try again.'}), 500
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/predict-weather', methods=['POST'])
def predict_weather():
    """API endpoint to predict weather for next days"""
    try:
        data = request.get_json()
        city = data.get('city', '').strip()
        days = data.get('days', 5)
        
        if not city:
            return jsonify({'error': 'Please enter a city name'}), 400
        
        # Get forecast data
        params = {
            'q': city,
            'appid': API_KEY,
            'units': 'metric'
        }
        
        response = requests.get(FORECAST_URL, params=params, timeout=10)
        
        if response.status_code != 200:
            return jsonify({'error': 'City not found'}), 404
        
        forecast_data = response.json()
        
        # Process forecast data
        forecast_dict = {}
        for item in forecast_data['list']:
            date = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
            
            if date not in forecast_dict:
                forecast_dict[date] = {
                    'temps': [],
                    'condition': item['weather'][0]['description']
                }
            
            forecast_dict[date]['temps'].append(item['main']['temp'])
        
        # Build forecast list (limit to requested days)
        forecast = []
        for i, (date, data_point) in enumerate(list(forecast_dict.items())[:days]):
            temps = data_point['temps']
            forecast.append({
                'date': datetime.strptime(date, '%Y-%m-%d').strftime('%a, %b %d'),
                'avg_temp': round(sum(temps) / len(temps), 1),
                'max_temp': round(max(temps), 1),
                'min_temp': round(min(temps), 1),
                'condition': data_point['condition']
            })
        
        result = {
            'city': forecast_data['city']['name'],
            'country': forecast_data['city']['country'],
            'forecast': forecast
        }
        
        return jsonify(result), 200
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Connection error. Please try again.'}), 500
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout. Please try again.'}), 500
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/predict')
def predict():
    """Renders the predict page"""
    return render_template('predict.html')

if __name__ == '__main__':
    print("🌤️  Weather App is running!")
    print("📱 Open your browser and go to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)