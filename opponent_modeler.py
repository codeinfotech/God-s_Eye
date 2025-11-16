import numpy as np
import scipy.stats  # <-- FIX 1: Added the required import

class OpponentModeler:
    def __init__(self):
        # Prior: uniform distribution over 3 opponent types
        self.beliefs = {
            'aggressive': 1/3,
            'balanced': 1/3,
            'conservative': 1/3
        }

        # Historical data: typical behaviors for each type
        self.profiles = {
            # FIX 2: Added 'overtake_probability' (a simple guess)
            'aggressive': {'avg_total_overtakes': 8, 'avg_energy_lap_pct': 2.5, 'overtake_probability': 0.7},
            'balanced': {'avg_total_overtakes': 4, 'avg_energy_lap_pct': 2.2, 'overtake_probability': 0.4},
            'conservative': {'avg_total_overtakes': 2, 'avg_energy_lap_pct': 2.0, 'overtake_probability': 0.1}
        }

    def update_belief(self, total_observed_overtakes, avg_observed_energy_per_lap):
        """Bayesian update after observing opponent behavior"""
        likelihoods = {}

        for opp_type, profile in self.profiles.items():

            # Likelihood: P(observations | opponent_type)
            # How likely are the overtakes we've seen, given this profile?
            overtake_likelihood = scipy.stats.poisson.pmf(
                total_observed_overtakes, 
                profile['avg_total_overtakes']
            )

            # How likely is the energy use we've seen, given this profile?
            energy_likelihood = scipy.stats.norm.pdf(
                avg_observed_energy_per_lap, 
                profile['avg_energy_lap_pct'], 
                0.1 # This is the standard deviation (how "noisy" we assume the data is)
            )

            # Total likelihood (assuming independence)
            likelihoods[opp_type] = overtake_likelihood * energy_likelihood

        # Bayes rule: P(type | obs) ∝ P(obs | type) * P(type)
        # 1. Multiply prior belief by likelihood
        for opp_type in self.beliefs:
            self.beliefs[opp_type] *= likelihoods[opp_type]

        # 2. Normalize (so all beliefs add up to 1.0)
        total = sum(self.beliefs.values())

        # Avoid division by zero if all likelihoods were 0
        if total == 0:
            # Reset to uniform probability if something went wrong
            for opp_type in self.beliefs:
                self.beliefs[opp_type] = 1/3
        else:
            for opp_type in self.beliefs:
                self.beliefs[opp_type] /= total

    def get_beliefs(self):
        """Returns the current belief dictionary."""
        return self.beliefs

    def predict_opponent_action(self):
        """Predict opponent's next move using belief distribution"""
        expected_action_prob = 0
        for opp_type, belief in self.beliefs.items():
            action_prob = self.profiles[opp_type]['overtake_probability']
            expected_action_prob += belief * action_prob

        # Returns the *probability* of an attack
        return expected_action_prob
