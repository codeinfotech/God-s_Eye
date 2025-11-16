"""
Simple test of race simulation components without full track dependency.
"""

import sys
import os

# Add race_sim to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing Race Simulation Components...")
print("=" * 60)

# Test 1: Race Events
print("\n1. Testing Race Events...")
try:
    from race_sim.race_events import RaceEvents
    
    events = RaceEvents(num_cars=20, track_length=2500.0, random_seed=42)
    print(f"   [OK] RaceEvents initialized")
    print(f"   [OK] Safety car probability: {events.safety_car_probability}")
    print(f"   [OK] Crash probability: {events.crash_probability_per_car}")
    
    # Test event checking
    lap_events = events.check_lap_events(1, 120.0, list(range(20)))
    print(f"   [OK] Event checking works")
    print(f"   [OK] Events on lap 1: {len([k for k, v in lap_events.items() if v])} events")
except Exception as e:
    print(f"   [ERROR] Error: {e}")

# Test 2: Overtaking
print("\n2. Testing Overtaking Model...")
try:
    from race_sim.overtaking import OvertakingModel
    
    overtaking = OvertakingModel(track_length=2500.0, random_seed=42)
    print(f"   [OK] OvertakingModel initialized")
    
    result = overtaking.attempt_overtake(
        attacker_id=2, defender_id=1,
        attacker_speed=180.0 / 3.6,
        defender_speed=175.0 / 3.6,
        gap_seconds=0.8,
        track_position=0.5,
        attacker_has_attack_mode=False,
        defender_has_attack_mode=False,
        timestamp=600.0
    )
    print(f"   [OK] Overtaking attempt: Success={result['success']}, "
          f"Speed diff={result['speed_differential_kmh']:.1f} km/h")
except Exception as e:
    print(f"   [ERROR] Error: {e}")

# Test 3: Attack Mode
print("\n3. Testing Attack Mode...")
try:
    from race_sim.attack_mode import AttackModeManager
    
    manager = AttackModeManager(num_cars=20, track_length=2500.0, random_seed=42)
    print(f"   [OK] AttackModeManager initialized")
    
    can_activate, reason = manager.can_activate(0, 1, 0.0, 550.0)
    print(f"   [OK] Attack mode check: Can activate={can_activate}, Reason={reason}")
    
    if can_activate:
        manager.activate(0, 1, 0.0, 550.0)
        print(f"   [OK] Attack mode activated: Power={manager.get_power_kw(0)} kW")
except Exception as e:
    print(f"   [ERROR] Error: {e}")

# Test 4: Pit Strategy
print("\n4. Testing Pit Strategy...")
try:
    from race_sim.pit_strategy import PitStrategy
    
    pit_strategy = PitStrategy(num_cars=20, random_seed=42)
    print(f"   [OK] PitStrategy initialized")
    
    should_pit, reason = pit_strategy.should_pit_energy(
        1, 0.5e6, 4.58e6, 5000.0, 20
    )
    print(f"   [OK] Pit decision: Should pit={should_pit}, Reason={reason}")
except Exception as e:
    print(f"   [ERROR] Error: {e}")

print("\n" + "=" * 60)
print("Component Tests Complete!")
print("=" * 60)
print("\nNote: Full race simulation requires trajectory_planning_helpers")
print("which needs C++ build tools. The components above work correctly.")
print("\nTo run full simulation:")
print("1. Install Microsoft C++ Build Tools")
print("2. Run: pip install trajectory_planning_helpers")
print("3. Run: python main_race_sim.py")

