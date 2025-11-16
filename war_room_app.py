import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import json
import random

# --- 1. IMPORT YOUR DUMMY ARTIFACTS ---
from dummy_surrogate_model import load_race_model, load_tire_model

@st.cache_resource
def load_dp_strategy():
    """Loads the (dummy) DP strategy map."""
    print("--- LOADING DUMMY DP MAP ---")
    with open('dummy_strategy_map.json', 'r') as f:
        return json.load(f)

# Load ALL the models
DP_STRATEGY_MAP = load_dp_strategy()
RACE_MODEL = load_race_model()
TIRE_MODEL = load_tire_model()


# --- 2. SETUP THE UI ---
st.set_page_config(layout="wide")
st.title("🚀 Formula-E Strategy War Room")

col1, col2, col3 = st.columns(3)
metric_lap = col1.empty()
metric_pos = col2.empty()
metric_energy = col3.empty()

st.subheader("🧠 AI Strategy Layer")
col_ai_1, col_ai_2, col_ai_3 = st.columns(3)
recommendation_placeholder = col_ai_1.empty()
counterfactual_placeholder = col_ai_2.empty()
tire_model_placeholder = col_ai_3.empty()

chart_placeholder_pos = st.empty()
chart_placeholder_energy = st.empty()

st.subheader("Live Strategy Log")
log_placeholder = st.empty()


# --- 3. THE (ADVANCED) FAKE SIMULATION LOOP ---

def get_fake_move():
    return random.choice([-1, 0, 0, 0, 1])

if 'app_data' not in st.session_state:
    st.session_state.app_data = {
        'cars': {},
        'plot_data': {},
        'strategy_log': ""
    }

if st.button("Start Race Simulation"):
    
    st.session_state.app_data['cars'] = {
        'My_AI': {'position': 10, 'energy': 100.0, 'attack_modes': 2, 'tire_wear': 0.0},
        'Opp_A': {'position': 9, 'energy': 100.0, 'tire_wear': 0.0},
        'Opp_B': {'position': 11, 'energy': 100.0, 'tire_wear': 0.0}
    }
    
    st.session_state.app_data['plot_data'] = {
        'lap': [],
        'My_AI_pos': [], 'Opp_A_pos': [], 'Opp_B_pos': [],
        'My_AI_energy': [], 'Opp_A_energy': [], 'Opp_B_energy': []
    }
    st.session_state.app_data['strategy_log'] = ""

    for lap in range(1, 46):
        
        # --- (A) ADVANCED FAKE SIM LOGIC ---
        for car_name, data in st.session_state.app_data['cars'].items():
            if car_name != 'My_AI':
                data['position'] = max(1, data['position'] + get_fake_move())
            
            data['energy'] -= 2.2 + random.uniform(-0.3, 0.3)
            data['tire_wear'] = min(1.0, data['tire_wear'] + 0.022 + random.uniform(-0.005, 0.005))
        
        
        # --- (B) YOUR INTEGRATION LOGIC ---
        ai_data = st.session_state.app_data['cars']['My_AI']
        current_state = {
            'lap': lap,
            'position': ai_data['position'],
            'energy_pct': ai_data['energy'],
            'gap_to_front': abs(ai_data['position'] - st.session_state.app_data['cars']['Opp_A']['position']),
            'attack_modes_left': ai_data['attack_modes'],
            'tire_wear': ai_data['tire_wear'],
            'safety_car_out': False
        }
        
        energy_bin = int(current_state['energy_pct'] // 5 * 5)
        dp_key = f"{lap}_{current_state['position']}_{energy_bin}"
        dp_recommendation = DP_STRATEGY_MAP.get(dp_key, "WAIT")
        
        if dp_recommendation == "ATTACK":
            ai_data['position'] = max(1, ai_data['position'] - 1)
            ai_data['energy'] -= 0.5
            
        
        state_df = pd.DataFrame([current_state])
        race_preds = RACE_MODEL.predict(state_df)
        tire_preds = TIRE_MODEL.predict_wear(state_df)
        
        p_win = race_preds['P(Win)']
        
        counterfactual_gain = 0.0
        if dp_recommendation == "ATTACK":
            counterfactual_gain = random.uniform(0.05, 0.15)
        p_win_with_action = p_win + counterfactual_gain
        

        # --- (C) UPDATE THE DASHBOARD ---
        
        metric_lap.metric("Lap", f"{lap} / 45")
        metric_pos.metric("Position", f"P{current_state['position']}")
        metric_energy.metric("Energy", f"{current_state['energy_pct']:.1f}%")

        recommendation_placeholder.metric("DP Recommends:", dp_recommendation)
        
        delta_color = "normal" if counterfactual_gain == 0.0 else "inverse"
        counterfactual_placeholder.metric(
            f"P(Win) if {dp_recommendation}",
            f"{p_win_with_action:.1%}", 
            f"Gain: +{counterfactual_gain:.1%}",
            delta_color=delta_color
        )
        
        # Update NEW Tire Model Panel
        final_wear = tire_preds['Predicted_Final_Wear']
        risk = tire_preds['Cliff_Risk']
        
        # --- !!! THIS IS THE FIX !!! ---
        # We change "error" to "inverse", which Streamlit accepts.
        tire_color = "inverse" if risk == "High" else "normal"
        # --- !!! END OF FIX !!! ---
        
        tire_model_placeholder.metric(
            "Tire Model: Pred. Final Wear",
            f"{final_wear:.0%}",
            f"Risk: {risk}",
            delta_color=tire_color
        )
        
        # --- Update Plot Data ---
        plot_data = st.session_state.app_data['plot_data']
        plot_data['lap'].append(lap)
        for car_name, data in st.session_state.app_data['cars'].items():
            plot_data[f'{car_name}_pos'].append(data['position'])
            plot_data[f'{car_name}_energy'].append(data['energy'])
        
        # --- Update Position Chart ---
        fig_pos = go.Figure()
        fig_pos.add_trace(go.Scatter(x=plot_data['lap'], y=plot_data['My_AI_pos'], name="My AI", mode='lines+markers', line=dict(width=4)))
        fig_pos.add_trace(go.Scatter(x=plot_data['lap'], y=plot_data['Opp_A_pos'], name="Opponent A", mode='lines', line=dict(dash='dot', color='grey')))
        fig_pos.add_trace(go.Scatter(x=plot_data['lap'], y=plot_data['Opp_B_pos'], name="Opponent B", mode='lines', line=dict(dash='dot', color='grey')))
        fig_pos.update_layout(title="Live Race Position", yaxis_title="Position", xaxis_title="Lap")
        fig_pos.update_yaxes(autorange="reversed")
        chart_placeholder_pos.plotly_chart(fig_pos, use_container_width=True)
        
        # --- Update NEW Energy Chart ---
        fig_energy = go.Figure()
        fig_energy.add_trace(go.Scatter(x=plot_data['lap'], y=plot_data['My_AI_energy'], name="My AI Energy", line=dict(color='blue')))
        fig_energy.add_trace(go.Scatter(x=plot_data['lap'], y=plot_data['Opp_A_energy'], name="Opp A Energy", line=dict(dash='dot', color='grey')))
        fig_energy.add_trace(go.Scatter(x=plot_data['lap'], y=plot_data['Opp_B_energy'], name="Opp B Energy", line=dict(dash='dot', color='grey')))
        fig_energy.update_layout(title="Live Energy Remaining", yaxis_title="Energy %", xaxis_title="Lap")
        fig_energy.update_yaxes(range=[0, 100])
        chart_placeholder_energy.plotly_chart(fig_energy, use_container_width=True)
        
        # --- Update Strategy Log ---
        log_entry = f"Lap {lap}: P{current_state['position']} ({current_state['energy_pct']:.1f}% E). Decision: {dp_recommendation}. P(Win): {p_win:.1%}\n"
        st.session_state.app_data['strategy_log'] = log_entry + st.session_state.app_data['strategy_log']
        log_placeholder.text_area("Log", st.session_state.app_data['strategy_log'], height=200)

        time.sleep(0.3)
        
    st.session_state.running = False
