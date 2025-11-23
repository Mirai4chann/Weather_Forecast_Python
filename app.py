from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime, timedelta
import os
from pymongo import MongoClient, ASCENDING, DESCENDING

app = Flask(__name__)

# MongoDB setup (use env var; fallback to your Atlas string for local testing)
MONGO_URI = os.environ.get(
    'MONGO_URI',
    'mongodb+srv://yatogod22_db_user:cawiDwDdV1le1xEP@cluster0.rh6mdxp.mongodb.net/?retryWrites=true&w=majority'
)
mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

# quick ping to verify connection at startup (logs error but app keeps running)
try:
    mongo_client.admin.command('ping')
    db = mongo_client.get_database('weather_app')
    searches_col = db.get_collection('searches')
    # ensure useful indexes
    searches_col.create_index([('city', ASCENDING), ('retrieved_at', DESCENDING)])
    searches_col.create_index([('retrieved_at', DESCENDING)])
    app.logger.info("✅ MongoDB connected")
except Exception as e:
    searches_col = None
    app.logger.error(f"❌ MongoDB connection failed: {e}")

# IMPORTANT: use env var for OpenWeatherMap API key (fallback kept for local dev)
API_KEY = os.environ.get('OPENWEATHER_API_KEY', 'fcbbe5a62e6f93ecf2d8f759d77c26e9')
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
            'country': weather_data['sys'].get('country'),
            'temperature': weather_data['main']['temp'],
            'feels_like': weather_data['main']['feels_like'],
            'humidity': weather_data['main']['humidity'],
            'pressure': weather_data['main']['pressure'],
            'temp_min': weather_data['main']['temp_min'],
            'temp_max': weather_data['main']['temp_max'],
            'wind_speed': weather_data['wind'].get('speed'),
            'description': weather_data['weather'][0].get('description'),
            'icon': weather_data['weather'][0].get('icon'),
            'lat': weather_data['coord'].get('lat'),
            'lon': weather_data['coord'].get('lon'),
            'sunrise': datetime.fromtimestamp(weather_data['sys']['sunrise']).strftime('%H:%M') if weather_data['sys'].get('sunrise') else None,
            'sunset': datetime.fromtimestamp(weather_data['sys']['sunset']).strftime('%H:%M') if weather_data['sys'].get('sunset') else None
        }

        # Save to MongoDB (non-blocking pattern not required for small apps)
        try:
            doc = {
                'city': result['city'],
                'country': result['country'],
                'temperature': result['temperature'],
                'feels_like': result['feels_like'],
                'humidity': result['humidity'],
                'pressure': result['pressure'],
                'temp_min': result['temp_min'],
                'temp_max': result['temp_max'],
                'wind_speed': result['wind_speed'],
                'description': result['description'],
                'icon': result['icon'],
                'lat': result['lat'],
                'lon': result['lon'],
                'sunrise': result['sunrise'],
                'sunset': result['sunset'],
                'source': 'openweathermap',
                'retrieved_at': datetime.utcnow(),
                # 'raw': weather_data  # optional: store raw payload if desired
            }
            searches_col.insert_one(doc)
        except Exception as db_err:
            app.logger.error(f"MongoDB insert failed: {db_err}")
        
        return jsonify(result), 200
        
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Connection error. Please try again.'}), 500
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout. Please try again.'}), 500
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

# New endpoint to retrieve history
@app.route('/history', methods=['GET'])
def get_history():
    """Return saved search history. Query params: city (optional), limit (optional)"""
    try:
        city = request.args.get('city')
        limit = int(request.args.get('limit', 50))
        query = {}
        if city:
            query['city'] = city

        cursor = searches_col.find(query).sort('retrieved_at', DESCENDING).limit(limit)
        results = []
        for d in cursor:
            results.append({
                'id': str(d.get('_id')),
                'city': d.get('city'),
                'country': d.get('country'),
                'temperature': d.get('temperature'),
                'feels_like': d.get('feels_like'),
                'humidity': d.get('humidity'),
                'pressure': d.get('pressure'),
                'temp_min': d.get('temp_min'),
                'temp_max': d.get('temp_max'),
                'wind_speed': d.get('wind_speed'),
                'description': d.get('description'),
                'icon': d.get('icon'),
                'lat': d.get('lat'),
                'lon': d.get('lon'),
                'sunrise': d.get('sunrise'),
                'sunset': d.get('sunset'),
                'retrieved_at': d.get('retrieved_at').isoformat() if d.get('retrieved_at') else None
            })
        return jsonify({'history': results}), 200
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