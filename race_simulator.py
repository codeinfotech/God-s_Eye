"""
Race Simulator Module

Main orchestrator for multi-agent Formula E race simulation.

Manages 10-20 cars simultaneously with time-step based simulation,
race events, overtaking, attack mode, and strategic decisions.

author: Extended from Formula E lap time simulator
date: 2024
"""

import numpy as np
import time
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

# Import existing modules
import sys
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

import laptimesim.src.car_electric as car_electric
import laptimesim.src.track as track
import laptimesim.src.driver as driver
import laptimesim.src.lap as lap

# Import race simulation modules
try:
    from race_sim.race_events import RaceEvents, SafetyCarState
    from race_sim.overtaking import OvertakingModel
    from race_sim.attack_mode import AttackModeManager
except ImportError:
    # Handle relative imports
    from .race_events import RaceEvents, SafetyCarState
    from .overtaking import OvertakingModel
    from .attack_mode import AttackModeManager


@dataclass
class CarState:
    """State of a single car during the race"""
    car_id: int
    position: int  # Race position (1st, 2nd, etc.)
    lap: int
    track_distance: float  # Distance along track in meters
    track_position_normalized: float  # 0.0 to 1.0
    speed: float  # m/s
    energy_remaining: float  # Joules
    race_time: float  # Total race time
    gap_to_leader: float  # seconds
    gap_to_car_ahead: float  # seconds
    gap_to_car_behind: float  # seconds
    lap_times: List[float] = field(default_factory=list)
    is_active: bool = True  # False if crashed/DNF


@dataclass
class RaceState:
    """Current state of the race"""
    race_time: float
    current_lap: int
    leader_id: int
    positions: Dict[int, int]  # car_id -> position
    safety_car_active: bool
    weather_dry: bool
    mu_weather: float


class RaceSimulator:
    """
    Main race simulator for Formula E.
    
    Features:
    - Time-step based simulation (0.1-0.5s steps)
    - 10-20 cars racing simultaneously
    - Race events (safety car, crashes, weather)
    - Overtaking with slipstream
    - Attack Mode management
    - Energy management
    - Position tracking and gaps
    
    Example:
        simulator = RaceSimulator(
            num_cars=20,
            track_name="Berlin",
            race_duration_minutes=45
        )
        results = simulator.run_race()
    """
    
    def __init__(self, num_cars: int = 20, track_name: str = "Berlin",
                 race_duration_minutes: float = 45.0,
                 time_step: float = 0.2, random_seed: Optional[int] = None,
                 repo_path: Optional[str] = None):
        """
        Initialize race simulator.
        
        Args:
            num_cars: Number of cars in race (10-20)
            track_name: Track name (must exist in track_pars.ini)
            race_duration_minutes: Race duration in minutes (45 min + 1 lap)
            time_step: Simulation time step in seconds (0.1-0.5)
            random_seed: Optional random seed
            repo_path: Path to repository root
        """
        self.num_cars = num_cars
        self.track_name = track_name
        self.race_duration_minutes = race_duration_minutes
        self.time_step = time_step
        
        if random_seed is not None:
            np.random.seed(random_seed)
        
        # Get repository path
        if repo_path is None:
            repo_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.repo_path = repo_path
        
        # Initialize track
        self._initialize_track()
        
        # Initialize cars and drivers
        self.cars: Dict[int, car_electric.CarElectric] = {}
        self.drivers: Dict[int, driver.Driver] = {}
        self.laps: Dict[int, lap.Lap] = {}
        self.car_states: Dict[int, CarState] = {}
        
        # Initialize race systems
        self.race_events = RaceEvents(num_cars, self.track.track_length, random_seed)
        self.overtaking = OvertakingModel(self.track.track_length, random_seed)
        self.attack_mode_manager = AttackModeManager(
            num_cars, self.track.track_length, random_seed=random_seed
        )
        
        # Race state
        self.race_state = RaceState(
            race_time=0.0,
            current_lap=0,
            leader_id=0,
            positions={},
            safety_car_active=False,
            weather_dry=True,
            mu_weather=1.0
        )
        
        # Statistics
        self.race_history: List[RaceState] = []
        self.position_history: Dict[int, List[Tuple[float, int]]] = defaultdict(list)
        
        # Performance optimization
        self.use_fast_mode = True  # Use simplified physics for speed
        
    def _initialize_track(self):
        """Initialize track from existing track module."""
        parfilepath = os.path.join(self.repo_path, "laptimesim", "input", "tracks", "track_pars.ini")
        trackfilepath = os.path.join(self.repo_path, "laptimesim", "input", "tracks", "racelines",
                                    self.track_name + ".csv")
        
        track_opts = {
            "trackname": self.track_name,
            "flip_track": False,
            "mu_weather": 1.0,
            "interp_stepsize_des": 5.0,
            "curv_filt_width": 10.0,
            "use_drs1": False,
            "use_drs2": False,
            "use_pit": False
        }
        
        self.track = track.Track(
            pars_track=track_opts,
            parfilepath=parfilepath,
            trackfilepath=trackfilepath,
            vel_lim_glob=225.0 / 3.6  # Formula E speed limit
        )
    
    def _initialize_cars(self):
        """Initialize all cars with slight variations."""
        parfilepath = os.path.join(self.repo_path, "laptimesim", "input", "vehicles", "FE_Berlin.ini")
        
        for car_id in range(self.num_cars):
            # Create car (all use same base parameters)
            car = car_electric.CarElectric(parfilepath=parfilepath)
            
            # Add slight variations for realism
            # Driver skill: ±2% lap time variation
            skill_factor = np.random.uniform(0.98, 1.02)
            car.pars_general["m"] *= skill_factor  # Slight mass variation
            
            # Energy efficiency: ±3%
            efficiency_factor = np.random.uniform(0.97, 1.03)
            car.pars_engine["eta_e_motor"] *= efficiency_factor
            
            self.cars[car_id] = car
            
            # Create driver
            driver_opts = {
                "vel_subtr_corner": 0.5,
                "vel_lim_glob": None,
                "yellow_s1": False,
                "yellow_s2": False,
                "yellow_s3": False,
                "yellow_throttle": 0.3,
                "initial_energy": 4.58e6,  # 4.58 MJ
                "em_strategy": "FCFB",
                "use_recuperation": True,
                "use_lift_coast": False,
                "lift_coast_dist": 10.0
            }
            
            drv = driver.Driver(car, driver_opts, self.track, self.track.stepsize)
            self.drivers[car_id] = drv
            
            # Create lap solver (for reference lap time calculation)
            solver_opts = {
                "vehicle": "FE_Berlin.ini",
                "series": "FE",
                "limit_braking_weak_side": 'FA',
                "v_start": 100.0 / 3.6,
                "find_v_start": True,
                "max_no_em_iters": 5,
                "es_diff_max": 1.0
            }
            
            debug_opts = {
                "use_plot": False,
                "use_debug_plots": False,
                "use_plot_comparison_tph": False,
                "use_print": False,
                "use_print_result": False
            }
            
            lap_obj = lap.Lap(drv, self.track, solver_opts, debug_opts)
            self.laps[car_id] = lap_obj
            
            # Initialize car state
            self.car_states[car_id] = CarState(
                car_id=car_id,
                position=car_id + 1,  # Start in grid order
                lap=0,
                track_distance=0.0,
                track_position_normalized=0.0,
                speed=0.0,
                energy_remaining=4.58e6,
                race_time=0.0,
                gap_to_leader=0.0,
                gap_to_car_ahead=0.0,
                gap_to_car_behind=0.0,
                is_active=True
            )
    
    def run_race(self) -> Dict:
        """
        Run the full race simulation.
        
        Returns:
            Dictionary with race results:
            {
                'final_positions': Dict[car_id, position],
                'final_times': Dict[car_id, race_time],
                'laps_completed': Dict[car_id, laps],
                'event_log': List[events],
                'position_history': Dict[car_id, List[(time, position)]]
            }
        """
        print(f"Starting Formula E race simulation: {self.num_cars} cars on {self.track_name}")
        print(f"Race duration: {self.race_duration_minutes} minutes + 1 lap")
        print(f"Time step: {self.time_step}s")
        
        # Initialize cars
        self._initialize_cars()
        
        # Calculate reference lap time (for performance estimation)
        print("Calculating reference lap time...")
        reference_lap_time = self._calculate_reference_lap_time()
        print(f"Reference lap time: {reference_lap_time:.2f}s")
        
        # Race loop
        max_race_time = self.race_duration_minutes * 60.0
        race_finished = False
        leader_finished = False
        
        start_time = time.perf_counter()
        
        while not race_finished:
            # Update race time
            self.race_state.race_time += self.time_step
            
            # Check if race time limit reached
            if self.race_state.race_time >= max_race_time:
                # Race becomes "time + 1 lap" - leader finishes current lap
                if leader_finished:
                    race_finished = True
                else:
                    leader_finished = True
            
            # Update all systems
            self._update_race_events()
            self._update_cars()
            self._update_positions()
            self._check_overtaking()
            self._update_attack_modes()
            
            # Check for lap completion
            self._check_lap_completion()
            
            # Store history (every 5 seconds to save memory)
            if int(self.race_state.race_time) % 5 == 0:
                self._store_history()
            
            # Progress update
            if int(self.race_state.race_time) % 60 == 0:
                elapsed = time.perf_counter() - start_time
                print(f"Race time: {self.race_state.race_time/60:.1f} min, "
                      f"Simulation time: {elapsed:.1f}s, "
                      f"Leader: Car {self.race_state.leader_id}")
        
        total_time = time.perf_counter() - start_time
        print(f"\nRace finished! Simulation took {total_time:.2f} seconds")
        
        # Compile results
        return self._compile_results()
    
    def _calculate_reference_lap_time(self) -> float:
        """Calculate reference lap time for one car."""
        car_id = 0
        self.laps[car_id].simulate_lap()
        return self.laps[car_id].t_cl[-1]
    
    def _update_race_events(self):
        """Update race events (safety car, crashes, weather)."""
        # Check for new events at lap start
        if hasattr(self, '_last_lap_checked'):
            if self.race_state.current_lap != self._last_lap_checked:
                active_cars = [cid for cid, state in self.car_states.items() if state.is_active]
                events = self.race_events.check_lap_events(
                    self.race_state.current_lap,
                    self.race_state.race_time,
                    active_cars
                )
                
                # Handle crashes
                for crashed_id in events['crashes']:
                    self.car_states[crashed_id].is_active = False
                
                # Update weather
                if events['weather_changed']:
                    self.race_state.mu_weather = events['new_mu_weather']
                    # Update track friction
                    self.track.mu = self.track.mu * (events['new_mu_weather'] / self.track.pars_track["mu_weather"])
                    self.track.pars_track["mu_weather"] = events['new_mu_weather']
                
                self._last_lap_checked = self.race_state.current_lap
        else:
            self._last_lap_checked = 0
        
        # Update safety car
        self.race_events.update_safety_car(self.race_state.current_lap)
        self.race_state.safety_car_active = self.race_events.safety_car_active
    
    def _update_cars(self):
        """Update all car states (simplified physics for speed)."""
        safety_car_speed = self.race_events.get_safety_car_speed()
        
        for car_id, state in self.car_states.items():
            if not state.is_active:
                continue
            
            # Simplified speed update (for performance)
            # In full implementation, would use lap solver for each car
            if self.race_state.safety_car_active:
                # Follow safety car speed
                state.speed = min(state.speed, safety_car_speed)
            else:
                # Normal racing speed (simplified)
                # Use reference velocity profile with variations
                track_idx = int(state.track_distance / self.track.stepsize) % self.track.no_points
                reference_speed = 50.0  # Simplified: average speed
                
                # Add variation based on car performance
                skill_factor = self.cars[car_id].pars_general["m"] / 880.0  # Normalized
                state.speed = reference_speed * (1.0 + (1.0 - skill_factor) * 0.1)
            
            # Update track position
            state.track_distance += state.speed * self.time_step
            state.track_distance = state.track_distance % self.track.track_length
            state.track_position_normalized = state.track_distance / self.track.track_length
            
            # Update energy (simplified consumption)
            power_kw = self.attack_mode_manager.get_power_kw(car_id)
            energy_consumed = (power_kw * 1000.0 * self.time_step) / 0.9  # Account for efficiency
            state.energy_remaining -= energy_consumed
            
            # Check if energy depleted
            if state.energy_remaining <= 0:
                state.is_active = False
                state.energy_remaining = 0.0
    
    def _update_positions(self):
        """Update race positions based on track distance and lap."""
        # Sort cars by position: lap (descending), then track_distance (descending)
        sorted_cars = sorted(
            self.car_states.items(),
            key=lambda x: (x[1].lap, x[1].track_distance),
            reverse=True
        )
        
        # Update positions
        for position, (car_id, state) in enumerate(sorted_cars, 1):
            state.position = position
            self.race_state.positions[car_id] = position
        
        # Update leader
        if sorted_cars:
            self.race_state.leader_id = sorted_cars[0][0]
        
        # Calculate gaps
        self._calculate_gaps()
    
    def _calculate_gaps(self):
        """Calculate time gaps between cars."""
        leader_state = self.car_states[self.race_state.leader_id]
        
        for car_id, state in self.car_states.items():
            if not state.is_active:
                continue
            
            # Gap to leader
            if car_id == self.race_state.leader_id:
                state.gap_to_leader = 0.0
            else:
                # Simplified gap calculation
                lap_diff = leader_state.lap - state.lap
                dist_diff = leader_state.track_distance - state.track_distance
                if dist_diff < 0:
                    dist_diff += self.track.track_length
                state.gap_to_leader = (lap_diff * self.track.track_length + dist_diff) / state.speed if state.speed > 0 else 999.0
            
            # Gap to car ahead/behind (simplified)
            state.gap_to_car_ahead = 0.5  # Placeholder
            state.gap_to_car_behind = 0.5  # Placeholder
    
    def _check_overtaking(self):
        """Check and execute overtaking attempts."""
        # Simplified: check adjacent cars
        sorted_cars = sorted(
            [(cid, s) for cid, s in self.car_states.items() if s.is_active],
            key=lambda x: (x[1].lap, x[1].track_distance),
            reverse=True
        )
        
        for i in range(len(sorted_cars) - 1):
            attacker_id, attacker_state = sorted_cars[i + 1]
            defender_id, defender_state = sorted_cars[i]
            
            # Check if close enough to attempt overtake
            gap_seconds = (defender_state.track_distance - attacker_state.track_distance) / attacker_state.speed if attacker_state.speed > 0 else 999.0
            
            if 0 < gap_seconds < 2.0:  # Within 2 seconds
                result = self.overtaking.attempt_overtake(
                    attacker_id=attacker_id,
                    defender_id=defender_id,
                    attacker_speed=attacker_state.speed,
                    defender_speed=defender_state.speed,
                    gap_seconds=gap_seconds,
                    track_position=attacker_state.track_position_normalized,
                    attacker_has_attack_mode=self.attack_mode_manager.is_active(attacker_id),
                    defender_has_attack_mode=self.attack_mode_manager.is_active(defender_id),
                    timestamp=self.race_state.race_time
                )
                
                if result['success']:
                    # Swap positions (simplified)
                    attacker_state.position, defender_state.position = \
                        defender_state.position, attacker_state.position
    
    def _update_attack_modes(self):
        """Update all Attack Mode states."""
        self.attack_mode_manager.update_all(self.race_state.race_time)
    
    def _check_lap_completion(self):
        """Check if any car completed a lap."""
        for car_id, state in self.car_states.items():
            if not state.is_active:
                continue
            
            # Check if crossed start/finish line
            if state.track_distance < self.time_step * state.speed:
                state.lap += 1
                if state.lap > self.race_state.current_lap:
                    self.race_state.current_lap = state.lap
    
    def _store_history(self):
        """Store current race state in history."""
        self.race_history.append(RaceState(
            race_time=self.race_state.race_time,
            current_lap=self.race_state.current_lap,
            leader_id=self.race_state.leader_id,
            positions=self.race_state.positions.copy(),
            safety_car_active=self.race_state.safety_car_active,
            weather_dry=self.race_events.weather_dry,
            mu_weather=self.race_state.mu_weather
        ))
        
        # Store position history
        for car_id, state in self.car_states.items():
            self.position_history[car_id].append((self.race_state.race_time, state.position))
    
    def _compile_results(self) -> Dict:
        """Compile final race results."""
        # Sort by final position
        final_order = sorted(
            self.car_states.items(),
            key=lambda x: x[1].position
        )
        
        results = {
            'final_positions': {car_id: state.position for car_id, state in final_order},
            'final_times': {car_id: state.race_time for car_id, state in final_order},
            'laps_completed': {car_id: state.lap for car_id, state in final_order},
            'event_log': self.race_events.get_events_log(),
            'position_history': dict(self.position_history),
            'overtaking_stats': self.overtaking.get_overtaking_statistics(),
            'race_events_summary': self.race_events.get_event_summary()
        }
        
        return results


# Example usage
if __name__ == "__main__":
    simulator = RaceSimulator(
        num_cars=10,
        track_name="Berlin",
        race_duration_minutes=5.0,  # Short test race
        time_step=0.5,
        random_seed=42
    )
    
    results = simulator.run_race()
    
    print("\nFinal Results:")
    for car_id, position in sorted(results['final_positions'].items(), key=lambda x: x[1]):
        print(f"P{position}: Car {car_id} - {results['laps_completed'][car_id]} laps")

