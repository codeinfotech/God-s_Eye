"""
Race Visualizer Module

Creates visualizations for race simulation: leaderboard, track map, energy levels, etc.

author: Extended from Formula E lap time simulator
date: 2024
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Optional
import os


class RaceVisualizer:
    """
    Visualizes race simulation results.
    
    Features:
    - Live leaderboard with gaps
    - Energy levels bar chart
    - Track map with car positions
    - Race events timeline
    - Attack mode status indicators
    - Position changes over time
    
    Example:
        visualizer = RaceVisualizer(track, num_cars=20)
        visualizer.plot_leaderboard(race_state, car_states)
        visualizer.plot_energy_levels(car_states)
        visualizer.save_all(output_dir="output/")
    """
    
    def __init__(self, track, num_cars: int, output_dir: str = "output"):
        """
        Initialize visualizer.
        
        Args:
            track: Track object
            num_cars: Number of cars
            output_dir: Output directory for plots
        """
        self.track = track
        self.num_cars = num_cars
        self.output_dir = output_dir
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Color scheme
        self.colors = plt.cm.tab20(np.linspace(0, 1, num_cars))
    
    def plot_leaderboard(self, race_state, car_states: Dict, save_path: Optional[str] = None):
        """
        Plot current leaderboard.
        
        Args:
            race_state: Current race state
            car_states: Dictionary of car states
            save_path: Optional path to save figure
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Sort by position
        sorted_cars = sorted(
            car_states.items(),
            key=lambda x: x[1].position
        )
        
        positions = []
        gaps = []
        car_ids = []
        
        for car_id, state in sorted_cars:
            if state.is_active:
                positions.append(state.position)
                gaps.append(state.gap_to_leader)
                car_ids.append(f"Car {car_id}")
        
        # Create bar chart
        y_pos = np.arange(len(positions))
        bars = ax.barh(y_pos, gaps, color=self.colors[:len(positions)])
        
        # Labels
        ax.set_yticks(y_pos)
        ax.set_yticklabels(car_ids)
        ax.set_xlabel('Gap to Leader (seconds)')
        ax.set_title(f'Leaderboard - Lap {race_state.current_lap} - {race_state.race_time/60:.1f} min')
        ax.invert_yaxis()
        
        # Add position numbers
        for i, (pos, gap) in enumerate(zip(positions, gaps)):
            ax.text(gap + 0.1, i, f"P{pos}", va='center')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150)
        else:
            plt.savefig(os.path.join(self.output_dir, "leaderboard.png"), dpi=150)
        plt.close()
    
    def plot_energy_levels(self, car_states: Dict, initial_energy: float,
                          save_path: Optional[str] = None):
        """
        Plot energy levels for all cars.
        
        Args:
            car_states: Dictionary of car states
            initial_energy: Initial energy in Joules
            save_path: Optional path to save figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        car_ids = []
        energy_percents = []
        
        for car_id in range(self.num_cars):
            if car_id in car_states and car_states[car_id].is_active:
                car_ids.append(f"Car {car_id}")
                energy_percent = (car_states[car_id].energy_remaining / initial_energy) * 100
                energy_percents.append(energy_percent)
        
        # Create bar chart
        y_pos = np.arange(len(car_ids))
        bars = ax.barh(y_pos, energy_percents, color=self.colors[:len(car_ids)])
        
        # Color code: red < 20%, yellow < 40%, green otherwise
        for i, energy in enumerate(energy_percents):
            if energy < 20:
                bars[i].set_color('red')
            elif energy < 40:
                bars[i].set_color('orange')
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(car_ids)
        ax.set_xlabel('Energy Remaining (%)')
        ax.set_title('Energy Levels')
        ax.set_xlim(0, 100)
        ax.axvline(x=20, color='r', linestyle='--', alpha=0.5, label='Critical (20%)')
        
        plt.legend()
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150)
        else:
            plt.savefig(os.path.join(self.output_dir, "energy_levels.png"), dpi=150)
        plt.close()
    
    def plot_track_map(self, car_states: Dict, race_state, save_path: Optional[str] = None):
        """
        Plot track map with car positions.
        
        Args:
            car_states: Dictionary of car states
            race_state: Current race state
            save_path: Optional path to save figure
        """
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plot track
        ax.plot(self.track.raceline[:, 0], self.track.raceline[:, 1], 'k-', linewidth=2, label='Track')
        
        # Plot car positions
        for car_id, state in car_states.items():
            if state.is_active:
                # Find track point closest to car position
                track_idx = int(state.track_distance / self.track.stepsize) % self.track.no_points
                car_pos = self.track.raceline[track_idx]
                
                # Plot car
                color = self.colors[car_id]
                ax.plot(car_pos[0], car_pos[1], 'o', color=color, markersize=10, 
                       label=f"Car {car_id} (P{state.position})")
                ax.text(car_pos[0] + 5, car_pos[1] + 5, f"{car_id}", fontsize=8)
        
        ax.set_aspect('equal')
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_title(f'Track Map - Lap {race_state.current_lap}')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150)
        else:
            plt.savefig(os.path.join(self.output_dir, "track_map.png"), dpi=150)
        plt.close()
    
    def plot_position_changes(self, position_history: Dict, save_path: Optional[str] = None):
        """
        Plot position changes over time.
        
        Args:
            position_history: Dict of {car_id: List[(time, position)]}
            save_path: Optional path to save figure
        """
        fig, ax = plt.subplots(figsize=(12, 8))
        
        for car_id in range(self.num_cars):
            if car_id in position_history and position_history[car_id]:
                times, positions = zip(*position_history[car_id])
                ax.plot(times, positions, color=self.colors[car_id], 
                       label=f"Car {car_id}", linewidth=2)
        
        ax.set_xlabel('Race Time (seconds)')
        ax.set_ylabel('Position')
        ax.set_title('Position Changes Over Time')
        ax.set_ylim(0.5, self.num_cars + 0.5)
        ax.invert_yaxis()  # Position 1 at top
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150)
        else:
            plt.savefig(os.path.join(self.output_dir, "position_changes.png"), dpi=150)
        plt.close()
    
    def save_all(self, race_state, car_states: Dict, position_history: Dict,
                initial_energy: float):
        """Save all visualizations."""
        self.plot_leaderboard(race_state, car_states)
        self.plot_energy_levels(car_states, initial_energy)
        self.plot_track_map(car_states, race_state)
        if position_history:
            self.plot_position_changes(position_history)
        print(f"All visualizations saved to {self.output_dir}/")

