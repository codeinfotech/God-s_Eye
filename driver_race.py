"""
Extended Driver Module for Race Simulation

Adds race position awareness and strategic decision making to the base driver.

author: Extended from Formula E lap time simulator
date: 2024
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from laptimesim.src.driver import Driver


class RaceDriver(Driver):
    """
    Extended driver with race position awareness and strategic decision making.
    
    Extends the base Driver class with:
    - Race position tracking
    - Gap management (defend/attack)
    - Energy delta tracking vs competitors
    - Strategic decision making (attack mode timing, energy conservation)
    - Response to safety car
    
    Example:
        race_driver = RaceDriver(car, driver_opts, track, stepsize)
        decision = race_driver.make_strategic_decision(
            position=3, gap_ahead=2.5, gap_behind=1.2,
            energy_remaining=2.5e6, attack_mode_available=True
        )
    """
    
    def __init__(self, carobj, pars_driver: dict, trackobj, stepsize: float = 5.0,
                 driver_skill: float = 1.0, aggression_level: str = "neutral"):
        """
        Initialize race driver.
        
        Args:
            carobj: Car object
            pars_driver: Driver parameters (from base Driver)
            trackobj: Track object
            stepsize: Track step size
            driver_skill: Driver skill multiplier (0.98-1.02)
            aggression_level: "conservative", "neutral", "aggressive"
        """
        super().__init__(carobj, pars_driver, trackobj, stepsize)
        
        self.driver_skill = driver_skill
        self.aggression_level = aggression_level
        
        # Race state tracking
        self.current_position = None
        self.gap_to_leader = 0.0
        self.gap_to_car_ahead = 0.0
        self.gap_to_car_behind = 0.0
        self.energy_remaining = pars_driver["initial_energy"]
        
        # Strategy parameters
        self.defend_threshold = 1.0  # seconds - defend if gap behind < this
        self.attack_threshold = 2.0  # seconds - attack if gap ahead < this
        self.energy_critical_threshold = 0.2  # 20% energy remaining = critical
    
    def race_position_awareness(self, position: int, gap_to_leader: float,
                               gap_ahead: float, gap_behind: float):
        """
        Update driver's awareness of race position.
        
        Args:
            position: Current race position (1st, 2nd, etc.)
            gap_to_leader: Gap to race leader in seconds
            gap_ahead: Gap to car ahead in seconds
            gap_behind: Gap to car behind in seconds
        """
        self.current_position = position
        self.gap_to_leader = gap_to_leader
        self.gap_to_car_ahead = gap_ahead
        self.gap_to_car_behind = gap_behind
    
    def gap_management(self) -> str:
        """
        Determine gap management strategy.
        
        Returns:
            "defend", "attack", or "maintain"
        """
        if self.gap_to_car_behind < self.defend_threshold:
            return "defend"
        elif self.gap_to_car_ahead < self.attack_threshold:
            return "attack"
        else:
            return "maintain"
    
    def energy_delta_tracking(self, competitor_energies: Dict[int, float],
                            race_distance_remaining: float) -> float:
        """
        Track energy usage vs competitors.
        
        Args:
            competitor_energies: Dict of {car_id: energy_remaining}
            race_distance_remaining: Remaining race distance in meters
            
        Returns:
            Energy delta vs average competitor (positive = more energy)
        """
        if not competitor_energies:
            return 0.0
        
        avg_competitor_energy = np.mean(list(competitor_energies.values()))
        return self.energy_remaining - avg_competitor_energy
    
    def strategic_decision_maker(self, laps_remaining: int,
                                attack_mode_available: bool,
                                attack_mode_remaining: int,
                                safety_car_active: bool) -> Dict:
        """
        Make strategic decisions based on race situation.
        
        Args:
            laps_remaining: Number of laps remaining
            attack_mode_available: Whether attack mode can be activated
            attack_mode_remaining: Number of attack mode activations remaining
            safety_car_active: Whether safety car is deployed
            
        Returns:
            Dictionary with strategic decisions:
            {
                'use_attack_mode': bool,
                'energy_mode': 'push' | 'conserve' | 'normal',
                'defend_position': bool,
                'attack_position': bool
            }
        """
        decision = {
            'use_attack_mode': False,
            'energy_mode': 'normal',
            'defend_position': False,
            'attack_position': False
        }
        
        # Gap management
        gap_strategy = self.gap_management()
        if gap_strategy == "defend":
            decision['defend_position'] = True
            decision['energy_mode'] = 'push'  # Push to defend
        elif gap_strategy == "attack":
            decision['attack_position'] = True
            decision['energy_mode'] = 'push'
        
        # Energy management
        energy_percent = self.energy_remaining / self.pars_driver["initial_energy"]
        if energy_percent < self.energy_critical_threshold:
            decision['energy_mode'] = 'conserve'
        elif energy_percent > 0.8 and laps_remaining > 5:
            # Plenty of energy, can push
            decision['energy_mode'] = 'push'
        
        # Attack mode decision
        if attack_mode_available and attack_mode_remaining > 0:
            # Use attack mode if:
            # 1. Attacking position and close to car ahead
            # 2. Defending and car behind is close
            # 3. Final laps and in contention
            if (decision['attack_position'] and self.gap_to_car_ahead < 1.5) or \
               (decision['defend_position'] and self.gap_to_car_behind < 0.8) or \
               (laps_remaining <= 3 and self.current_position <= 3):
                decision['use_attack_mode'] = True
        
        # Safety car response
        if safety_car_active:
            # Conserve energy during safety car
            decision['energy_mode'] = 'conserve'
            decision['use_attack_mode'] = False  # Don't waste attack mode
        
        # Adjust based on aggression level
        if self.aggression_level == "conservative":
            decision['energy_mode'] = 'conserve' if decision['energy_mode'] == 'normal' else decision['energy_mode']
            decision['use_attack_mode'] = False  # Conservative drivers save attack mode
        elif self.aggression_level == "aggressive":
            if self.gap_to_car_ahead < 3.0:
                decision['attack_position'] = True
                decision['energy_mode'] = 'push'
        
        return decision
    
    def should_activate_attack_mode(self, current_lap: int, total_laps: int,
                                   gap_ahead: float, gap_behind: float,
                                   attack_mode_remaining: int) -> bool:
        """
        Determine if attack mode should be activated.
        
        Args:
            current_lap: Current lap number
            total_laps: Total race laps
            gap_ahead: Gap to car ahead
            gap_behind: Gap to car behind
            attack_mode_remaining: Remaining activations
            
        Returns:
            True if should activate
        """
        if attack_mode_remaining == 0:
            return False
        
        # Strategic timing based on position
        if self.current_position == 1:
            # Leader: only use if under pressure
            return gap_behind < 1.0 and attack_mode_remaining > 1
        elif self.current_position <= 3:
            # Top 3: use if close to position ahead
            return gap_ahead < 2.0
        else:
            # Lower positions: use more aggressively
            return gap_ahead < 3.0 or (current_lap > total_laps * 0.7 and attack_mode_remaining == 2)
    
    def get_throttle_modifier(self, energy_mode: str) -> float:
        """
        Get throttle modifier based on energy mode.
        
        Args:
            energy_mode: 'push', 'conserve', or 'normal'
            
        Returns:
            Throttle modifier (0.0-1.0)
        """
        if energy_mode == 'push':
            return 1.0
        elif energy_mode == 'conserve':
            return 0.85  # 15% reduction
        else:
            return 1.0

