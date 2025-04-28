import json
import time
from datetime import datetime, timedelta

class ChallengeManager:
    def __init__(self, database):
        """Initialize the challenge manager with database connection"""
        self.db = database
        self.current_phase = 1
        self.phase_start_time = datetime.now()
        self.phase_durations = {
            0: timedelta(minutes=30),  # Introduction & Setup
            1: timedelta(minutes=45),  # Phase 1: Flight Identification
            2: timedelta(minutes=45),  # Phase 2: Flight Pattern Analysis
            3: timedelta(minutes=45),  # Phase 3: Emergency Response
            4: timedelta(minutes=45),  # Phase 4: Air Traffic Control
            5: timedelta(minutes=15)   # Final Presentations
        }
        
    def get_current_challenge(self):
        """Get the current active challenge based on the phase"""
        # Check if we should advance to the next phase
        self._check_phase_transition()
        
        # Get all challenges for the current phase
        challenges = self.db.get_challenges_for_phase(self.current_phase)
        
        # Add time information
        time_info = self._get_phase_time_info()
        
        return {
            "phase": self.current_phase,
            "phase_name": self._get_phase_name(self.current_phase),
            "challenges": challenges,
            "time_remaining": time_info["time_remaining_str"],
            "progress_percent": time_info["progress_percent"]
        }
    
    def _check_phase_transition(self):
        """Check if we should transition to the next phase based on time"""
        current_time = datetime.now()
        phase_duration = self.phase_durations.get(self.current_phase, timedelta(minutes=45))
        
        if current_time - self.phase_start_time > phase_duration:
            # Time to advance to the next phase
            self.current_phase += 1
            if self.current_phase > 5:  # Reset to phase 1 if we've gone through all phases
                self.current_phase = 1
            
            self.phase_start_time = current_time
            print(f"Advancing to Phase {self.current_phase}: {self._get_phase_name(self.current_phase)}")
    
    def _get_phase_time_info(self):
        """Get information about the current phase's timing"""
        current_time = datetime.now()
        phase_duration = self.phase_durations.get(self.current_phase, timedelta(minutes=45))
        
        elapsed = current_time - self.phase_start_time
        remaining = phase_duration - elapsed
        
        # Calculate progress percentage
        if phase_duration.total_seconds() > 0:
            progress_percent = min(100, (elapsed.total_seconds() / phase_duration.total_seconds()) * 100)
        else:
            progress_percent = 100
            
        # Format the remaining time as a string
        minutes, seconds = divmod(int(remaining.total_seconds()), 60)
        time_remaining_str = f"{minutes:02d}:{seconds:02d}"
        
        return {
            "elapsed": elapsed,
            "remaining": remaining,
            "time_remaining_str": time_remaining_str,
            "progress_percent": progress_percent
        }
    
    def _get_phase_name(self, phase):
        """Get the name of a phase based on its number"""
        phase_names = {
            0: "Introduction & Setup",
            1: "Flight Identification",
            2: "Flight Pattern Analysis",
            3: "Emergency Response",
            4: "Air Traffic Control",
            5: "Final Presentations"
        }
        return phase_names.get(phase, f"Phase {phase}")
    
    def check_answer(self, team_name, challenge_id, answer):
        """Check a team's answer to a challenge and award points"""
        result = self.db.submit_challenge_answer(team_name, challenge_id, answer)
        
        # Get updated team information
        team_score = self.db.get_team_score(team_name)
        
        return {
            "is_correct": result["is_correct"],
            "points_awarded": result["points_awarded"],
            "team_score": team_score,
            "message": "Correct! Points awarded." if result["is_correct"] else "That's not correct. Try again!"
        }
    
    def override_phase(self, new_phase):
        """Override the current phase (for admin control)"""
        if 0 <= new_phase <= 5:
            self.current_phase = new_phase
            self.phase_start_time = datetime.now()
            return {"success": True, "message": f"Phase set to {new_phase}: {self._get_phase_name(new_phase)}"}
        else:
            return {"success": False, "message": "Invalid phase number"}