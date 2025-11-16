"""
Overtaking Module

Handles car-to-car overtaking logic with speed differentials, slipstream, and success probabilities.

author: Extended from Formula E lap time simulator
date: 2024
"""

import numpy as np
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class OvertakingAttempt:
    """Represents an overtaking attempt"""
    attacker_id: int
    defender_id: int
    success: bool
    speed_differential: float  # km/h
    time_gain: float  # seconds if successful
    timestamp: float


class OvertakingModel:
    """
    Models overtaking behavior between cars.
    
    Features:
    - Speed differential requirements (>5 km/h)
    - Slipstream effect (5% drag reduction within 1 second)
    - Overtaking success probability based on speed difference
    - Track position awareness (overtaking zones)
    - Attack mode power advantage
    
    Example:
        overtaking = OvertakingModel(track_length=2500.0)
        result = overtaking.attempt_overtake(
            attacker_id=2, defender_id=1,
            attacker_speed=180.0, defender_speed=175.0,
            gap_seconds=0.8, attacker_has_attack_mode=True
        )
    """
    
    def __init__(self, track_length: float, random_seed: Optional[int] = None):
        """
        Initialize overtaking model.
        
        Args:
            track_length: Track length in meters
            random_seed: Optional random seed for reproducibility
        """
        self.track_length = track_length
        
        if random_seed is not None:
            np.random.seed(random_seed)
        
        # Overtaking parameters
        self.min_speed_diff = 5.0  # km/h minimum speed difference to attempt
        self.slipstream_distance = 1.0  # seconds gap for slipstream effect
        self.slipstream_drag_reduction = 0.05  # 5% drag reduction
        
        # Success probabilities based on speed differential
        # Format: (min_speed_diff, max_speed_diff, success_probability)
        self.success_probabilities = [
            (5.0, 10.0, 0.20),   # 5-10 km/h: 20% success
            (10.0, 15.0, 0.50),  # 10-15 km/h: 50% success
            (15.0, np.inf, 0.80) # >15 km/h: 80% success
        ]
        
        # Attack mode advantage
        self.attack_mode_power_boost = 50.0  # kW extra power
        self.attack_mode_speed_advantage = 8.0  # km/h typical advantage
        
        # Overtaking history
        self.overtaking_history: List[OvertakingAttempt] = []
        
    def calculate_slipstream_effect(self, gap_seconds: float, base_drag: float) -> float:
        """
        Calculate drag reduction from slipstream.
        
        Args:
            gap_seconds: Time gap to car ahead in seconds
            base_drag: Base drag coefficient (c_w_a)
            
        Returns:
            Modified drag coefficient
        """
        if gap_seconds <= self.slipstream_distance:
            # Within slipstream zone
            drag_reduction = self.slipstream_drag_reduction * (1.0 - gap_seconds / self.slipstream_distance)
            return base_drag * (1.0 - drag_reduction)
        return base_drag
    
    def get_overtaking_success_probability(self, speed_diff_kmh: float, 
                                          attacker_has_attack_mode: bool = False,
                                          defender_has_attack_mode: bool = False) -> float:
        """
        Calculate probability of successful overtake.
        
        Args:
            speed_diff_kmh: Speed difference in km/h (attacker - defender)
            attacker_has_attack_mode: Whether attacker has active attack mode
            defender_has_attack_mode: Whether defender has active attack mode
            
        Returns:
            Success probability [0.0, 1.0]
        """
        # Adjust speed differential for attack mode
        if attacker_has_attack_mode:
            speed_diff_kmh += self.attack_mode_speed_advantage
        if defender_has_attack_mode:
            speed_diff_kmh -= self.attack_mode_speed_advantage
        
        if speed_diff_kmh < self.min_speed_diff:
            return 0.0
        
        # Find appropriate probability range
        for min_diff, max_diff, prob in self.success_probabilities:
            if min_diff <= speed_diff_kmh < max_diff:
                return prob
        
        # If speed diff is very high, use maximum probability
        return 0.95
    
    def attempt_overtake(self, attacker_id: int, defender_id: int,
                        attacker_speed: float, defender_speed: float,
                        gap_seconds: float, track_position: float,
                        attacker_has_attack_mode: bool = False,
                        defender_has_attack_mode: bool = False,
                        timestamp: float = 0.0) -> Dict:
        """
        Attempt an overtake.
        
        Args:
            attacker_id: ID of attacking car
            defender_id: ID of defending car
            attacker_speed: Attacker speed in m/s
            defender_speed: Defender speed in m/s
            gap_seconds: Time gap between cars in seconds
            track_position: Current track position (0.0 to 1.0)
            attacker_has_attack_mode: Whether attacker has active attack mode
            defender_has_attack_mode: Whether defender has active attack mode
            timestamp: Current race time
            
        Returns:
            Dictionary with overtaking result:
            {
                'success': bool,
                'speed_differential_kmh': float,
                'time_gain': float,
                'slipstream_active': bool
            }
        """
        # Convert speeds to km/h
        attacker_speed_kmh = attacker_speed * 3.6
        defender_speed_kmh = defender_speed * 3.6
        speed_diff_kmh = attacker_speed_kmh - defender_speed_kmh
        
        # Check if overtaking is even possible
        if speed_diff_kmh < self.min_speed_diff:
            return {
                'success': False,
                'speed_differential_kmh': speed_diff_kmh,
                'time_gain': 0.0,
                'slipstream_active': gap_seconds <= self.slipstream_distance
            }
        
        # Check if in slipstream
        slipstream_active = gap_seconds <= self.slipstream_distance
        
        # Calculate success probability
        success_prob = self.get_overtaking_success_probability(
            speed_diff_kmh,
            attacker_has_attack_mode,
            defender_has_attack_mode
        )
        
        # Determine success
        success = np.random.random() < success_prob
        
        # Calculate time gain if successful
        time_gain = 0.0
        if success:
            # Time gain depends on speed differential
            # Approximate: if 10 km/h faster, gain ~0.1s per 100m
            speed_diff_ms = speed_diff_kmh / 3.6
            # Typical overtaking distance: 200-300m
            overtaking_distance = 250.0  # meters
            time_gain = overtaking_distance / (attacker_speed + speed_diff_ms / 2) - \
                       overtaking_distance / defender_speed
            time_gain = max(0.0, time_gain)  # Ensure positive
        
        # Record attempt
        attempt = OvertakingAttempt(
            attacker_id=attacker_id,
            defender_id=defender_id,
            success=success,
            speed_differential=speed_diff_kmh,
            time_gain=time_gain,
            timestamp=timestamp
        )
        self.overtaking_history.append(attempt)
        
        return {
            'success': success,
            'speed_differential_kmh': speed_diff_kmh,
            'time_gain': time_gain,
            'slipstream_active': slipstream_active
        }
    
    def can_overtake(self, attacker_speed: float, defender_speed: float,
                     gap_seconds: float) -> bool:
        """
        Quick check if overtaking is possible (without attempting).
        
        Args:
            attacker_speed: Attacker speed in m/s
            defender_speed: Defender speed in m/s
            gap_seconds: Time gap in seconds
            
        Returns:
            True if overtaking is possible
        """
        speed_diff_kmh = (attacker_speed - defender_speed) * 3.6
        return speed_diff_kmh >= self.min_speed_diff and gap_seconds <= 2.0
    
    def get_overtaking_statistics(self) -> Dict:
        """Get statistics about overtaking attempts."""
        if not self.overtaking_history:
            return {
                'total_attempts': 0,
                'successful_overtakes': 0,
                'success_rate': 0.0,
                'avg_speed_differential': 0.0
            }
        
        successful = sum(1 for attempt in self.overtaking_history if attempt.success)
        avg_speed_diff = np.mean([attempt.speed_differential for attempt in self.overtaking_history])
        
        return {
            'total_attempts': len(self.overtaking_history),
            'successful_overtakes': successful,
            'success_rate': successful / len(self.overtaking_history),
            'avg_speed_differential': avg_speed_diff
        }


# Example usage
if __name__ == "__main__":
    # Test overtaking model
    overtaking = OvertakingModel(track_length=2500.0, random_seed=42)
    
    # Simulate several overtaking attempts
    scenarios = [
        (180.0, 175.0, 0.8, False, False),  # Small speed diff
        (185.0, 175.0, 0.6, False, False),  # Medium speed diff
        (190.0, 175.0, 0.5, True, False),  # Large speed diff with attack mode
        (180.0, 175.0, 1.5, False, False),  # Too far back
    ]
    
    for i, (attacker_speed, defender_speed, gap, am_attacker, am_defender) in enumerate(scenarios):
        result = overtaking.attempt_overtake(
            attacker_id=2, defender_id=1,
            attacker_speed=attacker_speed / 3.6,  # Convert to m/s
            defender_speed=defender_speed / 3.6,
            gap_seconds=gap,
            track_position=0.5,
            attacker_has_attack_mode=am_attacker,
            defender_has_attack_mode=am_defender,
            timestamp=i * 10.0
        )
        
        print(f"Attempt {i+1}: Speed diff={result['speed_differential_kmh']:.1f} km/h, "
              f"Success={result['success']}, Time gain={result['time_gain']:.3f}s")
    
    print("\nOvertaking Statistics:")
    print(overtaking.get_overtaking_statistics())

