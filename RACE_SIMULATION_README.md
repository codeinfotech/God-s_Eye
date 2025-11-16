# Formula E Multi-Agent Race Simulator

## Overview

This extension transforms the single-car lap time simulator into a full multi-agent race simulator for Formula E. It supports 10-20 cars racing simultaneously with realistic race events, overtaking, Attack Mode, and strategic decision making.

## Features

### ✅ Implemented Features

1. **Multi-Agent Simulation**
   - 10-20 cars racing simultaneously
   - Time-step based simulation (0.1-0.5s)
   - Real-time position tracking and gap calculations

2. **Race Events** (`race_events.py`)
   - Safety car deployment (2-5% chance per lap, 3-8 lap duration)
   - Crashes/DNFs (1-2% per car per lap)
   - Weather changes (rain reduces grip by 15-30%)
   - Virtual safety car support

3. **Overtaking** (`overtaking.py`)
   - Speed differential requirements (>5 km/h)
   - Slipstream effect (5% drag reduction within 1 second)
   - Success probability based on speed difference
   - Attack Mode power advantage

4. **Attack Mode** (`attack_mode.py`)
   - 2 activations per race
   - 4 minutes duration each
   - Power boost: 200kW → 250kW (+50kW)
   - Time loss: 0.5-1.0s per activation
   - Strategic timing optimization

5. **Race Simulator** (`race_simulator.py`)
   - Main orchestrator for race simulation
   - Manages all cars, events, and interactions
   - Tracks positions, gaps, energy levels
   - Outputs comprehensive race results

6. **Extended Driver** (`driver_race.py`)
   - Race position awareness
   - Gap management (defend/attack)
   - Energy delta tracking
   - Strategic decision making

7. **Pit Strategy** (`pit_strategy.py`)
   - Energy-critical pit stops
   - Repair pit stops after incidents
   - Drive-through penalties

8. **Visualization** (`race_visualizer.py`)
   - Live leaderboard with gaps
   - Energy levels bar chart
   - Track map with car positions
   - Position changes over time

## Installation

No additional dependencies required beyond the base simulator:
```bash
pip install numpy matplotlib trajectory_planning_helpers utm pytest
```

## Quick Start

### Run a Full Race

```python
python main_race_sim.py
```

This will:
- Simulate a 20-car race on Berlin track
- Run for 45 minutes + 1 lap
- Generate visualizations
- Save results to `race_sim/output/`

### Custom Configuration

```python
from race_sim.race_simulator import RaceSimulator

simulator = RaceSimulator(
    num_cars=15,
    track_name="Berlin",
    race_duration_minutes=45.0,
    time_step=0.2,
    random_seed=42
)

results = simulator.run_race()
```

## Usage Examples

### 1. Run a 20-Car Race

```python
from race_sim.race_simulator import RaceSimulator

simulator = RaceSimulator(
    num_cars=20,
    track_name="Berlin",
    race_duration_minutes=45.0,
    time_step=0.2
)

results = simulator.run_race()

# Access results
print(f"Winner: Car {min(results['final_positions'], key=results['final_positions'].get)}")
print(f"Total overtakes: {results['overtaking_stats']['total_attempts']}")
```

### 2. Test Different Strategies

```python
# Early Attack Mode Strategy
simulator_early = RaceSimulator(num_cars=20, track_name="Berlin", random_seed=1)
results_early = simulator_early.run_race()

# Late Attack Mode Strategy (modify driver logic)
simulator_late = RaceSimulator(num_cars=20, track_name="Berlin", random_seed=2)
results_late = simulator_late.run_race()

# Compare results
print(f"Early strategy winner: {min(results_early['final_positions'], key=results_early['final_positions'].get)}")
print(f"Late strategy winner: {min(results_late['final_positions'], key=results_late['final_positions'].get)}")
```

### 3. Visualize Results

```python
from race_sim.race_visualizer import RaceVisualizer

visualizer = RaceVisualizer(
    simulator.track,
    num_cars=20,
    output_dir="output/"
)

visualizer.plot_leaderboard(race_state, car_states)
visualizer.plot_energy_levels(car_states, initial_energy=4.58e6)
visualizer.plot_track_map(car_states, race_state)
visualizer.plot_position_changes(position_history)
```

### 4. Analyze Race Events

```python
from race_sim.race_events import RaceEvents

events = RaceEvents(num_cars=20, track_length=2500.0, random_seed=42)

# Check events each lap
for lap in range(1, 21):
    lap_events = events.check_lap_events(lap, lap * 120.0, list(range(20)))
    
    if lap_events['safety_car_deployed']:
        print(f"Lap {lap}: Safety car deployed!")
    
    if lap_events['crashes']:
        print(f"Lap {lap}: Crashes: {lap_events['crashes']}")

# Get summary
summary = events.get_event_summary()
print(f"Total safety cars: {summary['total_safety_cars']}")
print(f"Total crashes: {summary['total_crashes']}")
```

### 5. Test Overtaking

```python
from race_sim.overtaking import OvertakingModel

overtaking = OvertakingModel(track_length=2500.0, random_seed=42)

result = overtaking.attempt_overtake(
    attacker_id=2,
    defender_id=1,
    attacker_speed=180.0 / 3.6,  # m/s
    defender_speed=175.0 / 3.6,
    gap_seconds=0.8,
    track_position=0.5,
    attacker_has_attack_mode=True,
    defender_has_attack_mode=False,
    timestamp=600.0
)

print(f"Overtake success: {result['success']}")
print(f"Time gain: {result['time_gain']:.3f}s")
```

## Output Files

After running a simulation, the following files are generated in `race_sim/output/`:

- `race_results.json`: Final classification and statistics
- `leaderboard.png`: Current leaderboard visualization
- `energy_levels.png`: Energy levels for all cars
- `track_map.png`: Track map with car positions
- `position_changes.png`: Position changes over time

## Configuration Options

### Race Simulator Parameters

```python
RaceSimulator(
    num_cars=20,              # Number of cars (10-20)
    track_name="Berlin",      # Track name (must exist in track_pars.ini)
    race_duration_minutes=45.0,  # Race duration
    time_step=0.2,            # Simulation time step (0.1-0.5s)
    random_seed=42            # Random seed for reproducibility
)
```

### Race Events Probabilities

Modify in `race_events.py`:
- `safety_car_probability = 0.03`  # 3% per lap
- `crash_probability_per_car = 0.015`  # 1.5% per car per lap
- `weather_change_probability = 0.02`  # 2% per lap

### Overtaking Parameters

Modify in `overtaking.py`:
- `min_speed_diff = 5.0`  # km/h minimum speed difference
- `slipstream_distance = 1.0`  # seconds gap for slipstream
- `slipstream_drag_reduction = 0.05`  # 5% drag reduction

## Performance

- **Simulation Speed**: ~2 minutes for a 45-minute race with 20 cars
- **Time Step**: 0.2s recommended for good balance
- **Memory Usage**: ~500MB for full race with history

## Testing Scenarios

### 1. Clean Race (No Events)
```python
# Set all probabilities to 0 in race_events.py
events.safety_car_probability = 0.0
events.crash_probability_per_car = 0.0
events.weather_change_probability = 0.0
```

### 2. Safety Car at Lap 10
```python
# Manually trigger safety car
events._deploy_safety_car(lap=10, race_time=1200.0)
```

### 3. Multiple Crashes
```python
# Increase crash probability
events.crash_probability_per_car = 0.05  # 5% per car per lap
```

### 4. Rain from Lap 15
```python
# Manually trigger weather change
events.weather_dry = False
events.mu_weather = 0.75  # 25% grip reduction
```

## Architecture

```
race_sim/
├── race_events.py          # Safety car, crashes, weather
├── overtaking.py           # Overtaking logic
├── attack_mode.py          # Attack Mode system
├── race_simulator.py       # Main orchestrator
├── driver_race.py          # Extended driver with strategy
├── pit_strategy.py         # Pit stop logic
└── race_visualizer.py      # Visualization tools

main_race_sim.py            # Entry point
```

## Integration with Existing Code

The race simulator reuses:
- `laptimesim.src.car_electric.CarElectric` - Vehicle dynamics
- `laptimesim.src.track.Track` - Track geometry
- `laptimesim.src.driver.Driver` - Base driver logic
- `laptimesim.src.lap.Lap` - Lap time solver (for reference)

## Limitations & Future Improvements

### Current Limitations:
1. Simplified physics for performance (uses reference lap time)
2. Overtaking is probabilistic, not physics-based
3. No tire degradation model
4. No detailed aerodynamic interactions

### Future Improvements:
1. Full physics-based simulation for each car
2. More sophisticated overtaking model
3. Tire degradation and pit stops
4. Real-time visualization during simulation
5. Monte Carlo strategy optimization
6. Machine learning for strategy decisions

## Troubleshooting

### Import Errors
If you get import errors, ensure the repository structure is correct:
```
formula_e/
├── laptime-simulation/
│   ├── race_sim/
│   ├── laptimesim/
│   └── main_race_sim.py
```

### Track Not Found
Ensure the track name exists in `laptimesim/input/tracks/track_pars.ini` and the raceline file exists in `laptimesim/input/tracks/racelines/`.

### Performance Issues
- Reduce `num_cars` (fewer cars = faster)
- Increase `time_step` (0.5s instead of 0.2s)
- Disable visualization during simulation

## Contact & Support

For issues or questions, refer to the base simulator documentation or create an issue in the repository.

## License

Same license as the base Formula E lap time simulator.

