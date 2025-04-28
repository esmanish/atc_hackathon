from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import json
import requests
from datetime import datetime
import os
from database import Database
from data_processor import DataProcessor
from challenge_manager import ChallengeManager

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production

# Initialize components
db = Database('teams.db')
data_processor = DataProcessor()
challenge_manager = ChallengeManager(db)

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

FLIGHT_FEEDER_IP = config.get('flight_feeder_ip', '192.168.31.123')

@app.route('/')
def index():
    if 'team_name' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        team_name = request.form.get('team_name')
        if team_name:
            # Register team if not exists
            if not db.team_exists(team_name):
                db.add_team(team_name)
            
            session['team_name'] = team_name
            return redirect(url_for('dashboard'))
    
    return render_template('login.html')

# Update the dashboard route in server.py to pass the config to the template

@app.route('/dashboard')
def dashboard():
    if 'team_name' not in session:
        return redirect(url_for('login'))
    
    team_name = session['team_name']
    team_score = db.get_team_score(team_name)
    current_challenge = challenge_manager.get_current_challenge()
    
    # Pass the config to the template
    return render_template('dashboard.html', 
                          team_name=team_name, 
                          team_score=team_score,
                          current_challenge=current_challenge,
                          map_config=config.get('map_settings', {}))

@app.route('/scoreboard')
def scoreboard():
    teams = db.get_all_teams()
    current_challenge = challenge_manager.get_current_challenge()
    return render_template('scoreboard.html', teams=teams, current_challenge=current_challenge)

@app.route('/api/aircraft')
def get_aircraft_data():
    """API endpoint to get aircraft data for the client"""
    try:
        # Get data from FlightAware or cached data
        aircraft_data = data_processor.get_aircraft_data(FLIGHT_FEEDER_IP)
        return jsonify(aircraft_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/submit_answer', methods=['POST'])
def submit_answer():
    """API endpoint for teams to submit challenge answers"""
    if 'team_name' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    team_name = session['team_name']
    data = request.json
    challenge_id = data.get('challenge_id')
    answer = data.get('answer')
    
    result = challenge_manager.check_answer(team_name, challenge_id, answer)
    return jsonify(result)

@app.route('/logout')
def logout():
    session.pop('team_name', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Ensure the database is initialized
    db.initialize()
    # Start the Flask application
    app.run(host='0.0.0.0', port=5000, debug=True)