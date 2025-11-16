"""
Test the race strategy optimizer.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing Race Strategy Optimizer...")
print("=" * 60)

try:
    from race_sim.race_strategy_optimizer import RaceStrategyOptimizer, Strategy
    
    optimizer = RaceStrategyOptimizer(
        num_cars=20,
        track_name="Berlin",
        race_duration_minutes=45.0,
        random_seed=42
    )
    
    print("[OK] RaceStrategyOptimizer initialized")
    
    # Test strategy generation
    strategies = optimizer.generate_strategy_candidates(num_strategies=5)
    print(f"[OK] Generated {len(strategies)} strategy candidates")
    
    # Test strategy simulation
    result = optimizer.simulate_strategy(strategies[0], num_simulations=10)
    print(f"[OK] Strategy simulation complete")
    print(f"     Avg position: {result.avg_finish_position:.2f}")
    print(f"     Win rate: {result.win_rate*100:.1f}%")
    
    # Test optimization (quick test)
    print("\nRunning quick optimization test...")
    best_strategy, best_result = optimizer.optimize_attack_mode_timing(
        num_simulations=20,  # Reduced for speed
        num_strategies=5,
        target_position=1
    )
    
    print(f"\n[OK] Optimization complete!")
    print(f"     Best Attack Mode timing: Lap {best_strategy.attack_mode_lap_1} and {best_strategy.attack_mode_lap_2}")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Strategy Optimizer Test Complete!")

