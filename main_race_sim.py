#!/usr/bin/env python3
"""
FORMULA E COMPLETE SIMULATOR + MONTE CARLO STRATEGY OPTIMIZER v1.0
================================================================================
Single file with:
- Full Formula E multi-agent race simulator
- Monte Carlo strategy optimization
- Attack mode timing optimization
- Pit window analysis
- Energy management strategies
- Real uncertainties (weather, crashes, safety car)
- 1000+ race simulations for pre-race planning
================================================================================
Copy-paste and run directly: python formula_e_complete.py
"""

import sys
import os
import numpy as np
import json
from collections import defaultdict
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Tuple
import time


# ============================================================================
# STRATEGY CONFIGS
# ============================================================================

@dataclass
class StrategyConfig:
    """Strategy configuration for a driver."""
    name: str
    target_speed_factor: float
    attack_mode_threshold: float
    pit_window_start: int
    pit_window_end: int
    tire_change_strategy: str
    energy_reserve: float


# Define base strategies
AGGRESSIVE_STRATEGY = StrategyConfig(
    name='aggressive',
    target_speed_factor=1.08,
    attack_mode_threshold=50.0,
    pit_window_start=15,
    pit_window_end=35,
    tire_change_strategy='early',
    energy_reserve=5.0
)

BALANCED_STRATEGY = StrategyConfig(
    name='balanced',
    target_speed_factor=1.00,
    attack_mode_threshold=60.0,
    pit_window_start=20,
    pit_window_end=40,
    tire_change_strategy='mid',
    energy_reserve=10.0
)

CONSERVATIVE_STRATEGY = StrategyConfig(
    name='conservative',
    target_speed_factor=0.92,
    attack_mode_threshold=70.0,
    pit_window_start=25,
    pit_window_end=45,
    tire_change_strategy='late',
    energy_reserve=15.0
)

STRATEGY_COLORS = {
    'aggressive': '#FF1744',
    'balanced': '#2196F3',
    'conservative': '#4CAF50'
}


# ============================================================================
# FORMULA E SIMULATOR
# ============================================================================

class FormulaEStrategySimulator:
    """Complete Formula E race simulator."""
    
    def __init__(
        self,
        num_cars: int = 10,
        race_duration_minutes: float = 90.0,
        time_step: float = 0.5,
        track_length: float = 5341,
        random_seed: int = None
    ):
        """Initialize simulator."""
        assert 1 <= num_cars <= 10, "Must have 1-10 cars"
        
        self.num_cars = num_cars
        self.race_duration = race_duration_minutes * 60.0
        self.time_step = time_step
        self.track_length = track_length
        
        if random_seed is None:
            random_seed = int(datetime.now().timestamp() * 1000) % 100000
        
        self.random_seed = random_seed
        np.random.seed(random_seed)
        
        self.cars = []
        self.race_state = {}
        self.event_log = []
        
        self._initialize()
    
    def _initialize(self):
        """Initialize race."""
        strategies = [
            AGGRESSIVE_STRATEGY,
            BALANCED_STRATEGY,
            CONSERVATIVE_STRATEGY,
            BALANCED_STRATEGY,
            AGGRESSIVE_STRATEGY,
            CONSERVATIVE_STRATEGY,
            BALANCED_STRATEGY,
            AGGRESSIVE_STRATEGY,
            CONSERVATIVE_STRATEGY,
            BALANCED_STRATEGY
        ]
        
        for car_id in range(self.num_cars):
            strategy = strategies[car_id] if car_id < len(strategies) else BALANCED_STRATEGY
            
            self.cars.append({
                'id': car_id,
                'position': car_id + 1,
                'lap': 0,
                'distance': 0.0,
                'speed': 0.0,
                'energy': 52.0,
                'tire_age': 0,
                'tire_degradation': 0.0,
                'pitted': False,
                'pit_count': 0,
                'attack_mode_uses': 0,
                'attack_mode_active': False,
                'attack_mode_end_time': 0.0,
                'strategy': strategy,
                'total_time': 0.0,
                'active': True,
                'dnf_reason': None,
                'lap_times': [],
                'energy_history': [52.0],
                'position_history': [car_id + 1],
                'lap_history': [0],
                'speed_history': [0.0],
                'attack_mode_lap_config': None,
                'pit_window_config': None
            })
        
        self.race_state = {
            'time': 0.0,
            'lap': 0,
            'safety_car_active': False,
            'safety_car_end_time': 0.0,
            'weather': 'dry',
            'friction': 1.0
        }
    
    def run_race(self, verbose: bool = False) -> Dict:
        """Run complete race."""
        if verbose:
            print(f"{'='*80}")
            print(f"🏁 LIGHTS OUT AND AWAY WE GO!")
            print(f"{'='*80}\n")
        
        start_time = time.time()
        last_print = 0.0
        
        while self.race_state['time'] < self.race_duration:
            self.race_state['time'] += self.time_step
            
            for car in self.cars:
                if car['active']:
                    self._update_car(car)
            
            self._check_events()
            self._update_positions()
            
            if self.race_state['time'] - last_print >= 600.0 and verbose:
                self._print_progress()
                last_print = self.race_state['time']
        
        sim_duration = time.time() - start_time
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"🏁 CHEQUERED FLAG!")
            print(f"{'='*80}\n")
        
        return self._compile_results(sim_duration)
    
    def _update_car(self, car: Dict):
        """Update single car state."""
        base_speed = self.track_length / 31.0
        base_speed *= car['strategy'].target_speed_factor
        
        tire_penalty = 1.0 - (car['tire_degradation'] * 0.6)
        base_speed *= tire_penalty
        
        energy_factor = max(0.5, car['energy'] / 52.0)
        base_speed *= energy_factor
        
        base_speed *= np.sqrt(self.race_state['friction'])
        
        if car['attack_mode_active']:
            base_speed *= 1.10
            if self.race_state['time'] >= car['attack_mode_end_time']:
                car['attack_mode_active'] = False
        
        if self.race_state['safety_car_active']:
            base_speed = min(base_speed, 80.0 / 3.6)
        
        car['speed'] = base_speed
        car['speed_history'].append(car['speed'])
        car['distance'] += car['speed'] * self.time_step
        car['total_time'] += self.time_step
        
        if car['distance'] >= self.track_length:
            car['distance'] -= self.track_length
            car['lap'] += 1
            car['lap_history'].append(car['lap'])
            car['tire_age'] += 1
            car['lap_times'].append(car['total_time'])
            
            self._try_pit(car)
            self._try_attack_mode(car)
        
        car['tire_degradation'] += 0.0006 * (car['speed'] / 50.0)
        car['tire_degradation'] = min(1.0, car['tire_degradation'])
        
        consumption = 0.30 * (car['speed'] / 50.0) * (1.0 + car['tire_degradation'] * 0.5)
        
        if car['attack_mode_active']:
            consumption *= 1.5
        
        if car['strategy'].name == 'aggressive':
            consumption *= 1.2
        elif car['strategy'].name == 'conservative':
            consumption *= 0.8
        
        car['energy'] -= consumption * (self.time_step / 60.0)
        car['energy_history'].append(max(0, car['energy']))
        
        if car['energy'] < 1.0 and not car['pitted']:
            car['active'] = False
            car['dnf_reason'] = 'out_of_energy'
    
    def _try_pit(self, car: Dict):
        """Attempt pit stop."""
        pit_window_start = car['strategy'].pit_window_start
        pit_window_end = car['strategy'].pit_window_end
        
        if car['pit_window_config']:
            pit_window_start = car['pit_window_config']['start']
            pit_window_end = car['pit_window_config']['end']
        
        should_pit = False
        
        if car['lap'] == pit_window_start:
            should_pit = True
        elif car['energy'] < car['strategy'].energy_reserve and not car['pitted']:
            should_pit = True
        
        if should_pit and pit_window_start <= car['lap'] <= pit_window_end and not car['pitted']:
            car['pitted'] = True
            car['pit_count'] += 1
            car['energy'] = 52.0
            car['tire_degradation'] = 0.0
            car['tire_age'] = 0
            car['total_time'] += 25.0
    
    def _try_attack_mode(self, car: Dict):
        """Attempt attack mode activation."""
        if car['attack_mode_uses'] >= 2:
            return
        
        if car['attack_mode_lap_config']:
            target_lap = car['attack_mode_lap_config']
            if car['lap'] == target_lap and car['energy'] > car['strategy'].attack_mode_threshold:
                car['attack_mode_active'] = True
                car['attack_mode_end_time'] = self.race_state['time'] + np.random.uniform(8, 12)
                car['attack_mode_uses'] += 1
        else:
            if car['energy'] > car['strategy'].attack_mode_threshold:
                if np.random.random() < 0.35:
                    car['attack_mode_active'] = True
                    car['attack_mode_end_time'] = self.race_state['time'] + np.random.uniform(8, 12)
                    car['attack_mode_uses'] += 1
    
    def _check_events(self):
        """Check for random race events."""
        active_cars = [c for c in self.cars if c['active']]
        
        if len(active_cars) == 0:
            return
        
        if np.random.random() < 0.0003 and self.race_state['weather'] == 'dry':
            self.race_state['weather'] = 'wet'
            self.race_state['friction'] = 0.70
            self.event_log.append({
                'time': self.race_state['time'],
                'type': 'weather',
                'condition': 'rain'
            })
        
        if (np.random.random() < 0.00005 and 
            not self.race_state['safety_car_active'] and 
            len(active_cars) > 1):
            
            self.race_state['safety_car_active'] = True
            self.race_state['safety_car_end_time'] = self.race_state['time'] + np.random.uniform(120, 300)
            
            self.event_log.append({
                'time': self.race_state['time'],
                'type': 'safety_car'
            })
        
        if np.random.random() < 0.00001 and len(active_cars) > 1:
            victim = np.random.choice(active_cars)
            victim['active'] = False
            victim['dnf_reason'] = 'crash'
            
            self.event_log.append({
                'time': self.race_state['time'],
                'type': 'crash',
                'car_id': victim['id']
            })
        
        if (self.race_state['safety_car_active'] and 
            self.race_state['time'] >= self.race_state['safety_car_end_time']):
            self.race_state['safety_car_active'] = False
    
    def _update_positions(self):
        """Update race positions."""
        active_cars = [c for c in self.cars if c['active']]
        
        if len(active_cars) == 0:
            return
        
        active_cars.sort(key=lambda x: (-x['lap'], -x['distance']))
        
        for rank, car in enumerate(active_cars):
            car['position'] = rank + 1
            car['position_history'].append(car['position'])
        
        dnf_cars = [c for c in self.cars if not c['active']]
        for rank, car in enumerate(dnf_cars):
            car['position'] = len(active_cars) + rank + 1
    
    def _print_progress(self):
        """Print race progress."""
        active_cars = [c for c in self.cars if c['active']]
        
        if len(active_cars) == 0:
            return
        
        leader = sorted(active_cars, key=lambda x: (-x['lap'], -x['distance']))[0]
        
        print(f"  ⏱️  {self.race_state['time']/60:5.1f}m | "
              f"Leader: Car {leader['id']} ({leader['strategy'].name:12s}) | "
              f"Lap {leader['lap']:2d} | Energy: {leader['energy']:5.1f}% | "
              f"Weather: {self.race_state['weather']:5s} | "
              f"Cars: {len(active_cars)}/{self.num_cars}")
    
    def _compile_results(self, sim_duration: float) -> Dict:
        """Compile race results."""
        active_cars = [c for c in self.cars if c['active']]
        final_standings = sorted(
            self.cars,
            key=lambda x: (not x['active'], -x['lap'], -x['distance'])
        )
        
        results_data = []
        
        for pos, car in enumerate(final_standings, 1):
            status = 'Finished' if car['active'] else f"DNF ({car['dnf_reason']})"
            
            results_data.append({
                'position': pos,
                'car_id': car['id'],
                'strategy': car['strategy'].name,
                'laps_completed': car['lap'],
                'final_energy': car['energy'],
                'pit_stops': car['pit_count'],
                'attack_mode_uses': car['attack_mode_uses'],
                'final_status': status,
                'avg_lap_time': np.mean(car['lap_times']) if car['lap_times'] else 0.0
            })
        
        strategy_stats = {}
        for strategy_name in ['aggressive', 'balanced', 'conservative']:
            cars_with_strategy = [c for c in self.cars if c['strategy'].name == strategy_name]
            
            if cars_with_strategy:
                active_strategy_cars = [c for c in cars_with_strategy if c['active']]
                
                avg_position = np.mean([c['position'] for c in cars_with_strategy]) if cars_with_strategy else 0
                avg_laps = np.mean([c['lap'] for c in cars_with_strategy])
                avg_pits = np.mean([c['pit_count'] for c in cars_with_strategy])
                avg_energy = np.mean([c['energy'] for c in cars_with_strategy])
                avg_attack_uses = np.mean([c['attack_mode_uses'] for c in cars_with_strategy])
                dnf_count = sum(1 for c in cars_with_strategy if not c['active'])
                
                strategy_stats[strategy_name] = {
                    'avg_position': avg_position,
                    'avg_laps': avg_laps,
                    'avg_pits': avg_pits,
                    'avg_final_energy': avg_energy,
                    'avg_attack_uses': avg_attack_uses,
                    'dnf_count': dnf_count,
                    'finisher_count': len(active_strategy_cars),
                    'total_cars': len(cars_with_strategy)
                }
        
        best_strategy = max(
            strategy_stats.items(),
            key=lambda x: (x[1]['finisher_count'], -x[1]['avg_position'])
        )[0] if strategy_stats else 'unknown'
        
        return {
            'final_standings': results_data,
            'strategy_comparison': strategy_stats,
            'best_strategy': best_strategy,
            'cars': self.cars,
            'events': self.event_log,
            'simulation_time': sim_duration,
            'random_seed': self.random_seed,
            'crashes': sum(1 for e in self.event_log if e['type'] == 'crash'),
            'safety_cars': sum(1 for e in self.event_log if e['type'] == 'safety_car'),
            'weather_changes': sum(1 for e in self.event_log if e['type'] == 'weather'),
            'dnfs': sum(1 for c in self.cars if not c['active']),
            'finishers': sum(1 for c in self.cars if c['active'])
        }


# ============================================================================
# MONTE CARLO STRATEGY OPTIMIZER
# ============================================================================

class MonteCarloStrategyOptimizer:
    """Monte Carlo simulation for finding optimal strategies."""
    
    def __init__(self, num_simulations: int = 1000):
        """Initialize optimizer."""
        self.num_simulations = num_simulations
        self.results = []
        self.statistics = {}
    
    def run_optimization(self, 
                         test_attack_mode_laps: List[int] = None,
                         test_pit_windows: List[Tuple[int, int]] = None,
                         verbose: bool = True) -> Dict:
        """
        Run Monte Carlo optimization over attack mode laps and pit windows.
        """
        
        if test_attack_mode_laps is None:
            test_attack_mode_laps = list(range(15, 55, 5))
        
        if test_pit_windows is None:
            test_pit_windows = [(15, 35), (20, 40), (25, 45)]
        
        if verbose:
            print("\n" + "="*80)
            print("🚀 MONTE CARLO STRATEGY OPTIMIZER")
            print("="*80)
            print(f"Number of simulations: {self.num_simulations}")
            print(f"Attack mode laps to test: {test_attack_mode_laps}")
            print(f"Pit windows to test: {test_pit_windows}")
            print("="*80 + "\n")
        
        config_stats = defaultdict(list)
        attack_mode_effectiveness = defaultdict(list)
        pit_strategy_effectiveness = defaultdict(list)
        
        total_runs = len(test_attack_mode_laps) * len(test_pit_windows) * self.num_simulations
        run_count = 0
        
        start_time = time.time()
        
        for am_lap in test_attack_mode_laps:
            for pit_start, pit_end in test_pit_windows:
                for sim_idx in range(self.num_simulations):
                    run_count += 1
                    
                    if verbose and run_count % 100 == 0:
                        elapsed = time.time() - start_time
                        rate = run_count / elapsed if elapsed > 0 else 1
                        eta = (total_runs - run_count) / rate if rate > 0 else 0
                        print(f"Progress: {run_count}/{total_runs} "
                              f"({100*run_count/total_runs:.1f}%) | "
                              f"ETA: {eta:.0f}s")
                    
                    sim = FormulaEStrategySimulator(
                        num_cars=10,
                        race_duration_minutes=90.0,
                        random_seed=None
                    )
                    
                    for car in sim.cars:
                        car['attack_mode_lap_config'] = am_lap
                        car['pit_window_config'] = {
                            'start': pit_start,
                            'end': pit_end
                        }
                    
                    race_results = sim.run_race(verbose=False)
                    
                    config_key = (am_lap, pit_start, pit_end)
                    
                    for car in race_results['cars']:
                        config_stats[config_key].append({
                            'position': car['position'],
                            'laps': car['lap'],
                            'attack_uses': car['attack_mode_uses'],
                            'energy': car['energy'],
                            'strategy': car['strategy'].name
                        })
                        
                        if car['attack_mode_uses'] > 0:
                            attack_mode_effectiveness[am_lap].append(
                                1 if car['position'] <= 3 else 0
                            )
                        
                        pit_key = (pit_start, pit_end)
                        pit_strategy_effectiveness[pit_key].append(
                            1 if car['position'] <= 5 else 0
                        )
        
        return self._compile_optimization_report(
            config_stats,
            attack_mode_effectiveness,
            pit_strategy_effectiveness,
            test_attack_mode_laps,
            test_pit_windows,
            verbose
        )
    
    def _compile_optimization_report(self,
                                     config_stats: Dict,
                                     attack_mode_effectiveness: Dict,
                                     pit_strategy_effectiveness: Dict,
                                     test_attack_mode_laps: List[int],
                                     test_pit_windows: List[Tuple[int, int]],
                                     verbose: bool) -> Dict:
        """Compile optimization report with recommendations."""
        
        print("\n" + "="*80)
        print("📊 OPTIMIZATION RESULTS")
        print("="*80 + "\n")
        
        print("ATTACK MODE LAP EFFECTIVENESS:")
        print("-" * 80)
        best_am_lap = None
        best_am_rate = 0
        
        for lap in sorted(attack_mode_effectiveness.keys()):
            results = attack_mode_effectiveness[lap]
            if results:
                success_rate = np.mean(results)
                print(f"  Lap {lap:2d}: Top-3 rate {100*success_rate:5.1f}% ({len(results)} cars tested)")
                
                if success_rate > best_am_rate:
                    best_am_rate = success_rate
                    best_am_lap = lap
        
        print(f"\n  ✅ RECOMMENDED ATTACK MODE LAP: {best_am_lap} (Success rate: {100*best_am_rate:.1f}%)\n")
        
        print("PIT WINDOW EFFECTIVENESS:")
        print("-" * 80)
        best_pit_window = None
        best_pit_rate = 0
        
        for (pit_start, pit_end) in sorted(pit_strategy_effectiveness.keys()):
            results = pit_strategy_effectiveness[(pit_start, pit_end)]
            if results:
                success_rate = np.mean(results)
                print(f"  Laps {pit_start:2d}-{pit_end:2d}: Top-5 rate {100*success_rate:5.1f}% ({len(results)} cars tested)")
                
                if success_rate > best_pit_rate:
                    best_pit_rate = success_rate
                    best_pit_window = (pit_start, pit_end)
        
        print(f"\n  ✅ RECOMMENDED PIT WINDOW: Laps {best_pit_window[0]}-{best_pit_window[1]} "
              f"(Success rate: {100*best_pit_rate:.1f}%)\n")
        
        print("BEST CONFIGURATION OVERALL:")
        print("-" * 80)
        
        best_config = max(
            config_stats.items(),
            key=lambda x: np.mean([1 if r['position'] <= 3 else 0 for r in x[1]])
        )
        
        config_key, results = best_config
        am_lap, pit_start, pit_end = config_key
        top3_rate = np.mean([1 if r['position'] <= 3 else 0 for r in results])
        avg_position = np.mean([r['position'] for r in results])
        
        print(f"  Attack Mode Lap: {am_lap}")
        print(f"  Pit Window: Laps {pit_start}-{pit_end}")
        print(f"  Top-3 Finish Rate: {100*top3_rate:.1f}%")
        print(f"  Average Finishing Position: {avg_position:.2f}")
        print(f"  Sample Size: {len(results)} drivers")
        
        print("\n" + "="*80 + "\n")
        
        return {
            'best_attack_mode_lap': best_am_lap,
            'attack_mode_success_rate': best_am_rate,
            'best_pit_window': best_pit_window,
            'pit_window_success_rate': best_pit_rate,
            'best_configuration': {
                'attack_mode_lap': am_lap,
                'pit_window_start': pit_start,
                'pit_window_end': pit_end,
                'top3_finish_rate': top3_rate,
                'avg_finishing_position': avg_position
            },
            'all_config_stats': dict(config_stats),
            'attack_mode_stats': dict(attack_mode_effectiveness),
            'pit_strategy_stats': dict(pit_strategy_effectiveness)
        }
    
    def save_report(self, report: Dict, filename: str = None) -> str:
        """Save optimization report to JSON."""
        if filename is None:
            filename = f"mc_optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        def convert_keys(obj):
            """Recursively convert tuple keys to strings."""
            if isinstance(obj, dict):
                new_dict = {}
                for key, value in obj.items():
                    if isinstance(key, tuple):
                        new_key = f"{key[0]}_{key[1]}" if len(key) == 2 else str(key)
                    else:
                        new_key = key
                    new_dict[new_key] = convert_keys(value)
                return new_dict
            elif isinstance(obj, list):
                return [convert_keys(item) for item in obj]
            else:
                return obj
        
        report_copy = convert_keys(report)
        report_copy['best_pit_window'] = list(report_copy['best_pit_window'])
        report_copy['best_configuration']['pit_window_start'] = int(report_copy['best_configuration']['pit_window_start'])
        report_copy['best_configuration']['pit_window_end'] = int(report_copy['best_configuration']['pit_window_end'])
        
        with open(filename, 'w') as f:
            json.dump(report_copy, f, indent=2, default=str)
        
        print(f"✅ Report saved to: {filename}\n")
        return filename


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run complete strategy optimization pipeline."""
    
    print("\n" + "="*80)
    print("FORMULA E COMPLETE SIMULATOR + MONTE CARLO OPTIMIZER")
    print("="*80 + "\n")
    
    # Run optimizer
    print("PHASE 1: Monte Carlo Strategy Search")
    print("-" * 80)
    
    optimizer = MonteCarloStrategyOptimizer(num_simulations=50)  # Change to 1000 for full optimization
    
    report = optimizer.run_optimization(
        test_attack_mode_laps=list(range(15, 55, 5)),
        test_pit_windows=[(15, 35), (20, 40), (25, 45), (18, 38)],
        verbose=True
    )
    
    optimizer.save_report(report)
    
    # Run demo race with optimized config
    print("\n" + "="*80)
    print("PHASE 2: Demo Race with Optimized Configuration")
    print("="*80 + "\n")
    
    demo_sim = FormulaEStrategySimulator(
        num_cars=10,
        race_duration_minutes=90.0,
        random_seed=42
    )
    
    best_am_lap = report['best_attack_mode_lap']
    best_pit_window = report['best_pit_window']
    
    for car in demo_sim.cars:
        car['attack_mode_lap_config'] = best_am_lap
        car['pit_window_config'] = {
            'start': best_pit_window[0],
            'end': best_pit_window[1]
        }
    
    print(f"Using optimized configuration:")
    print(f"  Attack Mode Lap: {best_am_lap}")
    print(f"  Pit Window: Laps {best_pit_window[0]}-{best_pit_window[1]}\n")
    
    demo_results = demo_sim.run_race(verbose=True)
    
    # Print final results
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    print(f"  Finishers: {demo_results['finishers']}/{demo_sim.num_cars}")
    print(f"  DNFs: {demo_results['dnfs']}")
    print(f"  Crashes: {demo_results['crashes']}")
    print(f"  Safety Cars: {demo_results['safety_cars']}")
    print(f"  Weather Changes: {demo_results['weather_changes']}")
    print(f"  Best Strategy: {demo_results['best_strategy'].upper()}")
    print(f"  Simulation Time: {demo_results['simulation_time']:.2f}s")
    print("="*80 + "\n")
    
    # Print leaderboard
    print("\n" + "="*80)
    print("🏆 FINAL CLASSIFICATION")
    print("="*80 + "\n")
    print(f"{'Pos':<5} {'Car':<5} {'Strategy':<15} {'Laps':<6} {'Energy':<10} {'Status':<20}")
    print("-" * 70)
    
    for result in demo_results['final_standings']:
        print(f"P{result['position']:<4} {result['car_id']:<5} {result['strategy']:<15} "
              f"{result['laps_completed']:<6} {result['final_energy']:>8.2f}% {result['final_status']:<20}")
    
    print("\n" + "="*80 + "\n")
    
    return report


if __name__ == "__main__":
    try:
        report = main()
        print("✅ Complete optimization and demo finished!")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)