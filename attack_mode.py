"""
Attack Mode Module

Formula E Attack Mode system implementation.

Attack Mode provides temporary power boost (200kW -> 250kW) but requires
driving off the racing line through an activation zone, causing time loss.

author: Extended from Formula E lap time simulator
date: 2024
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class AttackModeState(Enum):
    """Attack Mode activation states"""
    AVAILABLE = "available"  # Can be activated
    ACTIVATING = "activating"  # Currently in activation zone
    ACTIVE = "active"  # Currently active
    USED = "used"  # All activations used


@dataclass
class AttackModeActivation:
    """Record of an Attack Mode activation"""
    car_id: int
    activation_lap: int
    activation_time: float
    duration: float
    time_loss: float
    power_boost: float  # kW


class AttackMode:
    """
    Manages Formula E Attack Mode for a single car.
    
    Formula E Attack Mode Rules:
    - 2 activations per race (or 8 activations × 30 seconds in some seasons)
    - Duration: 4 minutes each (or 30 seconds × 8)
    - Power boost: 200kW -> 250kW (+50kW)
    - Requires driving through activation zone (off racing line)
    - Time loss: 0.5-1.0 seconds per activation
    
    Example:
        attack_mode = AttackMode(car_id=1, activation_zone_start=500.0, 
                                activation_zone_end=600.0)
        if attack_mode.can_activate(current_lap=5, race_time=600.0):
            attack_mode.activate(current_lap=5, race_time=600.0)
        if attack_mode.is_active():
            power_kw = attack_mode.get_power_boost()  # Returns 250.0
    """
    
    def __init__(self, car_id: int, activation_zone_start: float, 
                 activation_zone_end: float, base_power_kw: float = 200.0,
                 random_seed: Optional[int] = None):
        """
        Initialize Attack Mode for a car.
        
        Args:
            car_id: Car identifier
            activation_zone_start: Track distance where activation zone starts (meters)
            activation_zone_end: Track distance where activation zone ends (meters)
            base_power_kw: Base power without attack mode (default 200kW for FE)
            random_seed: Optional random seed
        """
        self.car_id = car_id
        self.activation_zone_start = activation_zone_start
        self.activation_zone_end = activation_zone_end
        self.base_power_kw = base_power_kw
        self.attack_mode_power_kw = 250.0  # 50kW boost
        
        if random_seed is not None:
            np.random.seed(random_seed + car_id)  # Different seed per car
        
        # Attack Mode parameters
        self.max_activations = 2  # 2 activations per race
        self.activation_duration = 240.0  # 4 minutes in seconds
        self.activation_time_loss = np.random.uniform(0.5, 1.0)  # 0.5-1.0s time loss
        
        # State
        self.state = AttackModeState.AVAILABLE
        self.activations_remaining = self.max_activations
        self.current_activation_start_time = None
        self.current_activation_lap = None
        
        # History
        self.activation_history: List[AttackModeActivation] = []
        
    def can_activate(self, current_lap: int, race_time: float, 
                    track_position: float) -> Tuple[bool, str]:
        """
        Check if Attack Mode can be activated.
        
        Args:
            current_lap: Current lap number
            race_time: Current race time in seconds
            track_position: Current track position (distance from start in meters)
            
        Returns:
            Tuple of (can_activate: bool, reason: str)
        """
        if self.state == AttackModeState.USED:
            return False, "All activations used"
        
        if self.state == AttackModeState.ACTIVE:
            return False, "Already active"
        
        if self.state == AttackModeState.ACTIVATING:
            return False, "Currently activating"
        
        # Check if in activation zone
        zone_length = self.activation_zone_end - self.activation_zone_start
        position_in_zone = track_position % (zone_length + 1000.0)  # Approximate
        
        if not (self.activation_zone_start <= position_in_zone <= self.activation_zone_end):
            return False, "Not in activation zone"
        
        return True, "Can activate"
    
    def activate(self, current_lap: int, race_time: float, track_position: float) -> bool:
        """
        Activate Attack Mode.
        
        Args:
            current_lap: Current lap number
            race_time: Current race time in seconds
            track_position: Current track position
            
        Returns:
            True if activation successful
        """
        can_activate, reason = self.can_activate(current_lap, race_time, track_position)
        
        if not can_activate:
            return False
        
        # Start activation process
        self.state = AttackModeState.ACTIVATING
        self.current_activation_start_time = race_time
        self.current_activation_lap = current_lap
        
        # Activation happens immediately (time loss applied)
        # In real FE, driver must drive through zone
        self.state = AttackModeState.ACTIVE
        self.activations_remaining -= 1
        
        # Record activation
        activation = AttackModeActivation(
            car_id=self.car_id,
            activation_lap=current_lap,
            activation_time=race_time,
            duration=self.activation_duration,
            time_loss=self.activation_time_loss,
            power_boost=self.attack_mode_power_kw - self.base_power_kw
        )
        self.activation_history.append(activation)
        
        return True
    
    def update(self, race_time: float) -> bool:
        """
        Update Attack Mode state. Call this each time step.
        
        Args:
            race_time: Current race time in seconds
            
        Returns:
            True if state changed (e.g., expired)
        """
        if self.state == AttackModeState.ACTIVE:
            # Check if duration expired
            if self.current_activation_start_time is not None:
                elapsed = race_time - self.current_activation_start_time
                if elapsed >= self.activation_duration:
                    # Attack Mode expired
                    self.state = AttackModeState.AVAILABLE if self.activations_remaining > 0 else AttackModeState.USED
                    self.current_activation_start_time = None
                    return True
        return False
    
    def is_active(self) -> bool:
        """Check if Attack Mode is currently active."""
        return self.state == AttackModeState.ACTIVE
    
    def is_activating(self) -> bool:
        """Check if currently in activation process."""
        return self.state == AttackModeState.ACTIVATING
    
    def get_power_kw(self) -> float:
        """
        Get current power output in kW.
        
        Returns:
            Power in kW (250kW if active, 200kW otherwise)
        """
        if self.is_active():
            return self.attack_mode_power_kw
        return self.base_power_kw
    
    def get_power_boost(self) -> float:
        """
        Get current power boost in kW.
        
        Returns:
            Power boost in kW (50kW if active, 0kW otherwise)
        """
        if self.is_active():
            return self.attack_mode_power_kw - self.base_power_kw
        return 0.0
    
    def get_activations_remaining(self) -> int:
        """Get number of activations remaining."""
        return self.activations_remaining
    
    def get_activation_history(self) -> List[AttackModeActivation]:
        """Get history of all activations."""
        return self.activation_history.copy()
    
    def get_time_loss(self) -> float:
        """
        Get time loss from last activation (if currently activating).
        
        Returns:
            Time loss in seconds
        """
        if self.state == AttackModeState.ACTIVATING:
            return self.activation_time_loss
        return 0.0


class AttackModeManager:
    """
    Manages Attack Mode for all cars in the race.
    
    Example:
        manager = AttackModeManager(num_cars=20, track_length=2500.0)
        manager.set_activation_zone(500.0, 600.0)  # Set zone for all cars
        
        for car_id in range(20):
            if manager.can_activate(car_id, current_lap, race_time, track_pos):
                manager.activate(car_id, current_lap, race_time, track_pos)
    """
    
    def __init__(self, num_cars: int, track_length: float, 
                 activation_zone_start: Optional[float] = None,
                 activation_zone_end: Optional[float] = None,
                 random_seed: Optional[int] = None):
        """
        Initialize Attack Mode manager for all cars.
        
        Args:
            num_cars: Number of cars in race
            track_length: Track length in meters
            activation_zone_start: Start of activation zone (default: 20% of track)
            activation_zone_end: End of activation zone (default: 25% of track)
            random_seed: Optional random seed
        """
        self.num_cars = num_cars
        self.track_length = track_length
        
        # Set default activation zone if not provided
        if activation_zone_start is None:
            activation_zone_start = track_length * 0.20
        if activation_zone_end is None:
            activation_zone_end = track_length * 0.25
        
        self.activation_zone_start = activation_zone_start
        self.activation_zone_end = activation_zone_end
        
        # Create Attack Mode for each car
        self.attack_modes: Dict[int, AttackMode] = {}
        for car_id in range(num_cars):
            self.attack_modes[car_id] = AttackMode(
                car_id=car_id,
                activation_zone_start=activation_zone_start,
                activation_zone_end=activation_zone_end,
                random_seed=random_seed
            )
    
    def can_activate(self, car_id: int, current_lap: int, race_time: float,
                    track_position: float) -> Tuple[bool, str]:
        """Check if car can activate Attack Mode."""
        if car_id not in self.attack_modes:
            return False, "Invalid car ID"
        return self.attack_modes[car_id].can_activate(current_lap, race_time, track_position)
    
    def activate(self, car_id: int, current_lap: int, race_time: float,
                track_position: float) -> bool:
        """Activate Attack Mode for a car."""
        if car_id not in self.attack_modes:
            return False
        return self.attack_modes[car_id].activate(current_lap, race_time, track_position)
    
    def update_all(self, race_time: float):
        """Update all Attack Mode states."""
        for attack_mode in self.attack_modes.values():
            attack_mode.update(race_time)
    
    def is_active(self, car_id: int) -> bool:
        """Check if car has active Attack Mode."""
        if car_id not in self.attack_modes:
            return False
        return self.attack_modes[car_id].is_active()
    
    def get_power_kw(self, car_id: int) -> float:
        """Get current power for a car."""
        if car_id not in self.attack_modes:
            return 200.0
        return self.attack_modes[car_id].get_power_kw()
    
    def get_activations_remaining(self, car_id: int) -> int:
        """Get remaining activations for a car."""
        if car_id not in self.attack_modes:
            return 0
        return self.attack_modes[car_id].get_activations_remaining()


# Example usage
if __name__ == "__main__":
    # Test Attack Mode
    attack_mode = AttackMode(
        car_id=1,
        activation_zone_start=500.0,
        activation_zone_end=600.0,
        random_seed=42
    )
    
    # Simulate activation
    print(f"Can activate: {attack_mode.can_activate(1, 0.0, 550.0)[0]}")
    attack_mode.activate(1, 0.0, 550.0)
    print(f"Active: {attack_mode.is_active()}, Power: {attack_mode.get_power_kw()} kW")
    
    # Update over time
    for t in range(0, 300, 60):
        attack_mode.update(t)
        print(f"Time {t}s: Active={attack_mode.is_active()}, "
              f"Remaining={attack_mode.get_activations_remaining()}")

