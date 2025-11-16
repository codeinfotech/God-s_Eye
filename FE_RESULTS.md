# Formula E Simulation Results

## How to Run FE Simulation

1. **Configure vehicle parameters** in `main_laptimesim.py`:
   - Set `solver_opts_["vehicle"]` to `"FE_Berlin.ini"`
   - Set `solver_opts_["series"]` to `"FE"`
   - Set `track_opts_["use_drs1"]` and `["use_drs2"]` to `False`
   - Set `driver_opts_["initial_energy"]` to `4.58e6` (4.58 MJ)

2. **Install dependencies**:
   ```bash
   pip install numpy matplotlib trajectory_planning_helpers utm pytest
   ```

3. **Run simulation**:
   ```bash
   python main_laptimesim.py
   ```

## Key Vehicle Differences: F1 vs FE

| Parameter | F1 Hybrid | FE Electric |
|-----------|-----------|-------------|
| **Powertrain** | ICE (575 kW) + E-motor (120 kW) | E-motor only (200 kW) |
| **Mass** | 733 kg | 880 kg (+20%) |
| **Gearbox** | 8-speed | 2-speed |
| **Aerodynamics** | High downforce (c_z_a: 2.20/2.68) | Lower downforce (c_z_a: 1.24/1.52) |
| **Drag** | c_w_a: 1.56 m² | c_w_a: 1.15 m² (-26%) |
| **DRS** | Enabled (17% drag reduction) | Disabled |
| **Recuperation** | Low efficiency (15%) | High efficiency (90%) |

## Simulation Results

**Test Configuration:** Shanghai International Circuit, FE Berlin vehicle parameters

- **Lap Time:** 132.079 seconds (2:12.079)
- **Energy Consumption:** 19,580 kJ/lap (5.44 kWh)
- **Average Speed:** 179 km/h
- **Energy per Sector:** S1: 35.054s, S2: 39.330s, S3: 57.694s

**Interpretation:** The simulation shows energy consumption significantly exceeds the initial 4.58 MJ allocation, indicating aggressive driving or suboptimal energy management. The consistent start/final velocity (179.2 km/h) confirms a closed lap. The longer S3 sector suggests higher energy consumption in the final sector, potentially due to track characteristics or energy depletion.

## Use Cases

This simulation is valuable for:
- **Energy Strategy:** Optimizing power deployment and recuperation to complete races within energy limits
- **Performance Analysis:** Comparing lap times and energy efficiency across different vehicle configurations
- **Race Planning:** Determining optimal lift-and-coast points and energy allocation strategies
- **Parameter Sensitivity:** Evaluating impact of mass, aerodynamics, and powertrain changes on performance

## Next Steps

1. **Energy Management:** Implement lift-and-coast strategies (`use_lift_coast: True`) to reduce consumption
2. **Track Optimization:** Test on FE-specific tracks (e.g., Berlin street circuit) for more realistic results
3. **Strategy Refinement:** Adjust `em_strategy` and `initial_energy` to match race regulations
4. **Sensitivity Analysis:** Run parameter sweeps for mass, aero, and powertrain efficiency
5. **Validation:** Compare results against real-world FE race data for model calibration

