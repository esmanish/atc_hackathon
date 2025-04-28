import sqlite3
import os
import json
from datetime import datetime

class Database:
    def __init__(self, db_file):
        """Initialize the database connection"""
        self.db_file = db_file
        self.conn = None
        
    def initialize(self):
        """Create the necessary tables if they don't exist"""
        self.conn = sqlite3.connect(self.db_file)
        cursor = self.conn.cursor()
        
        # Create teams table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create challenges table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            phase INTEGER NOT NULL,
            points INTEGER NOT NULL,
            correct_answer TEXT
        )
        ''')
        
        # Create submissions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            challenge_id INTEGER NOT NULL,
            answer TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            points_awarded INTEGER NOT NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (id),
            FOREIGN KEY (challenge_id) REFERENCES challenges (id)
        )
        ''')
        
        # Insert some sample challenges if none exist
        cursor.execute("SELECT COUNT(*) FROM challenges")
        if cursor.fetchone()[0] == 0:
            sample_challenges = [
                (1, "Identify Aircraft Type", "Identify the aircraft type of flight with callsign 'SVA783'", 1, 100, "Boeing 777"),
                (2, "Calculate Closest Approach", "Calculate the minimum distance between OMA223 and AXB744", 2, 150, None),
                (3, "Predict Landing Time", "Predict the landing time for flight IGO2173 based on current trajectory", 2, 200, None),
                (4, "Emergency Response", "Provide optimal route for emergency aircraft to land at nearest airport", 3, 250, None)
            ]
            cursor.executemany("INSERT INTO challenges (id, title, description, phase, points, correct_answer) VALUES (?, ?, ?, ?, ?, ?)", sample_challenges)
            
        self.conn.commit()
        self.conn.close()
        
    def team_exists(self, team_name):
        """Check if a team with the given name exists"""
        self.conn = sqlite3.connect(self.db_file)
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM teams WHERE name = ?", (team_name,))
        result = cursor.fetchone() is not None
        self.conn.close()
        return result
        
    def add_team(self, team_name):
        """Add a new team to the database"""
        self.conn = sqlite3.connect(self.db_file)
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO teams (name, score) VALUES (?, 0)", (team_name,))
        self.conn.commit()
        self.conn.close()
        
    def get_team_score(self, team_name):
        """Get the current score for a team"""
        self.conn = sqlite3.connect(self.db_file)
        cursor = self.conn.cursor()
        cursor.execute("SELECT score FROM teams WHERE name = ?", (team_name,))
        result = cursor.fetchone()
        self.conn.close()
        return result[0] if result else 0
        
    def update_team_score(self, team_name, points):
        """Update a team's score by adding points"""
        self.conn = sqlite3.connect(self.db_file)
        cursor = self.conn.cursor()
        cursor.execute("UPDATE teams SET score = score + ? WHERE name = ?", (points, team_name))
        self.conn.commit()
        self.conn.close()
        
    def get_all_teams(self):
        """Get all teams and their scores for the scoreboard"""
        self.conn = sqlite3.connect(self.db_file)
        cursor = self.conn.cursor()
        cursor.execute("SELECT name, score FROM teams ORDER BY score DESC")
        teams = [{"name": row[0], "score": row[1]} for row in cursor.fetchall()]
        self.conn.close()
        return teams
    
    def get_challenges_for_phase(self, phase):
        """Get all challenges for a specific phase"""
        self.conn = sqlite3.connect(self.db_file)
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, description, points FROM challenges WHERE phase = ?", (phase,))
        challenges = [{"id": row[0], "title": row[1], "description": row[2], "points": row[3]} for row in cursor.fetchall()]
        self.conn.close()
        return challenges
    
    def submit_challenge_answer(self, team_name, challenge_id, answer):
        """Record a team's submission for a challenge"""
        self.conn = sqlite3.connect(self.db_file)
        cursor = self.conn.cursor()
        
        # Get team ID
        cursor.execute("SELECT id FROM teams WHERE name = ?", (team_name,))
        team_id = cursor.fetchone()[0]
        
        # Get challenge details
        cursor.execute("SELECT correct_answer, points FROM challenges WHERE id = ?", (challenge_id,))
        challenge = cursor.fetchone()
        correct_answer = challenge[0]
        points = challenge[1]
        
        # Check if the answer is correct (simplified)
        # In a real application, you might use more sophisticated validation
        is_correct = False
        points_awarded = 0
        
        if correct_answer is not None:
            is_correct = (answer.lower() == correct_answer.lower())
            if is_correct:
                points_awarded = points
                # Update team score
                cursor.execute("UPDATE teams SET score = score + ? WHERE id = ?", (points, team_id))
        else:
            # For challenges without a fixed answer (e.g., calculations),
            # we would implement custom validation logic here
            pass
        
        # Record the submission
        cursor.execute(
            "INSERT INTO submissions (team_id, challenge_id, answer, is_correct, points_awarded) VALUES (?, ?, ?, ?, ?)",
            (team_id, challenge_id, answer, is_correct, points_awarded)
        )
        
        self.conn.commit()
        self.conn.close()
        
        return {
            "is_correct": is_correct,
            "points_awarded": points_awarded
        }