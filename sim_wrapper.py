import random
import pandas as pd

# -----------------------------------------------------------------
# SECTION 1: THE "PLACEHOLDER" SIMULATOR
#
# This is a temporary, FAKE simulator that *pretends* to be
# the complex TUMFTM code. We use this so your app can run
# before Person A is finished.
#
# LATER: You will replace this with the REAL imports from the 'src'
# folder, like:
# from src.race_simulator import RaceSimulator
# -----------------------------------------------------------------

class OriginalTUMFTMSimulator_Placeholder:
    """
    This is a FAKE F1 simulator. Its only job is to provide
    F1-style data (like 'pos', 'tire_wear') so that your
    'FormulaESimulator' class has something to translate.
    """
    def __init__(self):
        print("--- LOADING PLACEHOLDER F1 SIM ---")
        self.current_lap = 0
        self.position = 10
        self.tire_wear = 0.0
        # The F1 sim has no concept of "energy_pct" or "attack_mode"

    def run_one_lap(self):
        """Pretends to run one lap."""
        self.current_lap += 1
        self.position = max(1, self.position + random.choice([-1, 0, 1]))
        self.tire_wear = min(1.0, self.current_lap * 0.022)

    def get_f1_state(self):
        """Returns a FAKE F1-style state dictionary."""
        return {
            'lap': self.current_lap,
            'pos': self.position,
            'tire': self.tire_wear,
            'gap': random.uniform(0.5, 2.0)
        }

# -----------------------------------------------------------------
# SECTION 2: YOUR *REAL* WRAPPER CLASS
#
# This is the *only* class your main 'war_room_app.py' will
# ever talk to. Its job is to hide the complexity of the
# sim and enforce the 'CONTRACT.md'.
# -----------------------------------------------------------------

class FormulaESimulator:
    """
    This class "wraps" the sim. It loads the simulator (right now,
    the placeholder) and translates its F1 output into the
    Formula-E `CONTRACT.md` format.
    """
    def __init__(self):
        # 1. Load the simulator.
        #    We are loading the PLACEHOLDER for now.
        #
        #    *** LATER, YOU WILL CHANGE THIS: ***
        #    self.sim = RaceSimulator()  <-- (The REAL one)
        #
        self.sim = OriginalTUMFTMSimulator_Placeholder()
        
    def run_lap(self):
        """
        This function calls the *real* sim's logic for running one lap.
        """
        self.sim.run_one_lap()
        
    def get_current_state(self, car_id="My_AI") -> dict:
        """
        This is the most important part of your job.
        It gets the F1 data and FORCES it into your FE contract.
        """
        
        # 1. Get the raw state from the (placeholder) F1 sim
        f1_state = self.sim.get_f1_state()
        
        # 2. Translate the F1 data into your FE contract format.
        #    This is where you "fake" the FE-specific fields
        #    that the original F1 sim doesn't have.
        
        state_contract = {
            'lap': f1_state.get('lap', 0),
            'position': f1_state.get('pos', 10),
            'tire_wear': f1_state.get('tire', 0.0),
            'gap_to_front': f1_state.get('gap', 1.5),

            # --- FAKE (TRANSLATED) FIELDS ---
            
            # FAKE IT: The F1 sim doesn't have "energy_pct".
            # We'll just calculate a fake one based on lap.
            # (Person A will make this real later)
            'energy_pct': max(0.0, 100.0 - (f1_state.get('lap', 0) * 2.2)),
            
            # FAKE IT: The F1 sim doesn't have "attack_modes_left".
            # We'll just hardcode it for now.
            # (Person A will make this real later)
            'attack_modes_left': 2,
            
            # FAKE IT: The F1 sim doesn't track safety cars this way.
            # (Person A will make this real later)
            'safety_car_out': False
        }
        
        return state_contract
