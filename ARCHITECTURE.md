# Formula E Race Simulator - Architecture Documentation

## System Architecture Overview

This document explains how all the files are connected and how the race simulation system runs.

## 📐 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MAIN ENTRY POINT                             │
│                  main_race_sim.py                               │
│  - Configuration                                                │
│  - Initializes RaceSimulator                                    │
│  - Runs race and collects results                              │
│  - Generates visualizations                                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              RACE SIMULATOR (main_race_sim.py)                  │
│  RaceSimulator Class                                            │
│  - Orchestrates entire race                                     │
│  - Manages time-step loop                                       │
│  - Coordinates all subsystems                                   │
└──────┬──────────────┬──────────────┬──────────────┬─────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   TRACK     │ │   EVENTS    │ │ OVERTAKING  │ │ ATTACK MODE │
│  (track.py) │ │(race_events)│ │(overtaking)│ │(attack_mode)│
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
       │              │              │              │
       └──────────────┴──────────────┴──────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  CAR STATES      │
              │  (20 cars)        │
              └─────────────────┘
```

## 🔗 File Connections & Data Flow

### 1. Entry Point: `main_race_sim.py`

**Purpose**: Main script that users run to start a race

**Flow**:
```
main_race_sim.py
    │
    ├─> Creates RaceSimulator instance
    │   └─> RaceSimulator.__init__()
    │       ├─> _initialize_track()      → Uses laptimesim.src.track
    │       ├─> _initialize_race_components()
    │       │   ├─> RaceEvents()        → race_sim/race_events.py
    │       │   ├─> OvertakingModel()   → race_sim/overtaking.py
    │       │   ├─> AttackModeManager() → race_sim/attack_mode.py
    │       │   └─> PitStrategy()       → race_sim/pit_strategy.py
    │       └─> _initialize_car_states()
    │
    ├─> Calls simulator.run_race()
    │   └─> Main time-step loop
    │       ├─> _update_car() for each car
    │       ├─> _process_overtaking()
    │       ├─> _check_race_events()
    │       └─> _update_positions()
    │
    └─> Collects results and creates visualizations
        └─> RaceVisualizer()           → race_sim/race_visualizer.py
```

### 2. Core Race Simulator: `main_race_sim.py` (RaceSimulator class)

**Dependencies**:
- `laptimesim.src.track` - Track geometry and data
- `race_sim.race_events` - Safety car, crashes, weather
- `race_sim.overtaking` - Overtaking logic
- `race_sim.attack_mode` - Attack Mode system
- `race_sim.pit_strategy` - Pit stop decisions

**Internal State**:
- `self.track` - Track object (from laptimesim)
- `self.car_states` - Dictionary of all car states
- `self.race_state` - Current race state
- `self.events` - RaceEvents instance
- `self.overtaking` - OvertakingModel instance
- `self.attack_mode` - AttackModeManager instance
- `self.pit_strategy` - PitStrategy instance

**Main Loop** (runs every `time_step` seconds):
```
while race_time < race_duration:
    1. Update each car (_update_car)
       ├─> Calculate speed (considering safety car, attack mode, energy)
       ├─> Update position
       ├─> Check lap completion
       ├─> Update energy consumption
       └─> Try activate attack mode
    
    2. Process overtaking (_process_overtaking)
       └─> Check adjacent cars
           └─> Call overtaking.attempt_overtake()
    
    3. Check race events (_check_race_events)
       └─> Call events.check_lap_events()
           ├─> Safety car deployment?
           ├─> Crashes?
           └─> Weather changes?
    
    4. Update positions (_update_positions)
       └─> Sort cars by lap and distance
           └─> Assign position ranks
    
    5. Record history (every 10 seconds)
```

### 3. Race Events: `race_sim/race_events.py`

**Purpose**: Manages random race events

**Key Methods**:
- `check_lap_events()` - Called each lap to check for new events
- `update_safety_car()` - Updates safety car state each lap
- `get_safety_car_speed()` - Returns current speed limit

**Data Flow**:
```
RaceSimulator._check_race_events()
    │
    └─> events.check_lap_events(lap, time, active_cars)
        │
        ├─> Returns: {
        │     'safety_car_deployed': bool,
        │     'crashes': List[car_id],
        │     'weather_changed': bool,
        │     'new_mu_weather': float
        │   }
        │
        └─> RaceSimulator processes these events
            ├─> Sets safety_car_active = True
            ├─> Marks crashed cars as inactive
            └─> Updates track friction (mu_weather)
```

### 4. Overtaking: `race_sim/overtaking.py`

**Purpose**: Handles car-to-car overtaking

**Key Methods**:
- `attempt_overtake()` - Attempts an overtake between two cars
- `calculate_slipstream_effect()` - Calculates drag reduction
- `get_overtaking_success_probability()` - Returns success chance

**Data Flow**:
```
RaceSimulator._process_overtaking()
    │
    └─> For each adjacent car pair:
        │
        ├─> Calculate speed difference
        │
        └─> If speed_diff > 5 km/h:
            │
            └─> overtaking.attempt_overtake(
                    attacker_id, defender_id,
                    attacker_speed, defender_speed,
                    gap_seconds, track_position,
                    attacker_has_attack_mode,
                    defender_has_attack_mode,
                    timestamp
                )
                │
                └─> Returns: {
                      'success': bool,
                      'speed_differential_kmh': float,
                      'time_gain': float,
                      'slipstream_active': bool
                    }
                │
                └─> If success: Swap positions
```

### 5. Attack Mode: `race_sim/attack_mode.py`

**Purpose**: Manages Formula E Attack Mode for all cars

**Key Classes**:
- `AttackMode` - Single car's attack mode state
- `AttackModeManager` - Manages all cars' attack modes

**Data Flow**:
```
RaceSimulator._update_car()
    │
    ├─> Check if attack mode active:
    │   └─> attack_mode.is_active(car_id, race_time)
    │       └─> Returns: bool
    │
    └─> Try activate at lap start:
        └─> attack_mode.can_activate(car_id, lap, time, distance)
            └─> Returns: (can_activate: bool, reason: str)
            │
            └─> If True:
                └─> attack_mode.activate(car_id, lap, time, distance)
                    └─> Sets power boost active for 4 minutes
```

**Attack Mode State Machine**:
```
AVAILABLE → ACTIVATING → ACTIVE → AVAILABLE (if activations left)
                │                        │
                └────────────────────────┘
                              ↓
                          USED (if all activations used)
```

### 6. Pit Strategy: `race_sim/pit_strategy.py`

**Purpose**: Handles pit stop decisions

**Data Flow**:
```
RaceSimulator._handle_low_energy()
    │
    └─> pit_strategy.should_pit_energy(
            car_id, energy_remaining,
            initial_energy, race_distance_remaining,
            current_lap
        )
        │
        └─> Returns: (should_pit: bool, reason: str)
            │
            └─> If should_pit:
                └─> pit_strategy.execute_pit_stop(
                        car_id, pit_type, lap, race_time
                    )
                    └─> Returns: PitStop object
                        └─> Applies time loss to car
```

### 7. Extended Driver: `race_sim/driver_race.py`

**Purpose**: Adds race-aware strategic decision making

**Key Methods**:
- `race_position_awareness()` - Updates driver's knowledge
- `strategic_decision_maker()` - Makes strategic decisions
- `should_activate_attack_mode()` - Attack mode timing decision

**Usage** (Future integration):
```
RaceSimulator could use RaceDriver for each car:
    driver = RaceDriver(car, driver_opts, track)
    decision = driver.strategic_decision_maker(
        laps_remaining, attack_mode_available, ...
    )
    └─> Returns: {
          'use_attack_mode': bool,
          'energy_mode': 'push'|'conserve'|'normal',
          'defend_position': bool,
          'attack_position': bool
        }
```

### 8. Strategy Optimizer: `race_sim/race_strategy_optimizer.py`

**Purpose**: Pre-race strategy optimization using Monte Carlo

**Data Flow**:
```
User calls:
    optimizer = RaceStrategyOptimizer(...)
    best_strategy, result = optimizer.optimize_attack_mode_timing(
        num_simulations=100,
        target_position=1
    )
    │
    ├─> Generates candidate strategies
    │   └─> Different attack mode timings
    │       └─> Early, mid, late race activations
    │
    ├─> For each strategy:
    │   └─> simulate_strategy(strategy, num_simulations)
    │       └─> Runs simplified race simulation
    │           └─> Calculates performance metrics
    │
    └─> Returns best strategy based on target
        └─> Best for win, podium, or average position
```

### 9. Visualizer: `race_sim/race_visualizer.py`

**Purpose**: Creates visualizations of race results

**Data Flow**:
```
After race completes:
    visualizer = RaceVisualizer(track, num_cars)
    visualizer.save_all(
        race_state, car_states, position_history, initial_energy
    )
    │
    ├─> plot_leaderboard() → leaderboard.png
    ├─> plot_energy_levels() → energy_levels.png
    ├─> plot_track_map() → track_map.png
    └─> plot_position_changes() → position_changes.png
```

## 🔄 Complete Execution Flow

### Step-by-Step: How a Race Runs

```
1. USER RUNS: python main_race_sim.py
   │
   ├─> main() function executes
   │   └─> Creates RaceSimulator(config)
   │
2. RaceSimulator.__init__()
   │
   ├─> _initialize_track()
   │   └─> Loads track from laptimesim/input/tracks/
   │       └─> Creates Track object
   │           └─> Calculates curvature, distances, etc.
   │
   ├─> _initialize_race_components()
   │   ├─> RaceEvents() - Initializes event system
   │   ├─> OvertakingModel() - Initializes overtaking
   │   ├─> AttackModeManager() - Creates attack mode for each car
   │   └─> PitStrategy() - Initializes pit logic
   │
   └─> _initialize_car_states()
       └─> Creates state dictionary for each car
           └─> Sets initial positions, energy, etc.
   
3. simulator.run_race()
   │
   └─> MAIN LOOP (time_step = 0.5s):
       │
       ├─> For each car:
       │   └─> _update_car(car_id)
       │       ├─> Calculate speed
       │       │   ├─> Check safety car → 80 km/h
       │       │   ├─> Check attack mode → +8% speed
       │       │   ├─> Check energy → -8% if low
       │       │   └─> Apply weather factor
       │       │
       │       ├─> Update distance = speed * time_step
       │       │
       │       ├─> Check lap completion
       │       │   └─> If distance >= track_length:
       │       │       ├─> Increment lap
       │       │       └─> Try activate attack mode
       │       │
       │       ├─> Update energy consumption
       │       │   └─> energy -= consumption_rate * time_step
       │       │
       │       └─> Check critical energy
       │           └─> If energy < 3 kWh:
       │               └─> _handle_low_energy()
       │                   └─> Check if should pit
       │
       ├─> _process_overtaking()
       │   └─> For each adjacent car pair:
       │       ├─> Calculate speed difference
       │       └─> If > 5 km/h:
       │           └─> Call overtaking.attempt_overtake()
       │               └─> If successful: Swap positions
       │
       ├─> _check_race_events()
       │   └─> Every lap:
       │       └─> events.check_lap_events()
       │           ├─> Safety car? (3% chance)
       │           ├─> Crashes? (1.5% per car)
       │           └─> Weather change? (2% chance)
       │
       ├─> _update_positions()
       │   └─> Sort cars by (lap, distance)
       │       └─> Assign position ranks
       │
       └─> Record history (every 10s)
           └─> Store position snapshot
   
4. Race finishes (time limit reached)
   │
   ├─> _compile_results()
   │   └─> Creates results dictionary:
   │       ├─> final_positions
   │       ├─> final_times
   │       ├─> laps_completed
   │       ├─> race_events_summary
   │       └─> overtaking_stats
   │
   ├─> _print_final_classification()
   │   └─> Prints leaderboard to console
   │
   └─> Create visualizations
       └─> RaceVisualizer.save_all()
           └─> Generates PNG files
```

## 📊 Data Structures

### Car State (Dictionary)
```python
car_states[car_id] = {
    'position_rank': int,      # Current race position (1-20)
    'distance': float,          # Distance along track (meters)
    'lap': int,                 # Current lap number
    'total_time': float,        # Total race time (seconds)
    'lap_time': float,          # Expected lap time (seconds)
    'speed': float,             # Current speed (m/s)
    'energy': float,            # Battery energy (kWh)
    'active': bool,             # Still racing?
    'dnf_reason': str,          # None or 'crash'
    'attack_mode_used': int,    # Number of activations (0-2)
    'pit_stops': int,           # Number of pit stops
    'driver_skill': float,      # Skill multiplier
    'strategy': str             # 'aggressive', 'balanced', 'conservative'
}
```

### Race State (Dictionary)
```python
race_state = {
    'race_time': float,         # Current race time (seconds)
    'safety_car_active': bool,  # Safety car deployed?
    'safety_car_end_time': float, # When safety car ends
    'weather': str,             # 'dry' or 'wet'
    'mu_weather': float,        # Friction multiplier (0.5-1.0)
    'leader_id': int,           # Car ID of race leader
    'current_lap': int          # Current lap number
}
```

## 🔌 Module Dependencies

```
main_race_sim.py
    │
    ├─> laptimesim.src.track (existing)
    │   └─> Uses trajectory_planning_helpers
    │
    ├─> race_sim.race_events
    │   └─> Standalone (numpy only)
    │
    ├─> race_sim.overtaking
    │   └─> Standalone (numpy only)
    │
    ├─> race_sim.attack_mode
    │   └─> Standalone (numpy only)
    │
    └─> race_sim.pit_strategy
        └─> Standalone (numpy only)
```

## 🎯 Key Integration Points

### 1. Track Integration
- **File**: `laptimesim/src/track.py` (existing)
- **Used by**: `RaceSimulator._initialize_track()`
- **Provides**: Track geometry, curvature, distances, speed limits
- **Data**: `track_length`, `track.raceline`, `track.kappa`, `track.mu`

### 2. Event System Integration
- **File**: `race_sim/race_events.py`
- **Used by**: `RaceSimulator._check_race_events()`
- **Called**: Once per lap
- **Returns**: Event dictionary with safety car, crashes, weather

### 3. Overtaking Integration
- **File**: `race_sim/overtaking.py`
- **Used by**: `RaceSimulator._process_overtaking()`
- **Called**: Every 5 seconds during race
- **Input**: Car speeds, positions, attack mode status
- **Output**: Overtaking success/failure

### 4. Attack Mode Integration
- **File**: `race_sim/attack_mode.py`
- **Used by**: `RaceSimulator._update_car()`, `_try_activate_attack_mode()`
- **Called**: 
  - Every time step (check if active)
  - At lap start (try to activate)
- **Manages**: Power boost, duration, activations remaining

### 5. Pit Strategy Integration
- **File**: `race_sim/pit_strategy.py`
- **Used by**: `RaceSimulator._handle_low_energy()`
- **Called**: When car energy < 3 kWh
- **Returns**: Whether car should pit

## 🔄 Time-Step Simulation Flow

```
Time: 0.0s
├─> Initialize all cars at start line
└─> Set initial positions, energy, speeds

Time: 0.5s (first time step)
├─> Update Car 0:
│   ├─> Calculate speed (considering track, energy, attack mode)
│   ├─> Update distance += speed * 0.5
│   ├─> Update energy -= consumption * 0.5
│   └─> Check lap completion
├─> Update Car 1: (same process)
├─> ... (all 20 cars)
├─> Process overtaking (check adjacent cars)
├─> Check race events (safety car, crashes, weather)
└─> Update positions (sort by lap + distance)

Time: 1.0s
└─> Repeat above...

Time: 1.5s
└─> Repeat...

... (continues until race_duration reached)
```

## 📈 State Updates Per Time Step

For each car, per time step (0.5s):
1. **Speed calculation** → `car['speed']`
2. **Position update** → `car['distance']`
3. **Energy consumption** → `car['energy']`
4. **Lap completion check** → `car['lap']`
5. **Attack mode check** → `car['attack_mode_used']`

For race, per time step:
1. **Overtaking attempts** → Position changes
2. **Event checks** → Safety car, crashes, weather
3. **Position ranking** → `car['position_rank']` for all cars

## 🎮 Control Flow Summary

```
User Command
    │
    └─> python main_race_sim.py
        │
        ├─> Configuration (num_cars, track, duration, etc.)
        │
        ├─> Initialize RaceSimulator
        │   ├─> Load track
        │   ├─> Initialize race systems
        │   └─> Initialize car states
        │
        ├─> Run race loop
        │   └─> For each time step:
        │       ├─> Update all cars
        │       ├─> Process interactions
        │       └─> Update race state
        │
        ├─> Collect results
        │
        └─> Generate output
            ├─> Print classification
            ├─> Save JSON results
            └─> Create visualizations
```

## 🔍 Key Design Decisions

1. **Time-Step Based**: Not lap-based optimization, but real-time simulation
2. **Simplified Physics**: Uses reference lap time for speed calculation (fast)
3. **Modular Design**: Each system (events, overtaking, attack mode) is independent
4. **State-Based**: All car data stored in dictionaries, not objects
5. **Event-Driven**: Race events checked per lap, not per time step

## 🚀 Performance Characteristics

- **Time Step**: 0.5s (configurable)
- **Cars**: 10-20 simultaneously
- **Race Duration**: 45 minutes = 5400 seconds
- **Total Steps**: 5400 / 0.5 = 10,800 time steps
- **Operations per Step**: ~100 (20 cars × 5 operations each)
- **Total Operations**: ~1,080,000 for full race
- **Simulation Time**: ~2 minutes for full race

## 📝 Example: Single Time Step Execution

```python
# Time: 120.5 seconds (Lap 2, mid-race)

# 1. Update Car 0
car = car_states[0]
car['speed'] = calculate_speed(car)  # 50 m/s
car['distance'] += 50.0 * 0.5  # += 25 meters
car['energy'] -= 0.35 * (0.5/60)  # -= 0.0029 kWh
if car['distance'] >= track_length:
    car['lap'] += 1
    try_activate_attack_mode(0)

# 2. Update Car 1
# ... (same for all 20 cars)

# 3. Process Overtaking
# Car 5 is 0.8s behind Car 4
if speed_diff > 5 km/h:
    result = overtaking.attempt_overtake(...)
    if result['success']:
        # Swap positions
        car_states[4]['position_rank'], car_states[5]['position_rank'] = \
            car_states[5]['position_rank'], car_states[4]['position_rank']

# 4. Check Events (only at lap start)
if is_lap_start:
    events = race_events.check_lap_events(...)
    if events['safety_car_deployed']:
        race_state['safety_car_active'] = True

# 5. Update Positions
active_cars.sort(key=lambda i: (-lap, -distance))
for rank, car_id in enumerate(active_cars):
    car_states[car_id]['position_rank'] = rank

# 6. Record History (every 10s)
if race_time % 10.0 < time_step:
    position_history.append({'time': race_time, 'positions': [...]})
```

This architecture allows the system to simulate complex multi-car races with realistic interactions while maintaining good performance!

