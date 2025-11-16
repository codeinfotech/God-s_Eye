import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import RegularPolygon, Circle
import traceback
from enum import Enum

# --- Track Definition ---
track_points = np.array([
    [150, 550], [200, 500], [300, 450], [400, 400], [480, 360], [550, 350],
    [600, 360], [650, 420], [700, 480], [720, 530], [700, 580], [650, 590],
    [600, 600], [550, 580], [500, 540], [450, 500], [400, 460], [350, 430],
    [300, 410], [250, 420], [200, 460], [160, 510], [150, 550]
])

# --- Parameters ---
num_samples = 3000
dt = 0.05

# Vehicle dynamics
max_speed = 200.0
min_speed = 30.0
lookahead_dist = 120.0
max_accel = 300.0
max_decel = 600.0

# Game theory parameters
OVERTAKE_GAP = 35.0
SLIPSTREAM_GAP = 55.0
SLIPSTREAM_BOOST = 18.0
DEFEND_GAP = 45.0
PRESSURE_GAP = 65.0

# Skill-based parameters
SKILL_LEVELS = {
    'ELITE': {'corner_speed': 1.12, 'brake_point': 0.92, 'consistency': 0.95, 'mistake_prob': 0.002},
    'EXPERT': {'corner_speed': 1.08, 'brake_point': 0.95, 'consistency': 0.90, 'mistake_prob': 0.005},
    'SKILLED': {'corner_speed': 1.04, 'brake_point': 0.98, 'consistency': 0.85, 'mistake_prob': 0.010},
    'AVERAGE': {'corner_speed': 1.00, 'brake_point': 1.00, 'consistency': 0.80, 'mistake_prob': 0.015},
    'NOVICE': {'corner_speed': 0.96, 'brake_point': 1.03, 'consistency': 0.70, 'mistake_prob': 0.025},
}

# Enhanced randomness parameters
CONTROL_NOISE_SIGMA = {
    'ELITE': 0.01,   'EXPERT': 0.02,   'SKILLED': 0.03,
    'AVERAGE': 0.05, 'NOVICE': 0.08,
}

# Random walk drift parameters
DRIFT_RATE = 0.0005  # Per-frame drift in skill attributes
DRIFT_BOUNDS = {'corner_speed': (0.88, 1.18), 'brake_point': (0.85, 1.10), 'consistency': (0.55, 0.98)}

# Mistake events
LOCKUP_DURATION = 20
LOCKUP_SPEED_PENALTY = 0.65  # Multiplier during lockup
MISSED_APEX_DURATION = 10
MISSED_APEX_PENALTY = 0.85

# Tire degradation (nonlinear)
TIRE_DEG_BASE_RATE = 0.00008
TIRE_DEG_EXPONENTIAL = 1.3  # Exponential factor for nonlinear wear
MAX_TIRE_DEG = 0.12

# Decision payoff noise
PAYOFF_NOISE_SCALE = 8.0

# Attack windows
STRAIGHT_CURVATURE_THRESHOLD = 0.15
WIDE_CORNER_THRESHOLD = 0.35
TIGHT_CORNER_THRESHOLD = 0.5

# Strategy parameters
PREDICTION_HORIZON = 1.0
ATTACK_COOLDOWN = 80
DEFEND_COOLDOWN = 60
COMMIT_DURATION = 40
MIN_CLOSING_RATE = 5.0

# PID gains
Kp = 4.0
Ki = 0.5
Kd = 0.8

DEBUG = False

# --- Spline utilities ---
use_scipy = True
try:
    from scipy import interpolate
except Exception:
    use_scipy = False

def make_dense_track_with_scipy(points, num_samples=2000, smoothing=0):
    pts = points[:-1].T
    tck, u = interpolate.splprep(pts, s=smoothing, per=1)
    u_dense = np.linspace(0, 1, max(num_samples, 1000))
    x_dense, y_dense = interpolate.splev(u_dense, tck)
    dense = np.vstack([x_dense, y_dense]).T
    diffs = np.diff(dense, axis=0)
    seg_lens = np.sqrt((diffs ** 2).sum(axis=1))
    cumlen = np.concatenate([[0.0], np.cumsum(seg_lens)])
    total_len = cumlen[-1]
    desired_d = np.linspace(0, total_len, num_samples)
    u_uniform = np.interp(desired_d, cumlen, u_dense)
    x_unif, y_unif = interpolate.splev(u_uniform, tck)
    track_dense = np.vstack([x_unif, y_unif]).T
    return track_dense, total_len

def make_dense_track_fallback(points, n_per_segment=50):
    interpolated = []
    for i in range(len(points) - 1):
        seg = np.linspace(points[i], points[i + 1], n_per_segment, endpoint=False)
        interpolated.extend(seg)
    interpolated.append(points[-1])
    track_dense = np.array(interpolated)
    diffs = np.diff(track_dense, axis=0)
    seg_lens = np.sqrt((diffs ** 2).sum(axis=1))
    total_len = seg_lens.sum()
    return track_dense, total_len

# Build track
if not np.allclose(track_points[0], track_points[-1]):
    track_points = np.vstack([track_points, track_points[0]])

if use_scipy:
    try:
        track_points_dense, track_length = make_dense_track_with_scipy(track_points, num_samples=num_samples, smoothing=0)
    except Exception as e:
        print("scipy failed, fallback:", e)
        track_points_dense, track_length = make_dense_track_fallback(track_points, n_per_segment=50)
else:
    track_points_dense, track_length = make_dense_track_fallback(track_points, n_per_segment=100)

diffs = np.diff(track_points_dense, axis=0)
segment_lengths = np.sqrt((diffs ** 2).sum(axis=1))
cum_lengths = np.concatenate([[0.0], np.cumsum(segment_lengths)])
total_length = cum_lengths[-1]

def get_position(distance):
    distance = distance % total_length
    i = np.searchsorted(cum_lengths, distance, side='right') - 1
    if i >= len(track_points_dense) - 1:
        return track_points_dense[0].copy()
    seg_start = track_points_dense[i]
    seg_end = track_points_dense[i + 1]
    seg_len = segment_lengths[i]
    if seg_len == 0:
        return seg_start.copy()
    ratio = (distance - cum_lengths[i]) / seg_len
    pos = seg_start + ratio * (seg_end - seg_start)
    return pos

def get_heading(distance, ahead=1.0):
    a = get_position(distance)
    b = get_position(distance + ahead)
    vec = b - a
    return np.arctan2(vec[1], vec[0])

def get_curvature(distance, lookahead=lookahead_dist):
    a = get_position(distance)
    mid = get_position(distance + lookahead * 0.4)
    far = get_position(distance + lookahead)
    v1 = mid - a
    v2 = far - mid
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    cosang = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
    angle = np.arccos(cosang)
    return abs(angle)

def turn_sharpness_to_target_speed(curvature):
    norm = np.clip(curvature / (np.pi * 0.6), 0.0, 1.0)
    target = min_speed + (max_speed - min_speed) * (1.0 - norm)
    return target

# --- PID Controller ---
class PID:
    def _init_(self, Kp, Ki, Kd, dt, out_min=-np.inf, out_max=np.inf):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.dt = dt
        self.out_min = out_min
        self.out_max = out_max
        self.integral = 0.0
        self.prev_error = None

    def update(self, error):
        self.integral += error * self.dt
        self.integral = np.clip(self.integral, -1000.0, 1000.0)
        deriv = 0.0
        if self.prev_error is not None:
            deriv = (error - self.prev_error) / self.dt
        self.prev_error = error
        out = self.Kp * error + self.Ki * self.integral + self.Kd * deriv
        out = np.clip(out, self.out_min, self.out_max)
        return out

    def reset(self):
        self.integral = 0.0
        self.prev_error = None

# --- Racing State Machine ---
class RaceState(Enum):
    CRUISE = "CRUISE"
    PRESSURE = "PRESSURE"
    ATTACK = "ATTACK"
    COMMIT = "COMMIT"
    DEFEND = "DEFEND"
    WAIT = "WAIT"

class AttackType(Enum):
    NONE = "NONE"
    INSIDE = "INSIDE"
    OUTSIDE = "OUTSIDE"

# --- Racing Agent with Advanced Stochasticity ---
class RacingAgent:
    def _init_(self, agent_id, start_distance, color, skill_level='AVERAGE'):
        self.id = agent_id
        self.distance = start_distance
        self.speed = 80.0
        self.lap_count = 0
        self.pid = PID(Kp, Ki, Kd, dt, out_min=-max_decel, out_max=max_accel)
        self.color = color
        self.base_color = color
        
        # Skill level
        self.skill_level = skill_level
        self.skill_params = SKILL_LEVELS[skill_level].copy()
        self.control_noise_sigma = CONTROL_NOISE_SIGMA[skill_level]
        
        # FSM state
        self.state = RaceState.CRUISE
        self.attack_type = AttackType.NONE
        
        # Cooldowns
        self.attack_cooldown = 0
        self.defend_cooldown = 0
        self.commit_timer = 0
        
        # History
        self.speed_history = []
        self.gap_closing_rate = 0.0
        
        # Stochastic skill drift (random walk)
        self.current_corner_speed = self.skill_params['corner_speed']
        self.current_brake_point = self.skill_params['brake_point']
        self.current_consistency = self.skill_params['consistency']
        
        # Mistake events
        self.lockup_timer = 0
        self.missed_apex_timer = 0
        
        # Tire degradation (nonlinear cumulative)
        self.tire_distance = 0.0
        self.tire_deg = 0.0
        
        # Energy management
        self.energy_management = np.random.uniform(0.97, 1.03)
        
        # Visual feedback
        self.recent_performance = 1.0
        
    def apply_stochastic_drift(self):
        """Random walk for skill attributes"""
        # Corner speed drift
        drift_cs = np.random.normal(0, DRIFT_RATE)
        self.current_corner_speed = np.clip(
            self.current_corner_speed + drift_cs,
            DRIFT_BOUNDS['corner_speed'][0],
            DRIFT_BOUNDS['corner_speed'][1]
        )
        
        # Brake point drift
        drift_bp = np.random.normal(0, DRIFT_RATE * 0.5)
        self.current_brake_point = np.clip(
            self.current_brake_point + drift_bp,
            DRIFT_BOUNDS['brake_point'][0],
            DRIFT_BOUNDS['brake_point'][1]
        )
        
        # Consistency drift
        drift_cons = np.random.normal(0, DRIFT_RATE * 2)
        self.current_consistency = np.clip(
            self.current_consistency + drift_cons,
            DRIFT_BOUNDS['consistency'][0],
            DRIFT_BOUNDS['consistency'][1]
        )
        
        # Update performance metric
        self.recent_performance = (self.current_corner_speed + 
                                  (2.0 - self.current_brake_point) + 
                                  self.current_consistency) / 3.0
    
    def check_for_mistakes(self, track_type):
        """Stochastic mistake events"""
        if track_type in ["CORNER", "TIGHT_CORNER"]:
            # Lockup probability
            mistake_chance = self.skill_params['mistake_prob'] * (1.5 - self.current_consistency)
            if np.random.random() < mistake_chance:
                self.lockup_timer = LOCKUP_DURATION
                if DEBUG:
                    print(f"Car {self.id} locked up!")
            
            # Missed apex (independent event)
            if np.random.random() < mistake_chance * 0.7:
                self.missed_apex_timer = MISSED_APEX_DURATION
                if DEBUG:
                    print(f"Car {self.id} missed apex!")
    
    def update_tire_degradation(self):
        """Nonlinear tire degradation"""
        self.tire_distance += self.speed * dt
        # Nonlinear formula: deg = base * (distance ^ exponential)
        normalized_distance = self.tire_distance / 10000.0
        self.tire_deg = min(MAX_TIRE_DEG, 
                           TIRE_DEG_BASE_RATE * (normalized_distance ** TIRE_DEG_EXPONENTIAL))
    
    def forward_distance_to(self, other_agent):
        if other_agent is None:
            return np.inf
        diff = (other_agent.distance - self.distance) % total_length
        if diff > total_length / 2:
            diff = diff - total_length
        return diff
    
    def predict_opponent_position(self, opponent, time_ahead):
        if opponent is None:
            return None
        predicted_distance = opponent.distance + opponent.speed * time_ahead
        return predicted_distance
    
    def get_track_type_ahead(self, lookahead_time=1.0):
        future_distance = self.distance + self.speed * lookahead_time
        curvature = get_curvature(future_distance, lookahead=lookahead_dist)
        
        if curvature < STRAIGHT_CURVATURE_THRESHOLD:
            return "STRAIGHT"
        elif curvature < WIDE_CORNER_THRESHOLD:
            return "WIDE_CORNER"
        elif curvature < TIGHT_CORNER_THRESHOLD:
            return "CORNER"
        else:
            return "TIGHT_CORNER"
    
    def estimate_opponent_defend_probability(self, gap):
        if gap > DEFEND_GAP:
            return 0.0
        elif gap < OVERTAKE_GAP:
            return 0.9
        else:
            return 0.9 * (1.0 - (gap - OVERTAKE_GAP) / (DEFEND_GAP - OVERTAKE_GAP))
    
    def calculate_attack_payoff(self, gap, track_type, opponent_defend_prob, opponent_skill):
        if track_type == "TIGHT_CORNER":
            return -10.0
        
        position_gain = 50.0 if gap < OVERTAKE_GAP else 20.0
        skill_diff = self.current_corner_speed - opponent_skill
        skill_bonus = skill_diff * 25.0
        contact_risk = opponent_defend_prob * 30.0 if gap < 25.0 else 0.0
        track_bonus = 20.0 if track_type == "STRAIGHT" else 10.0 if track_type == "WIDE_CORNER" else 0.0
        slipstream_bonus = 15.0 if gap < SLIPSTREAM_GAP else 0.0
        
        # Stochastic noise on payoff
        payoff_noise = np.random.normal(0, PAYOFF_NOISE_SCALE * (1.0 - self.current_consistency))
        
        return position_gain + track_bonus + slipstream_bonus + skill_bonus - contact_risk + payoff_noise
    
    def calculate_wait_payoff(self, gap, track_type):
        slipstream_value = 10.0 if gap < SLIPSTREAM_GAP else 0.0
        future_value = 15.0 if track_type in ["CORNER", "TIGHT_CORNER"] else 5.0
        
        # Stochastic noise
        payoff_noise = np.random.normal(0, PAYOFF_NOISE_SCALE * 0.5 * (1.0 - self.current_consistency))
        
        return slipstream_value + future_value + payoff_noise
    
    def calculate_defend_payoff(self, gap_behind):
        if gap_behind > DEFEND_GAP:
            return 0.0
        defend_cost = 10.0
        position_hold = 30.0 if gap_behind < OVERTAKE_GAP else 15.0
        return position_hold - defend_cost
    
    def is_attack_feasible(self, gap, car_ahead):
        if car_ahead is None or gap > OVERTAKE_GAP * 1.5:
            return False
        if self.gap_closing_rate < MIN_CLOSING_RATE:
            return False
        return True
    
    def choose_attack_line(self, track_type):
        curvature = get_curvature(self.distance, lookahead=lookahead_dist * 0.5)
        if track_type == "STRAIGHT":
            return AttackType.OUTSIDE
        else:
            return AttackType.INSIDE
    
    def fsm_transition(self, car_ahead, car_behind):
        gap_ahead = self.forward_distance_to(car_ahead)
        gap_behind = -self.forward_distance_to(car_behind) if car_behind else np.inf
        
        track_type = self.get_track_type_ahead(lookahead_time=0.7)
        
        if car_ahead and len(self.speed_history) > 5:
            self.gap_closing_rate = self.speed - car_ahead.speed
        
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if self.defend_cooldown > 0:
            self.defend_cooldown -= 1
        if self.commit_timer > 0:
            self.commit_timer -= 1
        
        # Check for mistakes
        self.check_for_mistakes(track_type)
        
        if self.state == RaceState.COMMIT:
            if self.commit_timer <= 0:
                self.state = RaceState.CRUISE
                self.attack_cooldown = ATTACK_COOLDOWN
                self.attack_type = AttackType.NONE
            return self.state
        
        if gap_behind < DEFEND_GAP and car_behind:
            predicted_pos = self.predict_opponent_position(car_behind, PREDICTION_HORIZON)
            if predicted_pos and (predicted_pos - self.distance) % total_length < OVERTAKE_GAP:
                if self.defend_cooldown == 0:
                    self.state = RaceState.DEFEND
                    self.defend_cooldown = DEFEND_COOLDOWN
                    return self.state
        
        if car_ahead and gap_ahead < PRESSURE_GAP and self.attack_cooldown == 0:
            opponent_defend_prob = self.estimate_opponent_defend_probability(gap_ahead)
            
            attack_payoff = self.calculate_attack_payoff(gap_ahead, track_type, 
                                                        opponent_defend_prob, 
                                                        car_ahead.current_corner_speed)
            wait_payoff = self.calculate_wait_payoff(gap_ahead, track_type)
            
            if self.state == RaceState.CRUISE:
                if gap_ahead < PRESSURE_GAP:
                    self.state = RaceState.PRESSURE
            
            elif self.state == RaceState.PRESSURE:
                if gap_ahead < OVERTAKE_GAP and self.is_attack_feasible(gap_ahead, car_ahead):
                    if attack_payoff > wait_payoff and attack_payoff > 0:
                        self.state = RaceState.ATTACK
                        self.attack_type = self.choose_attack_line(track_type)
                    else:
                        self.state = RaceState.WAIT
                elif gap_ahead > PRESSURE_GAP * 1.2:
                    self.state = RaceState.CRUISE
            
            elif self.state == RaceState.ATTACK:
                self.state = RaceState.COMMIT
                self.commit_timer = COMMIT_DURATION
            
            elif self.state == RaceState.WAIT:
                if track_type == "STRAIGHT" and gap_ahead < OVERTAKE_GAP * 0.8:
                    self.state = RaceState.PRESSURE
                elif gap_ahead > PRESSURE_GAP:
                    self.state = RaceState.CRUISE
        else:
            if self.state != RaceState.DEFEND:
                self.state = RaceState.CRUISE
        
        return self.state
    
    def apply_strategy(self, car_ahead):
        speed_modifier = 1.0
        color = self.base_color
        
        curvature = get_curvature(self.distance, lookahead=lookahead_dist * 0.5)
        is_cornering = curvature > STRAIGHT_CURVATURE_THRESHOLD
        
        # Frame-by-frame control noise
        control_noise = np.random.normal(0, self.control_noise_sigma)
        
        if self.state == RaceState.CRUISE:
            if is_cornering:
                speed_modifier = self.current_corner_speed + control_noise
            else:
                speed_modifier = 1.0 + control_noise * 0.5
            color = self.base_color
        
        elif self.state == RaceState.PRESSURE:
            speed_modifier = 1.02 * (self.current_corner_speed if is_cornering else 1.0) + control_noise
            color = 'yellow'
        
        elif self.state == RaceState.ATTACK or self.state == RaceState.COMMIT:
            speed_modifier = 1.08 * (self.current_corner_speed if is_cornering else 1.0) + control_noise
            color = 'red'
        
        elif self.state == RaceState.WAIT:
            speed_modifier = 0.98 + control_noise * 0.5
            color = 'orange'
        
        elif self.state == RaceState.DEFEND:
            speed_modifier = 0.96 * (1.0 + (self.current_corner_speed - 1.0) * 0.5) + control_noise
            color = 'blue'
        
        # Apply mistake penalties
        if self.lockup_timer > 0:
            speed_modifier *= LOCKUP_SPEED_PENALTY
            color = 'purple'
            self.lockup_timer -= 1
        
        if self.missed_apex_timer > 0:
            speed_modifier *= MISSED_APEX_PENALTY
            color = 'darkviolet'
            self.missed_apex_timer -= 1
        
        # Slipstream with randomness
        if car_ahead:
            gap = self.forward_distance_to(car_ahead)
            if 0 < gap < SLIPSTREAM_GAP and self.state != RaceState.DEFEND:
                slipstream_efficiency = self.energy_management * np.random.uniform(0.95, 1.05)
                self.speed += SLIPSTREAM_BOOST * dt * slipstream_efficiency
        
        # Nonlinear tire degradation
        speed_modifier *= (1.0 - self.tire_deg)
        
        self.color = color
        return speed_modifier
    
    def update(self, car_ahead=None, car_behind=None):
        try:
            # Apply stochastic drift
            self.apply_stochastic_drift()
            
            # Update tire degradation
            self.update_tire_degradation()
            
            self.speed_history.append(self.speed)
            if len(self.speed_history) > 20:
                self.speed_history.pop(0)
            
            self.fsm_transition(car_ahead, car_behind)
            speed_modifier = self.apply_strategy(car_ahead)
            
            # Base speed with dynamic brake point
            curvature = get_curvature(self.distance, lookahead=lookahead_dist * self.current_brake_point)
            target_speed = turn_sharpness_to_target_speed(curvature) * speed_modifier
            
            speed_error = target_speed - self.speed
            accel_command = self.pid.update(speed_error)
            
            if accel_command >= 0:
                accel = min(accel_command, max_accel)
            else:
                accel = max(accel_command, -max_decel)
            
            self.speed = np.clip(self.speed + accel * dt, 0.0, max_speed)
            
            prev_distance = self.distance
            self.distance += self.speed * dt
            
            if (self.distance // total_length) > (prev_distance // total_length):
                self.lap_count += 1
                self.pid.reset()
            
        except Exception:
            print(f"Exception in agent {self.id} update:")
            traceback.print_exc()
            raise
    
    def get_position(self):
        base_pos = get_position(self.distance)
        heading = get_heading(self.distance, ahead=2.0)
        return base_pos, heading

# --- Initialize agents ---
NUM_AGENTS = 5
agents = []
colors = ['#FF6B35', '#4ECDC4', '#C77DFF', '#06FFA5', '#FFD23F']
skill_distribution = ['ELITE', 'EXPERT', 'SKILLED', 'AVERAGE', 'NOVICE']

for i in range(NUM_AGENTS):
    skill = skill_distribution[i % len(skill_distribution)]
    agent = RacingAgent(i, 0, colors[i], skill_level=skill)
    agent.speed = np.random.uniform(85, 115)
    agents.append(agent)

# --- Enhanced Visualization ---
fig, (ax_track, ax_stats) = plt.subplots(1, 2, figsize=(16, 7), 
                                          gridspec_kw={'width_ratios': [2, 1]})

# Track view
ax_track.plot(track_points_dense[:, 0], track_points_dense[:, 1], 
             'k-', linewidth=4, zorder=1, alpha=0.4)

# Add car patches with glow effects
car_patches = []
glow_patches = []
for agent in agents:
    pos, heading = agent.get_position()
    
    # Glow effect
    glow = Circle(pos, radius=15, facecolor=agent.color, alpha=0.2, zorder=2)
    ax_track.add_patch(glow)
    glow_patches.append(glow)
    
    # Car triangle
    car_patch = RegularPolygon(pos, numVertices=3, radius=12, orientation=heading - np.pi/2,
                               facecolor=agent.color, edgecolor='white', linewidth=2, zorder=5)
    ax_track.add_patch(car_patch)
    car_patches.append(car_patch)

ax_track.set_aspect('equal')
ax_track.set_xlim(100, 750)
ax_track.set_ylim(300, 650)
ax_track.set_title('Formula E Race - Stochastic Multi-Agent Simulation', 
                   fontsize=14, fontweight='bold', pad=15)
ax_track.axis('off')
ax_track.set_facecolor('#F0F0F0')

# Stats panel
ax_stats.axis('off')
ax_stats.set_xlim(0, 1)
ax_stats.set_ylim(0, 1)

stats_text = ax_stats.text(0.05, 0.95, "", transform=ax_stats.transAxes, 
                           fontsize=9, verticalalignment='top', family='monospace',
                           bbox=dict(facecolor='white', alpha=0.9, edgecolor='gray', 
                                    boxstyle='round,pad=1'))

def update(frame):
    try:
        # Sort agents by position
        agents_sorted = sorted(agents, key=lambda a: (a.lap_count * total_length + a.distance), reverse=True)
        
        # Update each agent
        for i, agent in enumerate(agents_sorted):
            car_ahead = agents_sorted[i - 1] if i > 0 else None
            car_behind = agents_sorted[i + 1] if i < len(agents_sorted) - 1 else None
            agent.update(car_ahead, car_behind)
        
        # Handle overtakes with stochastic success
        for i, agent in enumerate(agents_sorted[:-1]):
            car_behind = agents_sorted[i + 1]
            gap = car_behind.forward_distance_to(agent)
            
            if (car_behind.state == RaceState.COMMIT and 
                gap < 5.0 and gap > -5.0 and 
                car_behind.gap_closing_rate > 0):
                
                skill_advantage = car_behind.current_corner_speed - agent.current_corner_speed
                base_prob = 0.7
                
                track_type = car_behind.get_track_type_ahead(0.5)
                if track_type == "STRAIGHT":
                    track_modifier = 1.2
                elif track_type == "WIDE_CORNER":
                    track_modifier = 1.1
                elif track_type == "CORNER":
                    track_modifier = 1.0
                else:
                    track_modifier = 0.7
                
                overtake_prob = base_prob * (1.0 + skill_advantage) * track_modifier
                overtake_prob = np.clip(overtake_prob, 0.3, 0.95)
                
                if np.random.random() < overtake_prob:
                    car_behind.distance = agent.distance + 3.0
                    car_behind.state = RaceState.CRUISE
                    car_behind.commit_timer = 0
                    car_behind.attack_cooldown = ATTACK_COOLDOWN
                    agent.state = RaceState.CRUISE
                else:
                    car_behind.speed *= 0.9
                    agent.speed *= 0.95
                    car_behind.state = RaceState.CRUISE
                    car_behind.attack_cooldown = int(ATTACK_COOLDOWN * 1.5)
        
        # Update visualizations
        for i, agent in enumerate(agents):
            pos, heading = agent.get_position()
            car_patches[i].xy = pos
            car_patches[i].orientation = heading - np.pi/2
            car_patches[i].set_facecolor(agent.color)
            
            glow_patches[i].center = pos
            glow_patches[i].set_facecolor(agent.color)
        
        # Enhanced stats panel
        leaderboard = sorted(agents, key=lambda a: (a.lap_count * total_length + a.distance), reverse=True)
        
        stats_lines = ["=" * 45]
        stats_lines.append("      FORMULA E RACE LEADERBOARD")
        stats_lines.append("=" * 45)
        stats_lines.append("")
        
        for pos, agent in enumerate(leaderboard, 1):
            state_str = agent.state.value[:7]
            skill_str = agent.skill_level[:7]
            
            # Status indicators
            status = ""
            if agent.lockup_timer > 0:
                status = "🔒LOCK"
            elif agent.missed_apex_timer > 0:
                status = "💥MISS"
            else:
                perf = agent.recent_performance
                if perf > 1.05:
                    status = "🔥HOT"
                elif perf > 1.02:
                    status = "⚡GOOD"
                elif perf < 0.95:
                    status = "❄COLD"
                else:
                    status = "~OK"
            
            # Tire wear indicator
            tire_pct = int((1.0 - agent.tire_deg / MAX_TIRE_DEG) * 100)
            tire_bar = "█" * (tire_pct // 10) + "░" * (10 - tire_pct // 10)
            
            stats_lines.append(f"P{pos} │ CAR #{agent.id} │ {skill_str}")
            stats_lines.append(f"   │ Lap {agent.lap_count} │ {agent.speed:5.1f} px/s")
            stats_lines.append(f"   │ {state_str:7s} │ {status}")
            stats_lines.append(f"   │ Tire: {tire_bar} {tire_pct}%")
            stats_lines.append("   " + "─" * 39)
        
        stats_lines.append("")
        stats_lines.append("LEGEND:")
        stats_lines.append("🔥HOT  ⚡GOOD  ~OK  ❄COLD")
        stats_lines.append("🔒LOCK 💥MISS")
        stats_lines.append("")
        stats_lines.append("STATES:")
        stats_lines.append("🟡PRESSURE 🔴ATTACK 🔵DEFEND")
        stats_lines.append("🟠WAIT 🟢CRUISE")
        
        stats_text.set_text("\n".join(stats_lines))
        
        return car_patches + glow_patches + [stats_text]
    
    except Exception:
        print("Exception in animation update:")
        traceback.print_exc()
        raise

ani = animation.FuncAnimation(fig, update, frames=np.arange(0, 10000), 
                              interval=dt*1000, blit=True)
plt.tight_layout()
plt.show()