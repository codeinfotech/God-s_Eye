# Usage Examples

## Example 1: Run a Full 20-Car Race

```python
from race_sim.race_simulator import RaceSimulator

# Create simulator
simulator = RaceSimulator(
    num_cars=20,
    track_name="Berlin",
    race_duration_minutes=45.0,
    time_step=0.2,
    random_seed=42
)

# Run race
results = simulator.run_race()

# Print winner
winner_id = min(results['final_positions'], key=results['final_positions'].get)
print(f"Winner: Car {winner_id}")
print(f"Laps completed: {results['laps_completed'][winner_id]}")
```

## Example 2: Test Different Strategies

```python
from race_sim.race_simulator import RaceSimulator

# Test early attack mode strategy
simulator_early = RaceSimulator(
    num_cars=15,
    track_name="Berlin",
    race_duration_minutes=30.0,  # Shorter for testing
    random_seed=1
)
results_early = simulator_early.run_race()

# Test late attack mode strategy
simulator_late = RaceSimulator(
    num_cars=15,
    track_name="Berlin",
    race_duration_minutes=30.0,
    random_seed=2
)
results_late = simulator_late.run_race()

# Compare
print("Early strategy results:")
for car_id, pos in sorted(results_early['final_positions'].items(), key=lambda x: x[1])[:5]:
    print(f"  P{pos}: Car {car_id}")

print("\nLate strategy results:")
for car_id, pos in sorted(results_late['final_positions'].items(), key=lambda x: x[1])[:5]:
    print(f"  P{pos}: Car {car_id}")
```

## Example 3: Analyze Race Events

```python
from race_sim.race_events import RaceEvents

events = RaceEvents(num_cars=20, track_length=2500.0, random_seed=42)

# Simulate 20 laps
for lap in range(1, 21):
    active_cars = list(range(20))
    lap_events = events.check_lap_events(lap, lap * 120.0, active_cars)
    
    if lap_events['safety_car_deployed']:
        print(f"Lap {lap}: 🚨 Safety car deployed!")
    
    if lap_events['crashes']:
        print(f"Lap {lap}: 💥 Crashes: Cars {lap_events['crashes']}")
    
    if lap_events['weather_changed']:
        print(f"Lap {lap}: 🌧️ Weather changed, mu={lap_events['new_mu_weather']:.2f}")
    
    # Update safety car
    events.update_safety_car(lap)

# Get summary
summary = events.get_event_summary()
print(f"\nRace Summary:")
print(f"  Safety cars: {summary['total_safety_cars']}")
print(f"  Crashes: {summary['total_crashes']}")
print(f"  Crashed cars: {summary['crashed_cars']}")
```

## Example 4: Test Overtaking

```python
from race_sim.overtaking import OvertakingModel

overtaking = OvertakingModel(track_length=2500.0, random_seed=42)

# Test different scenarios
scenarios = [
    (180.0, 175.0, 0.8, False, False),  # Small speed diff
    (185.0, 175.0, 0.6, False, False),  # Medium speed diff
    (190.0, 175.0, 0.5, True, False),   # Large speed diff with attack mode
]

for i, (attacker_speed, defender_speed, gap, am_attacker, am_defender) in enumerate(scenarios):
    result = overtaking.attempt_overtake(
        attacker_id=2,
        defender_id=1,
        attacker_speed=attacker_speed / 3.6,  # Convert to m/s
        defender_speed=defender_speed / 3.6,
        gap_seconds=gap,
        track_position=0.5,
        attacker_has_attack_mode=am_attacker,
        defender_has_attack_mode=am_defender,
        timestamp=i * 10.0
    )
    
    print(f"Scenario {i+1}:")
    print(f"  Speed diff: {result['speed_differential_kmh']:.1f} km/h")
    print(f"  Success: {result['success']}")
    print(f"  Time gain: {result['time_gain']:.3f}s")
    print(f"  Slipstream: {result['slipstream_active']}")
    print()

# Get statistics
stats = overtaking.get_overtaking_statistics()
print(f"Overtaking Statistics:")
print(f"  Total attempts: {stats['total_attempts']}")
print(f"  Success rate: {stats['success_rate']*100:.1f}%")
```

## Example 5: Attack Mode Strategy

```python
from race_sim.attack_mode import AttackModeManager

manager = AttackModeManager(
    num_cars=20,
    track_length=2500.0,
    activation_zone_start=500.0,
    activation_zone_end=600.0,
    random_seed=42
)

# Simulate race and activate attack mode for different cars
for car_id in [0, 5, 10]:
    can_activate, reason = manager.can_activate(
        car_id, current_lap=5, race_time=600.0, track_position=550.0
    )
    
    if can_activate:
        success = manager.activate(car_id, 5, 600.0, 550.0)
        print(f"Car {car_id}: Attack Mode activated: {success}")
        print(f"  Power: {manager.get_power_kw(car_id)} kW")
        print(f"  Remaining: {manager.get_activations_remaining(car_id)}")
    else:
        print(f"Car {car_id}: Cannot activate - {reason}")

# Update over time
for t in [600, 700, 800, 900]:
    manager.update_all(t)
    active_cars = [cid for cid in range(20) if manager.is_active(cid)]
    if active_cars:
        print(f"Time {t}s: Cars with active Attack Mode: {active_cars}")
```

## Example 6: Visualize Results

```python
from race_sim.race_simulator import RaceSimulator
from race_sim.race_visualizer import RaceVisualizer

# Run race
simulator = RaceSimulator(
    num_cars=15,
    track_name="Berlin",
    race_duration_minutes=20.0,  # Shorter for demo
    time_step=0.3
)
results = simulator.run_race()

# Create visualizations
visualizer = RaceVisualizer(
    simulator.track,
    num_cars=15,
    output_dir="output/"
)

# Generate all plots
visualizer.save_all(
    simulator.race_state,
    simulator.car_states,
    results['position_history'],
    initial_energy=4.58e6
)

print("Visualizations saved to output/")
```

## Example 7: Custom Race Configuration

```python
from race_sim.race_simulator import RaceSimulator
from race_sim.race_events import RaceEvents

# Create simulator with custom configuration
simulator = RaceSimulator(
    num_cars=12,
    track_name="Berlin",
    race_duration_minutes=30.0,
    time_step=0.2,
    random_seed=123
)

# Modify event probabilities for more action
simulator.race_events.safety_car_probability = 0.05  # 5% per lap
simulator.race_events.crash_probability_per_car = 0.02  # 2% per car per lap

# Run race
results = simulator.run_race()

# Analyze results
print(f"Race completed!")
print(f"Total safety cars: {results['race_events_summary']['total_safety_cars']}")
print(f"Total crashes: {results['race_events_summary']['total_crashes']}")
print(f"Overtaking attempts: {results['overtaking_stats']['total_attempts']}")
print(f"Successful overtakes: {results['overtaking_stats']['successful_overtakes']}")
```

## Example 8: Compare Strategies

```python
import numpy as np
from race_sim.race_simulator import RaceSimulator

strategies = {
    'aggressive': {'safety_car_prob': 0.03, 'crash_prob': 0.02},
    'conservative': {'safety_car_prob': 0.01, 'crash_prob': 0.01},
    'balanced': {'safety_car_prob': 0.02, 'crash_prob': 0.015}
}

results_comparison = {}

for strategy_name, params in strategies.items():
    print(f"\nTesting {strategy_name} strategy...")
    
    simulator = RaceSimulator(
        num_cars=10,
        track_name="Berlin",
        race_duration_minutes=15.0,
        random_seed=42
    )
    
    # Apply strategy parameters
    simulator.race_events.safety_car_probability = params['safety_car_prob']
    simulator.race_events.crash_probability_per_car = params['crash_prob']
    
    results = simulator.run_race()
    results_comparison[strategy_name] = results
    
    print(f"  Winner: Car {min(results['final_positions'], key=results['final_positions'].get)}")
    print(f"  Events: {results['race_events_summary']['total_safety_cars']} SC, "
          f"{results['race_events_summary']['total_crashes']} crashes")

# Compare
print("\n" + "="*60)
print("Strategy Comparison")
print("="*60)
for strategy, results in results_comparison.items():
    winner = min(results['final_positions'], key=results['final_positions'].get)
    print(f"{strategy:15s}: Winner Car {winner}, "
          f"{results['overtaking_stats']['total_attempts']} overtakes")
```

## Example 9: Export Results to CSV

```python
import csv
from race_sim.race_simulator import RaceSimulator

simulator = RaceSimulator(num_cars=20, track_name="Berlin", random_seed=42)
results = simulator.run_race()

# Export final positions
with open('race_results.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Position', 'Car ID', 'Laps', 'Time (min)'])
    
    for car_id, position in sorted(results['final_positions'].items(), key=lambda x: x[1]):
        writer.writerow([
            position,
            car_id,
            results['laps_completed'][car_id],
            results['final_times'][car_id] / 60.0
        ])

print("Results exported to race_results.csv")
```

## Example 10: Monitor Race Progress

```python
from race_sim.race_simulator import RaceSimulator

simulator = RaceSimulator(
    num_cars=15,
    track_name="Berlin",
    race_duration_minutes=20.0,
    time_step=0.2
)

# Run race with progress monitoring
print("Starting race...")
results = simulator.run_race()

# Print intermediate results every 5 minutes
for i in range(0, int(simulator.race_state.race_time), 300):
    # Access race state at different times
    print(f"\nRace time: {i/60:.1f} min")
    print(f"  Leader: Car {simulator.race_state.leader_id}")
    print(f"  Current lap: {simulator.race_state.current_lap}")
    print(f"  Safety car: {simulator.race_state.safety_car_active}")

print("\nRace finished!")
```

