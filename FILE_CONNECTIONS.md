# File Connections - Visual Guide

## 📁 Directory Structure

```
laptime-simulation/
│
├── main_race_sim.py          ← ENTRY POINT (you run this)
│
├── race_sim/                 ← NEW RACE SIMULATION MODULES
│   ├── __init__.py
│   ├── race_events.py        ← Safety car, crashes, weather
│   ├── overtaking.py         ← Overtaking logic
│   ├── attack_mode.py        ← Attack Mode system
│   ├── pit_strategy.py       ← Pit stop decisions
│   ├── driver_race.py        ← Extended driver strategy
│   ├── race_strategy_optimizer.py  ← Pre-race optimization
│   └── race_visualizer.py    ← Visualization tools
│
└── laptimesim/               ← EXISTING LAP TIME SIMULATOR
    └── src/
        ├── track.py          ← Track geometry (REUSED)
        ├── car_electric.py   ← Car physics (REUSED)
        ├── driver.py         ← Base driver (EXTENDED)
        └── lap.py            ← Lap solver (REFERENCE)
```

## 🔗 Import Chain

```
main_race_sim.py
    │
    ├─> import laptimesim.src.track
    │   └─> (existing module)
    │
    ├─> from race_sim.race_events import RaceEvents
    │   └─> race_sim/race_events.py
    │       └─> import numpy
    │
    ├─> from race_sim.overtaking import OvertakingModel
    │   └─> race_sim/overtaking.py
    │       └─> import numpy
    │
    ├─> from race_sim.attack_mode import AttackModeManager
    │   └─> race_sim/attack_mode.py
    │       └─> import numpy
    │
    └─> from race_sim.pit_strategy import PitStrategy
        └─> race_sim/pit_strategy.py
            └─> import numpy
```

## 🔄 Runtime Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    main_race_sim.py                          │
│                                                              │
│  def main():                                                 │
│      simulator = RaceSimulator(...)                          │
│      results = simulator.run_race()                         │
│      visualizer.save_all(...)                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   RaceSimulator.__init__()    │
        └──────────────┬───────────────┘
                       │
        ┌──────────────┼───────────────┐
        │              │               │
        ▼              ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│_initialize_ │  │_initialize_ │  │_initialize_│
│  _track()   │  │race_compone │  │car_states() │
│             │  │    nts()    │  │             │
│             │  │             │  │             │
│ Uses:       │  │ Creates:    │  │ Creates:    │
│ track.py    │  │ RaceEvents  │  │ 20 car      │
│             │  │ Overtaking  │  │ states      │
│             │  │ AttackMode  │  │             │
│             │  │ PitStrategy │  │             │
└─────────────┘  └─────────────┘  └─────────────┘
        │              │               │
        └──────────────┴───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │    RaceSimulator.run_race()   │
        │                               │
        │    while race_time < duration:│
        │        _update_car()          │
        │        _process_overtaking()  │
        │        _check_race_events()   │
        │        _update_positions()    │
        └──────────────┬────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│_update_car()│  │_process_    │  │_check_race_ │
│             │  │overtaking() │  │  events()   │
│             │  │             │  │             │
│ Calls:      │  │ Calls:      │  │ Calls:     │
│ attack_mode │  │ overtaking. │  │ events.     │
│ .is_active()│  │ attempt_    │  │ check_lap_  │
│ attack_mode │  │ overtake()  │  │ events()    │
│ .activate() │  │             │  │             │
│ pit_strategy│  │             │  │             │
│ .should_pit │  │             │  │             │
└─────────────┘  └─────────────┘  └─────────────┘
```

## 📊 Data Flow Between Modules

### 1. Track Data Flow
```
track.py (existing)
    │
    └─> Provides:
        ├─> track_length (float)
        ├─> dists_cl (array) - distances along track
        ├─> kappa (array) - curvature
        └─> mu (array) - friction
        │
        └─> Used by:
            └─> RaceSimulator
                ├─> For calculating car positions
                ├─> For lap completion checks
                └─> For track visualization
```

### 2. Car State Data Flow
```
RaceSimulator.car_states[car_id]
    │
    ├─> Read by:
    │   ├─> _update_car() - updates each time step
    │   ├─> _process_overtaking() - checks positions
    │   ├─> _update_positions() - sorts by position
    │   └─> _check_race_events() - checks active status
    │
    └─> Modified by:
        ├─> _update_car() - distance, energy, speed, lap
        ├─> _process_overtaking() - position swaps
        ├─> _check_race_events() - active flag (crashes)
        └─> _update_positions() - position_rank
```

### 3. Race Events Data Flow
```
RaceEvents.check_lap_events()
    │
    └─> Returns: {
          'safety_car': bool,
          'crashed_cars': List[int],
          'weather_change': bool,
          'new_weather': str,
          'mu_weather': float
        }
    │
    └─> Used by:
        └─> RaceSimulator._check_race_events()
            ├─> Sets race_state['safety_car_active']
            ├─> Marks cars as inactive
            └─> Updates race_state['mu_weather']
```

### 4. Overtaking Data Flow
```
OvertakingModel.attempt_overtake()
    │
    ├─> Input:
    │   ├─> attacker_id, defender_id
    │   ├─> speeds (km/h)
    │   ├─> gap_seconds
    │   └─> attack mode status
    │
    └─> Returns: {
          'success': bool,
          'speed_differential_kmh': float,
          'time_gain': float
        }
    │
    └─> Used by:
        └─> RaceSimulator._process_overtaking()
            └─> If success: Swap car positions
```

### 5. Attack Mode Data Flow
```
AttackModeManager
    │
    ├─> is_active(car_id, race_time)
    │   └─> Returns: bool
    │       └─> Used by: _update_car() for speed boost
    │
    ├─> can_activate(car_id, lap, time, distance)
    │   └─> Returns: (bool, str)
    │       └─> Used by: _try_activate_attack_mode()
    │
    └─> activate(car_id, time)
        └─> Sets attack mode active for 4 minutes
            └─> Used by: _try_activate_attack_mode()
```

## 🎯 Key Integration Points

### Integration Point 1: Track Loading
```python
# In RaceSimulator._initialize_track()
import laptimesim.src.track

track_opts = {...}
self.track = laptimesim.src.track.Track(
    pars_track=track_opts,
    parfilepath=parfilepath,
    trackfilepath=trackfilepath,
    ...
)
self.track_length = self.track.dists_cl[-1]
```

### Integration Point 2: Event System
```python
# In RaceSimulator._check_race_events()
lap_events = self.events.check_lap_events(
    current_lap,
    self.race_state['race_time'],
    active_cars
)

if lap_events['safety_car']:
    self.race_state['safety_car_active'] = True
```

### Integration Point 3: Overtaking
```python
# In RaceSimulator._process_overtaking()
result = self.overtaking.attempt_overtake(
    car_behind_id,
    car_ahead_id,
    speed_behind * 3.6,
    speed_ahead * 3.6,
    distance_behind,
    self.race_state['race_time'],
    in_drs_zone=False
)

if result['success']:
    # Swap positions
    self.car_states[car_behind_id]['distance'] += 10.0
```

### Integration Point 4: Attack Mode
```python
# In RaceSimulator._update_car()
if self.attack_mode.is_active(car_id, self.race_state['race_time']):
    base_speed *= 1.08  # +8% speed boost

# In RaceSimulator._try_activate_attack_mode()
if self.attack_mode.activate(car_id, self.race_state['race_time']):
    car['attack_mode_used'] += 1
```

## 🔄 Call Sequence Example

### During One Time Step (0.5 seconds):

```
RaceSimulator.run_race() [time = 120.5s]
    │
    ├─> _update_car(0)
    │   ├─> attack_mode.is_active(0, 120.5) → False
    │   ├─> Calculate speed → 50 m/s
    │   ├─> Update distance → += 25m
    │   ├─> Update energy → -= 0.0029 kWh
    │   └─> Check lap completion → No
    │
    ├─> _update_car(1)
    │   └─> (same process)
    │
    ├─> ... (cars 2-19)
    │
    ├─> _process_overtaking()
    │   ├─> Check: time % 5.0 < time_step? → No (skip)
    │   └─> (Only runs every 5 seconds)
    │
    ├─> _check_race_events()
    │   ├─> Calculate current_lap → 2
    │   ├─> Check: new lap? → No (already checked)
    │   └─> (Only checks at lap start)
    │
    ├─> _update_positions()
    │   ├─> Sort cars by (lap, distance)
    │   └─> Assign position_rank
    │
    └─> Record history (if time % 10.0 < time_step)
```

### During Lap Start:

```
RaceSimulator.run_race() [time = 90.0s, Lap 2 starts]
    │
    ├─> _update_car(0)
    │   ├─> distance >= track_length → Yes
    │   ├─> lap += 1 → 2
    │   ├─> distance -= track_length
    │   └─> _try_activate_attack_mode(0)
    │       ├─> attack_mode.can_activate(0, 2, 90.0, 0.0)
    │       └─> attack_mode.activate(0, 90.0) → Success
    │
    ├─> _check_race_events()
    │   ├─> current_lap = 2 (new lap)
    │   └─> events.check_lap_events(2, 90.0, active_cars)
    │       ├─> Safety car check → 3% chance → No
    │       ├─> Crash check → 1.5% per car → Car 5 crashed!
    │       └─> Weather check → 2% chance → No
    │
    └─> Process crash:
        ├─> car_states[5]['active'] = False
        └─> car_states[5]['dnf_reason'] = 'crash'
```

## 📦 Module Responsibilities

| Module | Responsibility | Dependencies |
|--------|---------------|--------------|
| `main_race_sim.py` | Main orchestrator | All other modules |
| `race_events.py` | Random events | numpy |
| `overtaking.py` | Car-to-car overtaking | numpy |
| `attack_mode.py` | Attack Mode system | numpy |
| `pit_strategy.py` | Pit stop logic | numpy |
| `track.py` | Track geometry | trajectory_planning_helpers |
| `driver_race.py` | Strategic decisions | driver.py (base) |
| `race_visualizer.py` | Visualizations | matplotlib |

## 🚀 Execution Order

1. **Import Phase**: All modules imported
2. **Initialization Phase**: 
   - Track loaded
   - Components created
   - Cars initialized
3. **Race Phase**: 
   - Time-step loop runs
   - All systems update each step
4. **Completion Phase**:
   - Results compiled
   - Visualizations generated

This architecture ensures clean separation of concerns while maintaining efficient execution!

