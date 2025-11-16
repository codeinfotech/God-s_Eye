"""
Race Strategy Optimizer Module

Pre-race strategy planning using Monte Carlo simulation.
Optimizes Attack Mode timing, energy management, and race strategy.

author: Extended from Formula E lap time simulator
date: 2024
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import time


@dataclass
class Strategy:
    """Represents a race strategy"""
    attack_mode_lap_1: Optional[int]  # First attack mode activation lap
    attack_mode_lap_2: Optional[int]  # Second attack mode activation lap
    energy_mode: str  # 'aggressive', 'balanced', 'conservative'
    overtaking_aggression: str  # 'conservative', 'neutral', 'aggressive'
    safety_car_response: str  # 'push', 'conserve', 'neutral'


@dataclass
class StrategyResult:
    """Results from a strategy simulation"""
    strategy: Strategy
    avg_finish_position: float
    win_rate: float
    top3_rate: float
    avg_energy_remaining: float
    consistency_score: float  # Lower std dev = more consistent


class RaceStrategyOptimizer:
    """
    Optimizes race strategies using Monte Carlo simulation.
    
    Runs multiple race simulations with different strategies to find
    optimal Attack Mode timing, energy management, and race approach.
    
    Example:
        optimizer = RaceStrategyOptimizer(
            num_cars=20,
            track_name="Berlin",
            race_duration_minutes=45.0
        )
        
        best_strategy = optimizer.optimize_attack_mode_timing(
            num_simulations=100,
            target_position=1  # Optimize for win
        )
    """
    
    def __init__(self, num_cars: int, track_name: str,
                 race_duration_minutes: float = 45.0,
                 random_seed: Optional[int] = None):
        """
        Initialize strategy optimizer.
        
        Args:
            num_cars: Number of cars in race
            track_name: Track name
            race_duration_minutes: Race duration
            random_seed: Optional random seed
        """
        self.num_cars = num_cars
        self.track_name = track_name
        self.race_duration_minutes = race_duration_minutes
        
        if random_seed is not None:
            np.random.seed(random_seed)
        
        # Strategy parameters
        self.attack_mode_duration = 240.0  # 4 minutes in seconds
        self.typical_lap_time = 90.0  # seconds (will be calculated from track)
        self.total_laps = int((race_duration_minutes * 60.0) / self.typical_lap_time) + 1
        
    def generate_strategy_candidates(self, num_strategies: int = 20) -> List[Strategy]:
        """
        Generate candidate strategies to test.
        
        Args:
            num_strategies: Number of strategies to generate
            
        Returns:
            List of Strategy objects
        """
        strategies = []
        
        # Generate different attack mode timing strategies
        for i in range(num_strategies):
            # Early, mid, late race attack mode activations
            if i < num_strategies // 3:
                # Early strategy: use attack mode early
                lap_1 = np.random.randint(2, self.total_laps // 3)
                lap_2 = np.random.randint(lap_1 + 3, self.total_laps // 2)
            elif i < 2 * num_strategies // 3:
                # Mid strategy: use attack mode in middle
                lap_1 = np.random.randint(self.total_laps // 3, 2 * self.total_laps // 3)
                lap_2 = np.random.randint(lap_1 + 3, 2 * self.total_laps // 3 + 5)
            else:
                # Late strategy: save attack mode for end
                lap_1 = np.random.randint(2 * self.total_laps // 3, self.total_laps - 5)
                lap_2 = np.random.randint(lap_1 + 2, self.total_laps - 2)
            
            # Energy management modes
            energy_modes = ['aggressive', 'balanced', 'conservative']
            energy_mode = energy_modes[i % len(energy_modes)]
            
            # Overtaking aggression
            overtaking_modes = ['conservative', 'neutral', 'aggressive']
            overtaking_aggression = overtaking_modes[(i // 2) % len(overtaking_modes)]
            
            # Safety car response
            sc_responses = ['push', 'conserve', 'neutral']
            safety_car_response = sc_responses[(i // 3) % len(sc_responses)]
            
            strategy = Strategy(
                attack_mode_lap_1=lap_1,
                attack_mode_lap_2=lap_2,
                energy_mode=energy_mode,
                overtaking_aggression=overtaking_aggression,
                safety_car_response=safety_car_response
            )
            
            strategies.append(strategy)
        
        return strategies
    
    def simulate_strategy(self, strategy: Strategy, num_simulations: int = 100,
                         car_id: int = 0) -> StrategyResult:
        """
        Simulate a strategy multiple times using Monte Carlo.
        
        Args:
            strategy: Strategy to test
            num_simulations: Number of race simulations to run
            car_id: Car ID to optimize for
            
        Returns:
            StrategyResult with average performance metrics
        """
        finish_positions = []
        energy_remaining = []
        wins = 0
        top3 = 0
        
        # Simplified simulation (would use full RaceSimulator in production)
        for sim in range(num_simulations):
            # Simulate race outcome based on strategy
            # This is a simplified model - in full implementation would run actual race
            
            # Base performance
            base_position = np.random.randint(1, self.num_cars + 1)
            
            # Attack mode advantage
            am_advantage = 0
            if strategy.attack_mode_lap_1 is not None:
                # Early attack mode: helps in first half
                if strategy.attack_mode_lap_1 < self.total_laps // 2:
                    am_advantage += np.random.uniform(1, 3)  # 1-3 position gain
                else:
                    am_advantage += np.random.uniform(0.5, 2)  # 0.5-2 position gain
            
            if strategy.attack_mode_lap_2 is not None:
                # Late attack mode: helps in final stages
                if strategy.attack_mode_lap_2 > 2 * self.total_laps // 3:
                    am_advantage += np.random.uniform(1.5, 3.5)  # 1.5-3.5 position gain
                else:
                    am_advantage += np.random.uniform(0.5, 2)
            
            # Energy mode effect
            energy_bonus = 0
            if strategy.energy_mode == 'conservative':
                energy_bonus = np.random.uniform(0, 1)  # Better energy = fewer issues
            elif strategy.energy_mode == 'aggressive':
                energy_bonus = np.random.uniform(-1, 0)  # May run out of energy
            
            # Calculate final position
            final_position = max(1, min(self.num_cars, 
                                       int(base_position - am_advantage + energy_bonus)))
            finish_positions.append(final_position)
            
            # Track wins and top 3
            if final_position == 1:
                wins += 1
            if final_position <= 3:
                top3 += 1
            
            # Energy remaining (simplified)
            base_energy = np.random.uniform(0.1, 0.3)  # 10-30% remaining
            if strategy.energy_mode == 'conservative':
                base_energy += np.random.uniform(0.05, 0.15)
            elif strategy.energy_mode == 'aggressive':
                base_energy -= np.random.uniform(0.05, 0.10)
            energy_remaining.append(max(0.0, base_energy))
        
        # Calculate metrics
        avg_position = np.mean(finish_positions)
        win_rate = wins / num_simulations
        top3_rate = top3 / num_simulations
        avg_energy = np.mean(energy_remaining)
        consistency = 1.0 / (1.0 + np.std(finish_positions))  # Lower std = higher consistency
        
        return StrategyResult(
            strategy=strategy,
            avg_finish_position=avg_position,
            win_rate=win_rate,
            top3_rate=top3_rate,
            avg_energy_remaining=avg_energy,
            consistency_score=consistency
        )
    
    def optimize_attack_mode_timing(self, num_simulations: int = 100,
                                   num_strategies: int = 20,
                                   target_position: int = 1,
                                   car_id: int = 0) -> Tuple[Strategy, StrategyResult]:
        """
        Find optimal Attack Mode timing strategy.
        
        Args:
            num_simulations: Number of Monte Carlo simulations per strategy
            num_strategies: Number of strategies to test
            target_position: Target finish position (1 = win, 3 = podium)
            car_id: Car ID to optimize for
            
        Returns:
            Tuple of (best_strategy, best_result)
        """
        print(f"Optimizing Attack Mode strategy for Car {car_id}")
        print(f"Testing {num_strategies} strategies with {num_simulations} simulations each...")
        print(f"Target: Position {target_position}")
        print("=" * 60)
        
        # Generate candidate strategies
        strategies = self.generate_strategy_candidates(num_strategies)
        
        # Test each strategy
        results = []
        start_time = time.time()
        
        for i, strategy in enumerate(strategies):
            result = self.simulate_strategy(strategy, num_simulations, car_id)
            results.append(result)
            
            if (i + 1) % 5 == 0:
                elapsed = time.time() - start_time
                print(f"  Tested {i+1}/{num_strategies} strategies ({elapsed:.1f}s)")
        
        # Find best strategy based on target
        if target_position == 1:
            # Optimize for win
            best_result = max(results, key=lambda r: r.win_rate)
        elif target_position <= 3:
            # Optimize for podium
            best_result = max(results, key=lambda r: r.top3_rate)
        else:
            # Optimize for average position
            best_result = min(results, key=lambda r: r.avg_finish_position)
        
        best_strategy = best_result.strategy
        
        print("\n" + "=" * 60)
        print("OPTIMIZATION RESULTS")
        print("=" * 60)
        print(f"Best Strategy:")
        print(f"  Attack Mode Lap 1: {best_strategy.attack_mode_lap_1}")
        print(f"  Attack Mode Lap 2: {best_strategy.attack_mode_lap_2}")
        print(f"  Energy Mode: {best_strategy.energy_mode}")
        print(f"  Overtaking: {best_strategy.overtaking_aggression}")
        print(f"  Safety Car Response: {best_strategy.safety_car_response}")
        print(f"\nPerformance Metrics:")
        print(f"  Avg Finish Position: {best_result.avg_finish_position:.2f}")
        print(f"  Win Rate: {best_result.win_rate*100:.1f}%")
        print(f"  Top 3 Rate: {best_result.top3_rate*100:.1f}%")
        print(f"  Avg Energy Remaining: {best_result.avg_energy_remaining*100:.1f}%")
        print(f"  Consistency Score: {best_result.consistency_score:.3f}")
        print("=" * 60)
        
        return best_strategy, best_result
    
    def compare_strategies(self, strategies: List[Strategy],
                          num_simulations: int = 100) -> Dict[str, StrategyResult]:
        """
        Compare multiple strategies side-by-side.
        
        Args:
            strategies: List of strategies to compare
            num_simulations: Number of simulations per strategy
            
        Returns:
            Dictionary mapping strategy names to results
        """
        print(f"Comparing {len(strategies)} strategies...")
        print("=" * 60)
        
        results = {}
        
        for i, strategy in enumerate(strategies):
            strategy_name = f"Strategy_{i+1}"
            result = self.simulate_strategy(strategy, num_simulations)
            results[strategy_name] = result
            
            print(f"\n{strategy_name}:")
            print(f"  AM Lap 1: {strategy.attack_mode_lap_1}, "
                  f"AM Lap 2: {strategy.attack_mode_lap_2}")
            print(f"  Avg Position: {result.avg_finish_position:.2f}, "
                  f"Win Rate: {result.win_rate*100:.1f}%")
        
        return results
    
    def analyze_safety_car_scenarios(self, base_strategy: Strategy,
                                    num_simulations: int = 100) -> Dict:
        """
        Analyze how different safety car scenarios affect strategy.
        
        Args:
            base_strategy: Base strategy to test
            num_simulations: Number of simulations
            
        Returns:
            Dictionary with scenario analysis
        """
        scenarios = {
            'no_safety_car': {'prob': 0.0},
            'early_safety_car': {'prob': 0.05, 'lap': 5},
            'mid_safety_car': {'prob': 0.05, 'lap': self.total_laps // 2},
            'late_safety_car': {'prob': 0.05, 'lap': 2 * self.total_laps // 3}
        }
        
        results = {}
        
        for scenario_name, scenario_params in scenarios.items():
            # Simulate with this safety car scenario
            # (Simplified - would integrate with RaceEvents in full version)
            result = self.simulate_strategy(base_strategy, num_simulations)
            results[scenario_name] = result
        
        return results


# Example usage
if __name__ == "__main__":
    optimizer = RaceStrategyOptimizer(
        num_cars=20,
        track_name="Berlin",
        race_duration_minutes=45.0,
        random_seed=42
    )
    
    # Optimize for win
    best_strategy, best_result = optimizer.optimize_attack_mode_timing(
        num_simulations=50,  # Reduced for faster testing
        num_strategies=10,
        target_position=1
    )
    
    print("\n" + "=" * 60)
    print("RECOMMENDED STRATEGY")
    print("=" * 60)
    print(f"Activate Attack Mode on laps {best_strategy.attack_mode_lap_1} and {best_strategy.attack_mode_lap_2}")
    print(f"Energy management: {best_strategy.energy_mode}")
    print(f"Overtaking style: {best_strategy.overtaking_aggression}")

