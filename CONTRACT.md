# --- PROJECT API CONTRACT (v1) ---
# All 3 team members MUST follow this.

## 1. The "RaceState" Dictionary
# This is the standard data object we will pass around.
# Person C provides this. Person A & B consume this.
RACE_STATE = {
    'lap': 15,                # int
    'position': 5,            # int
    'energy_pct': 60.5,       # float
    'gap_to_front': 1.2,      # float
    'attack_modes_left': 1,   # int
    'tire_wear': 0.35,        # float (0.0 to 1.0)
    'safety_car_out': False   # bool
}

## 2. Person A: The DP Optimizer
# FILE NAME: `strategy_map.json`
# FORMAT: A JSON dictionary.
# KEY: A string key: "lap_pos_energy_bin"
#   - lap: 1-45
#   - pos: 1-20
#   - energy_bin: 5-degree bins (e.g., 60, 65, 70)
#   - Example key: "15_5_60"
# VALUE: A string: "ATTACK" or "WAIT"
#
# EXAMPLE:
# {
#     "15_5_60": "ATTACK",
#     "15_5_55": "WAIT"
# }

## 3. Person B: The Surrogate Predictor
# FILE NAME: `surrogate_model.pkl` (or a .py file with a load_model() function)
# FUNCTION: The loaded model object MUST have a `.predict()` method.
# INPUT: A `pandas.DataFrame` where each row is a `RACE_STATE`.
# OUTPUT: A dictionary of predictions. MUST contain these keys.
#
# EXAMPLE:
# model.predict(state_df)
#
# Returns ->
# {
#     'P(Win)': 0.35,
#     'P(Top3)': 0.60,
#     'Expected_Pos': 4.5
# }

