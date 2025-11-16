# Execution Flow - How the Race Simulation Runs

## 🎬 Complete Execution Sequence

### Phase 1: Initialization (One-Time Setup)

```
1. User runs: python main_race_sim.py
   │
2. main() function executes
   │
3. Configuration loaded:
   ├─> num_cars = 20
   ├─> track_name = "Shanghai"
   ├─> race_duration_minutes = 45.0
   ├─> time_step = 0.5
   └─> random_seed = 42
   │
4. RaceSimulator created:
   └─> RaceSimulator.__init__()
       │
       ├─> STEP 1: _initialize_track()
       │   │
       │   ├─> Load track_pars.ini
       │   ├─> Load raceline CSV file
       │   ├─> Create Track object (from laptimesim)
       │   │   └─> Calculates:
       │   │       ├─> Track length
       │   │       ├─> Curvature profile
       │   │       ├─> Distance array
       │   │       └─> Friction values
       │   │
       │   └─> Store: self.track, self.track_length
       │
       ├─> STEP 2: _initialize_race_components()
       │   │
       │   ├─> Create RaceEvents()
       │   │   └─> Sets up:
       │   │       ├─> Safety car probabilities
       │   │       ├─> Crash probabilities
       │   │       └─> Weather probabilities
       │   │
       │   ├─> Create OvertakingModel()
       │   │   └─> Sets up:
       │   │       ├─> Speed differential thresholds
       │   │       ├─> Slipstream parameters
       │   │       └─> Success probabilities
       │   │
       │   ├─> Create AttackModeManager()
       │   │   └─> Creates AttackMode for each car:
       │   │       ├─> 20 AttackMode objects
       │   │       ├─> Activation zones
       │   │       └─> Power boost settings
       │   │
       │   ├─> Create PitStrategy()
       │   │   └─> Sets up:
       │   │       ├─> Pit stop durations
       │   │       └─> Energy thresholds
       │   │
       │   └─> Calculate reference_lap_time
       │       └─> track_length / average_speed
       │
       └─> STEP 3: _initialize_car_states()
           │
           └─> For each car (0-19):
               ├─> Create car state dictionary
               ├─> Set initial position (grid order)
               ├─> Set initial energy (52 kWh)
               ├─> Calculate lap time (with skill variation)
               └─> Initialize all counters
```

### Phase 2: Race Execution (Time-Step Loop)

```
5. simulator.run_race() called
   │
   └─> MAIN LOOP: while race_time < race_duration:
       │
       ├─> INCREMENT TIME
       │   └─> race_time += time_step (0.5s)
       │
       ├─> UPDATE ALL CARS (Parallel processing)
       │   │
       │   └─> For car_id in range(20):
       │       │
       │       └─> _update_car(car_id)
       │           │
       │           ├─> Calculate target speed:
       │           │   ├─> If safety car active:
       │           │   │   └─> speed = 80 km/h
       │           │   │
       │           │   └─> Else (normal racing):
       │           │       ├─> base_speed = track_length / lap_time
       │           │       ├─> Apply driver skill multiplier
       │           │       ├─> If attack mode active: +8%
       │           │       ├─> If low energy: -8%
       │           │       └─> Apply weather factor
       │           │
       │           ├─> Update position:
       │           │   └─> distance += speed * time_step
       │           │
       │           ├─> Update time:
       │           │   └─> total_time += time_step
       │           │
       │           ├─> Check lap completion:
       │           │   └─> If distance >= track_length:
       │           │       ├─> distance -= track_length
       │           │       ├─> lap += 1
       │           │       └─> Try activate attack mode
       │           │
       │           ├─> Update energy:
       │           │   ├─> consumption_rate = 0.35 kWh/min
       │           │   ├─> If attack mode: +40%
       │           │   ├─> If aggressive: +10%
       │           │   ├─> If conservative: -10%
       │           │   └─> energy -= consumption_rate * (time_step/60)
       │           │
       │           └─> Check critical energy:
       │               └─> If energy < 3 kWh:
       │                   └─> _handle_low_energy()
       │                       └─> Check if should pit
       │
       ├─> PROCESS OVERTAKING (Every 5 seconds)
       │   │
       │   └─> _process_overtaking()
       │       │
       │       ├─> Get active cars sorted by position
       │       │
       │       └─> For each adjacent pair:
       │           ├─> Calculate speed difference
       │           │
       │           └─> If speed_diff > 5 km/h:
       │               │
       │               └─> Call overtaking.attempt_overtake()
       │                   ├─> Calculate success probability
       │                   ├─> Check slipstream effect
       │                   ├─> Consider attack mode advantage
       │                   └─> Return success/failure
       │                   │
       │                   └─> If successful:
       │                       └─> Swap car positions
       │
       ├─> CHECK RACE EVENTS (At lap start)
       │   │
       │   └─> _check_race_events()
       │       │
       │       ├─> Calculate current lap
       │       │
       │       └─> If new lap and not in safety car:
       │           │
       │           └─> events.check_lap_events()
       │               │
       │               ├─> Safety car check (3% chance):
       │               │   └─> If triggered:
       │               │       ├─> Set safety_car_active = True
       │               │       ├─> Set duration (3-6 minutes)
       │               │       └─> Log event
       │               │
       │               ├─> Crash check (1.5% per car):
       │               │   └─> For each active car:
       │               │       └─> If crashed:
       │               │           ├─> Mark as inactive
       │               │           ├─> Set dnf_reason = 'crash'
       │               │           └─> Log event
       │               │
       │               └─> Weather check (2% chance):
       │                   └─> If changed:
       │                       ├─> Update weather state
       │                       ├─> Update mu_weather
       │                       └─> Log event
       │
       ├─> UPDATE POSITIONS
       │   │
       │   └─> _update_positions()
       │       │
       │       ├─> Get all active cars
       │       │
       │       ├─> Sort by:
       │       │   ├─> Lap (descending)
       │       │   └─> Distance (descending)
       │       │
       │       ├─> Assign position ranks:
       │       │   └─> position_rank = 1, 2, 3, ...
       │       │
       │       └─> Update leader:
       │           └─> leader_id = first car in sorted list
       │
       ├─> UPDATE ATTACK MODES
       │   │
       │   └─> attack_mode.update_all(race_time)
       │       │
       │       └─> For each car:
       │           └─> Check if attack mode duration expired
       │               └─> If expired: Deactivate
       │
       ├─> RECORD HISTORY (Every 10 seconds)
       │   │
       │   └─> If race_time % 10.0 < time_step:
       │       └─> Append position snapshot to history
       │
       └─> PROGRESS UPDATE (Every 2 minutes)
           │
           └─> If race_time - last_update >= 120.0:
               └─> Print progress to console
```

### Phase 3: Race Completion

```
6. Race time limit reached
   │
   ├─> Exit main loop
   │
   ├─> _compile_results()
   │   │
   │   ├─> Collect final positions
   │   ├─> Collect final times
   │   ├─> Collect laps completed
   │   ├─> Summarize race events
   │   ├─> Calculate overtaking statistics
   │   └─> Create results dictionary
   │
   ├─> _print_final_classification()
   │   │
   │   └─> Print leaderboard to console
   │       ├─> Sort cars by position
   │       ├─> Display top 15
   │       └─> Show: Position, Car ID, Laps, Energy, Attack Mode, Status
   │
   └─> Generate visualizations
       │
       └─> RaceVisualizer.save_all()
           ├─> plot_leaderboard() → PNG file
           ├─> plot_energy_levels() → PNG file
           ├─> plot_track_map() → PNG file
           └─> plot_position_changes() → PNG file
```

## 🔄 Detailed Component Interactions

### Attack Mode Activation Flow

```
Lap Start (car completes lap)
    │
    └─> _try_activate_attack_mode(car_id)
        │
        ├─> Check: attack_mode_used < 2?
        │   └─> If no: Return (all used)
        │
        ├─> Calculate activation chance:
        │   ├─> Base: 30%
        │   ├─> If position > 10: 50% (behind)
        │   └─> If position < 3: 20% (leading)
        │
        ├─> Random check: chance < activation_chance?
        │   └─> If no: Return (don't activate)
        │
        └─> If yes:
            │
            └─> attack_mode.can_activate(
                    car_id, lap, time, distance
                )
                │
                ├─> Check: activations_remaining > 0?
                ├─> Check: Not already active?
                └─> Check: In activation zone?
                    │
                    └─> Returns: (can_activate: bool, reason: str)
                        │
                        └─> If can_activate:
                            │
                            └─> attack_mode.activate(
                                    car_id, lap, time, distance
                                )
                                │
                                ├─> Set state = ACTIVE
                                ├─> Set start_time = race_time
                                ├─> Decrement activations_remaining
                                └─> Record in history
```

### Overtaking Flow

```
Every 5 seconds during race
    │
    └─> _process_overtaking()
        │
        ├─> Skip if safety car active
        │
        ├─> Get active cars sorted by position
        │
        └─> For each pair (car ahead, car behind):
            │
            ├─> Calculate speed difference:
            │   └─> speed_diff = (behind_speed - ahead_speed) * 3.6
            │
            ├─> If speed_diff > 5 km/h:
            │   │
            │   └─> overtaking.attempt_overtake(
            │           attacker_id=behind,
            │           defender_id=ahead,
            │           attacker_speed=behind_speed,
            │           defender_speed=ahead_speed,
            │           gap_seconds=calculated_gap,
            │           track_position=normalized_position,
            │           attacker_has_attack_mode=bool,
            │           defender_has_attack_mode=bool,
            │           timestamp=race_time
            │       )
            │       │
            │       ├─> Calculate slipstream effect
            │       ├─> Get success probability
            │       ├─> Random roll for success
            │       └─> Return result dict
            │       │
            │       └─> If result['success']:
            │           └─> Swap positions
            │               └─> car_behind['distance'] += 10.0
```

### Safety Car Flow

```
At lap start
    │
    └─> _check_race_events()
        │
        └─> events.check_lap_events()
            │
            ├─> Random check: < 3% chance?
            │   └─> If yes:
            │       │
            │       ├─> Deploy safety car
            │       ├─> Set safety_car_active = True
            │       ├─> Set duration = 3-8 laps
            │       └─> Return in event dict
            │
            └─> RaceSimulator processes:
                │
                ├─> Set all cars to 80 km/h
                ├─> Log safety car event
                └─> Print notification
                    │
                    └─> Later: Update safety car each lap
                        └─> When laps_remaining = 0:
                            └─> End safety car
                                └─> Racing resumes
```

## 📊 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    RaceSimulator                            │
│                  (main_race_sim.py)                         │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ Manages:
               │ - car_states (dict of 20 cars)
               │ - race_state (dict)
               │ - time_step loop
               │
       ┌───────┴────────┬──────────────┬──────────────┐
       │                 │              │              │
       ▼                 ▼              ▼              ▼
┌─────────────┐   ┌─────────────┐  ┌─────────────┐ ┌─────────────┐
│   TRACK     │   │   EVENTS    │  │ OVERTAKING  │ │ ATTACK MODE │
│             │   │             │  │             │ │             │
│ Provides:   │   │ Provides:   │  │ Provides:   │ │ Provides:   │
│ - length    │   │ - safety_car│  │ - attempt() │ │ - is_active│
│ - curvature │   │ - crashes   │  │ - success   │ │ - activate()│
│ - mu        │   │ - weather   │  │ - slipstream│ │ - power_kw  │
└─────────────┘   └─────────────┘  └─────────────┘ └─────────────┘
       │                 │              │              │
       │                 │              │              │
       └─────────────────┴──────────────┴──────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ CAR STATES   │
                   │ (20 cars)    │
                   │              │
                   │ Updated each │
                   │ time step     │
                   └──────────────┘
```

## 🎯 Key Execution Points

### 1. Initialization (One-Time)
- **Duration**: ~1-2 seconds
- **Operations**: Track loading, component creation
- **Output**: Ready-to-race simulator

### 2. Race Loop (Repeated)
- **Frequency**: Every 0.5 seconds
- **Operations per step**: ~100
- **Duration**: Until race_time >= race_duration

### 3. Event Checks (Periodic)
- **Safety car**: Checked each lap
- **Crashes**: Checked each lap
- **Weather**: Checked each lap
- **Overtaking**: Checked every 5 seconds

### 4. Position Updates (Continuous)
- **Frequency**: Every time step
- **Method**: Sort by (lap, distance)
- **Result**: Updated position_rank for all cars

## 🔍 Example: 10 Seconds of Race

```
Time: 0.0s
├─> All cars at start line
├─> Positions: 1-20 (grid order)
└─> Energy: 52.0 kWh each

Time: 0.5s
├─> Car 0: distance = 25m, energy = 51.997 kWh
├─> Car 1: distance = 24.8m, energy = 51.997 kWh
└─> ... (all 20 cars)

Time: 1.0s
├─> Car 0: distance = 50m
└─> ... (continues)

Time: 5.0s
├─> Overtaking check triggered
├─> Car 5 attempts to overtake Car 4
└─> Success! Positions swapped

Time: 10.0s
├─> Position history recorded
└─> Snapshot saved

Time: 90.0s (Lap 1 complete for leader)
├─> Leader completes lap
├─> Attack mode activation attempted
└─> Car 0 activates attack mode (if conditions met)
```

This architecture ensures efficient, realistic race simulation with proper separation of concerns!

