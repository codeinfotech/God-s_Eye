"""
Race Events Module

Handles random race events: safety car, crashes, weather changes.

author: Extended from Formula E lap time simulator
date: 2024
"""

import numpy as np
import random
from typing import Dict, List, Tuple, Optional
from enum import Enum


class EventType(Enum):
    """Types of race events"""
    SAFETY_CAR = "safety_car"
    CRASH = "crash"
    WEATHER_CHANGE = "weather_change"
    VIRTUAL_SAFETY_CAR = "virtual_safety_car"


class SafetyCarState(Enum):
    """Safety car deployment states"""
    DEPLOYED = "deployed"
    STANDING = "standing"  # Cars bunched up, waiting
    RETURNING = "returning"  # Returning to pits
    CLEAR = "clear"  # Race resumed


class RaceEvent:
    """Represents a single race event"""
    
    def __init__(self, event_type: EventType, timestamp: float, car_id: Optional[int] = None,
                 description: str = ""):
        self.event_type = event_type
        self.timestamp = timestamp
        self.car_id = car_id
        self.description = description


class RaceEvents:
    """
    Manages all race events during a simulation.
    
    Features:
    - Safety car deployment (2-5% chance per lap)
    - Crashes/DNFs (1-2% per car per lap)
    - Weather changes (rain, track temperature)
    - Virtual safety car
    
    Example:
        events = RaceEvents(num_cars=20, track_length=2500.0)
        events.check_lap_events(current_lap=5, race_time=600.0)
        if events.safety_car_active:
            speed_limit = events.get_safety_car_speed()
    """
    
    def __init__(self, num_cars: int, track_length: float, random_seed: Optional[int] = None):
        """
        Initialize race events manager.
        
        Args:
            num_cars: Number of cars in the race
            track_length: Track length in meters
            random_seed: Optional random seed for reproducibility
        """
        self.num_cars = num_cars
        self.track_length = track_length
        
        if random_seed is not None:
            np.random.seed(random_seed)
            random.seed(random_seed)
        
        # Safety car state
        self.safety_car_state = SafetyCarState.CLEAR
        self.safety_car_active = False
        self.safety_car_laps_remaining = 0
        self.safety_car_deployment_lap = None
        self.safety_car_speed = 80.0 / 3.6  # 80 km/h in m/s
        
        # Event probabilities (per lap)
        self.safety_car_probability = 0.03  # 3% per lap
        self.crash_probability_per_car = 0.015  # 1.5% per car per lap
        self.weather_change_probability = 0.02  # 2% per lap
        
        # Weather state
        self.weather_dry = True
        self.mu_weather = 1.0  # Friction multiplier (1.0 = dry, 0.7 = wet)
        self.track_temperature = 25.0  # Celsius
        
        # Event log
        self.event_log: List[RaceEvent] = []
        
        # Crashed cars (set of car IDs)
        self.crashed_cars: set = set()
        
        # Statistics
        self.total_safety_cars = 0
        self.total_crashes = 0
        
    def check_lap_events(self, current_lap: int, race_time: float, 
                        active_cars: List[int]) -> Dict:
        """
        Check for events at the start of a new lap.
        
        Args:
            current_lap: Current lap number
            race_time: Current race time in seconds
            active_cars: List of active car IDs (not crashed)
            
        Returns:
            Dictionary with event information:
            {
                'safety_car_deployed': bool,
                'crashes': List[car_id],
                'weather_changed': bool,
                'new_mu_weather': float
            }
        """
        events = {
            'safety_car_deployed': False,
            'crashes': [],
            'weather_changed': False,
            'new_mu_weather': self.mu_weather
        }
        
        # Check safety car (only if not already active)
        if not self.safety_car_active:
            if np.random.random() < self.safety_car_probability:
                self._deploy_safety_car(current_lap, race_time)
                events['safety_car_deployed'] = True
        
        # Check crashes (only for active cars)
        for car_id in active_cars:
            if car_id not in self.crashed_cars:
                if np.random.random() < self.crash_probability_per_car:
                    self._register_crash(car_id, race_time)
                    events['crashes'].append(car_id)
                    
                    # Crash may trigger safety car (50% chance)
                    if not self.safety_car_active and np.random.random() < 0.5:
                        self._deploy_safety_car(current_lap, race_time)
                        events['safety_car_deployed'] = True
        
        # Check weather change
        if np.random.random() < self.weather_change_probability:
            self._change_weather()
            events['weather_changed'] = True
            events['new_mu_weather'] = self.mu_weather
        
        return events
    
    def update_safety_car(self, current_lap: int) -> bool:
        """
        Update safety car state. Call this each lap.
        
        Args:
            current_lap: Current lap number
            
        Returns:
            True if safety car state changed
        """
        if not self.safety_car_active:
            return False
        
        state_changed = False
        
        # Decrement laps remaining
        self.safety_car_laps_remaining -= 1
        
        if self.safety_car_laps_remaining <= 0:
            # Safety car ending
            if self.safety_car_state == SafetyCarState.DEPLOYED:
                # Transition to returning
                self.safety_car_state = SafetyCarState.RETURNING
                self.safety_car_laps_remaining = 1  # One lap to return
                state_changed = True
            elif self.safety_car_state == SafetyCarState.RETURNING:
                # Safety car returned, race resumes
                self.safety_car_active = False
                self.safety_car_state = SafetyCarState.CLEAR
                self.safety_car_laps_remaining = 0
                state_changed = True
        
        return state_changed
    
    def get_safety_car_speed(self) -> float:
        """Get current safety car speed limit in m/s."""
        if self.safety_car_active:
            return self.safety_car_speed
        return np.inf
    
    def is_car_crashed(self, car_id: int) -> bool:
        """Check if a car has crashed."""
        return car_id in self.crashed_cars
    
    def get_active_cars(self, all_car_ids: List[int]) -> List[int]:
        """Get list of active (non-crashed) car IDs."""
        return [cid for cid in all_car_ids if cid not in self.crashed_cars]
    
    def get_weather_factor(self) -> float:
        """Get current weather friction factor."""
        return self.mu_weather
    
    def _deploy_safety_car(self, lap: int, race_time: float):
        """Deploy safety car."""
        self.safety_car_active = True
        self.safety_car_state = SafetyCarState.DEPLOYED
        self.safety_car_deployment_lap = lap
        # Duration: 3-8 laps
        self.safety_car_laps_remaining = np.random.randint(3, 9)
        self.total_safety_cars += 1
        
        event = RaceEvent(
            EventType.SAFETY_CAR,
            race_time,
            description=f"Safety car deployed on lap {lap} for {self.safety_car_laps_remaining} laps"
        )
        self.event_log.append(event)
    
    def _register_crash(self, car_id: int, race_time: float):
        """Register a car crash."""
        self.crashed_cars.add(car_id)
        self.total_crashes += 1
        
        event = RaceEvent(
            EventType.CRASH,
            race_time,
            car_id=car_id,
            description=f"Car {car_id} crashed and retired"
        )
        self.event_log.append(event)
    
    def _change_weather(self):
        """Change weather conditions."""
        if self.weather_dry:
            # Start raining
            self.weather_dry = False
            # Reduce grip by 15-30%
            grip_reduction = np.random.uniform(0.15, 0.30)
            self.mu_weather = 1.0 - grip_reduction
            self.track_temperature -= np.random.uniform(5, 15)
        else:
            # Track drying (gradual)
            if np.random.random() < 0.3:  # 30% chance to dry
                self.weather_dry = True
                self.mu_weather = np.random.uniform(0.85, 1.0)  # Partially dry
                self.track_temperature += np.random.uniform(2, 8)
        
        # Clamp values
        self.mu_weather = np.clip(self.mu_weather, 0.5, 1.0)
        self.track_temperature = np.clip(self.track_temperature, 10, 50)
    
    def get_event_summary(self) -> Dict:
        """Get summary of all events."""
        return {
            'total_safety_cars': self.total_safety_cars,
            'total_crashes': self.total_crashes,
            'crashed_cars': list(self.crashed_cars),
            'weather_dry': self.weather_dry,
            'mu_weather': self.mu_weather,
            'track_temperature': self.track_temperature,
            'event_count': len(self.event_log)
        }
    
    def get_events_log(self) -> List[RaceEvent]:
        """Get full event log."""
        return self.event_log.copy()


# Example usage
if __name__ == "__main__":
    # Test race events
    events = RaceEvents(num_cars=20, track_length=2500.0, random_seed=42)
    
    # Simulate 10 laps
    for lap in range(1, 11):
        active_cars = list(range(20))
        lap_events = events.check_lap_events(lap, lap * 120.0, active_cars)
        
        if lap_events['safety_car_deployed']:
            print(f"Lap {lap}: Safety car deployed!")
        
        if lap_events['crashes']:
            print(f"Lap {lap}: Crashes: {lap_events['crashes']}")
        
        if lap_events['weather_changed']:
            print(f"Lap {lap}: Weather changed, mu={lap_events['new_mu_weather']:.2f}")
        
        # Update safety car
        events.update_safety_car(lap)
    
    print("\nEvent Summary:")
    print(events.get_event_summary())

