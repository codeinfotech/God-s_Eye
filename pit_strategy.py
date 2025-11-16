"""
Pit Strategy Module

Handles pit stop logic for Formula E (energy management, repairs).

Note: Formula E typically doesn't pit during races, but this module
supports future scenarios (battery swap, repairs after incidents).

author: Extended from Formula E lap time simulator
date: 2024
"""

import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class PitStopType(Enum):
    """Types of pit stops"""
    ENERGY = "energy"  # Battery swap / energy top-up
    REPAIR = "repair"  # Car repairs after incident
    PENALTY = "penalty"  # Drive-through penalty


@dataclass
class PitStop:
    """Represents a pit stop"""
    car_id: int
    pit_type: PitStopType
    lap: int
    race_time: float
    duration: float  # seconds
    time_loss: float  # seconds vs normal lap time


class PitStrategy:
    """
    Manages pit stop strategy for Formula E.
    
    Formula E typically doesn't pit, but this supports:
    - Energy-critical pit stops (if battery swap allowed)
    - Repairs after crashes/incidents
    - Drive-through penalties
    
    Example:
        pit_strategy = PitStrategy(num_cars=20)
        if pit_strategy.should_pit(car_id, energy_remaining, race_distance_remaining):
            pit_stop = pit_strategy.execute_pit_stop(car_id, PitStopType.ENERGY, lap, race_time)
    """
    
    def __init__(self, num_cars: int, random_seed: Optional[int] = None):
        """
        Initialize pit strategy manager.
        
        Args:
            num_cars: Number of cars in race
            random_seed: Optional random seed
        """
        self.num_cars = num_cars
        
        if random_seed is not None:
            np.random.seed(random_seed)
        
        # Pit stop parameters
        self.energy_pit_duration = 30.0  # seconds (battery swap)
        self.repair_pit_duration = 25.0  # seconds (minor repairs)
        self.penalty_duration = 10.0  # seconds (drive-through)
        
        # Time loss vs normal lap
        self.energy_pit_time_loss = 35.0  # seconds
        self.repair_pit_time_loss = 30.0  # seconds
        self.penalty_time_loss = 15.0  # seconds
        
        # Energy thresholds
        self.energy_critical_threshold = 0.15  # 15% remaining = critical
        
        # Pit stop history
        self.pit_stops: Dict[int, List[PitStop]] = {car_id: [] for car_id in range(num_cars)}
    
    def should_pit_energy(self, car_id: int, energy_remaining: float,
                         initial_energy: float, race_distance_remaining: float,
                         current_lap: int) -> Tuple[bool, str]:
        """
        Determine if car should pit for energy.
        
        Args:
            car_id: Car identifier
            energy_remaining: Current energy in Joules
            initial_energy: Initial energy in Joules
            race_distance_remaining: Remaining race distance in meters
            current_lap: Current lap number
            
        Returns:
            Tuple of (should_pit: bool, reason: str)
        """
        # Formula E typically doesn't pit, so this is for future scenarios
        energy_percent = energy_remaining / initial_energy
        
        # Check if energy is critical
        if energy_percent < self.energy_critical_threshold:
            # Estimate if can finish race
            energy_per_km = (initial_energy - energy_remaining) / (current_lap * 2.5)  # Approximate
            energy_needed = energy_per_km * (race_distance_remaining / 1000.0)
            
            if energy_remaining < energy_needed * 1.1:  # 10% safety margin
                return True, "Energy critical, cannot finish race"
        
        return False, "Sufficient energy"
    
    def execute_pit_stop(self, car_id: int, pit_type: PitStopType,
                        lap: int, race_time: float) -> PitStop:
        """
        Execute a pit stop.
        
        Args:
            car_id: Car identifier
            pit_type: Type of pit stop
            lap: Current lap number
            race_time: Current race time
            
        Returns:
            PitStop object with details
        """
        # Determine duration and time loss
        if pit_type == PitStopType.ENERGY:
            duration = self.energy_pit_duration
            time_loss = self.energy_pit_time_loss
        elif pit_type == PitStopType.REPAIR:
            duration = self.repair_pit_duration
            time_loss = self.repair_pit_time_loss
        else:  # PENALTY
            duration = self.penalty_duration
            time_loss = self.penalty_time_loss
        
        # Add some randomness
        duration += np.random.uniform(-2.0, 2.0)
        time_loss += np.random.uniform(-1.0, 1.0)
        
        pit_stop = PitStop(
            car_id=car_id,
            pit_type=pit_type,
            lap=lap,
            race_time=race_time,
            duration=duration,
            time_loss=time_loss
        )
        
        # Record pit stop
        self.pit_stops[car_id].append(pit_stop)
        
        return pit_stop
    
    def get_pit_stop_count(self, car_id: int) -> int:
        """Get number of pit stops for a car."""
        return len(self.pit_stops.get(car_id, []))
    
    def get_total_pit_time(self, car_id: int) -> float:
        """Get total time lost in pit stops for a car."""
        return sum(pit.time_loss for pit in self.pit_stops.get(car_id, []))


# Example usage
if __name__ == "__main__":
    pit_strategy = PitStrategy(num_cars=20, random_seed=42)
    
    # Check if car should pit
    should_pit, reason = pit_strategy.should_pit_energy(
        car_id=1,
        energy_remaining=0.5e6,  # 0.5 MJ remaining
        initial_energy=4.58e6,  # 4.58 MJ initial
        race_distance_remaining=5000.0,  # 5 km remaining
        current_lap=20
    )
    
    print(f"Should pit: {should_pit}, Reason: {reason}")
    
    if should_pit:
        pit_stop = pit_strategy.execute_pit_stop(1, PitStopType.ENERGY, 20, 1200.0)
        print(f"Pit stop: {pit_stop.duration:.1f}s duration, {pit_stop.time_loss:.1f}s time loss")

