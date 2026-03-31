"""
Advanced F1 Strategy Analysis Module
Contains improved degradation models, risk analysis, fuel weight modeling, and detailed metrics
"""

import numpy as np
from typing import Dict, List, Tuple
import math


class FuelModel:
    """
    F1 Fuel consumption and weight impact modeling.

    Realistic values based on 2024 F1 regulations:
    - Starting fuel: 105-110 kg
    - Fuel consumption: 2.0-3.0 kg/lap depending on fuel map
    - Weight impact on lap time: ~0.025s per kg
    - Weight impact on degradation: ~1% increase per 10kg
    """

    # Fuel maps and consumption rates (kg/lap)
    FUEL_MAPS = {
        'ECO': 2.0,          # Fuel saving mode
        'BALANCED': 2.5,     # Standard race mode
        'PUSH': 3.0,         # Aggressive mode
        'QUALIFY': 3.2,      # Qualifying mode (max consumption)
    }

    # Weight-to-lap-time conversion (seconds per kg)
    WEIGHT_LAP_TIME_PENALTY = 0.025

    # Weight-to-degradation conversion (multiplier per 10kg)
    WEIGHT_DEGRADATION_MULTIPLIER = 0.01

    def __init__(self, max_fuel: float = 110.0, fuel_map: str = 'BALANCED'):
        """
        Initialize fuel model.

        Args:
            max_fuel: Maximum fuel capacity (kg), typically 110 for F1
            fuel_map: Default fuel consumption map (ECO, BALANCED, PUSH, QUALIFY)
        """
        self.max_fuel = max_fuel
        self.fuel_map = fuel_map
        self.consumption_rate = self.FUEL_MAPS.get(fuel_map, 2.5)

    def get_fuel_weight_at_lap(self, current_lap: int, total_laps: int,
                               num_refueling_stops: int = 0) -> float:
        """
        Calculate remaining fuel weight at a given lap.

        Args:
            current_lap: Current lap number (1-indexed)
            total_laps: Total race laps
            num_refueling_stops: Number of times fuel is added

        Returns:
            Remaining fuel weight in kg
        """
        # Assume refueling happens evenly throughout race
        fuel_per_stint = self.max_fuel / (num_refueling_stops + 1)

        # Current stint based on number of stops
        stint_number = min(int((current_lap - 1) / (total_laps / (num_refueling_stops + 1))), num_refueling_stops)
        laps_since_refuel = current_lap - (stint_number * (total_laps / (num_refueling_stops + 1)))

        fuel_consumed = laps_since_refuel * self.consumption_rate
        current_fuel = fuel_per_stint - fuel_consumed

        return max(0, current_fuel)

    def get_lap_time_penalty(self, fuel_weight: float) -> float:
        """
        Calculate lap time penalty from fuel weight.

        Args:
            fuel_weight: Fuel weight in kg

        Returns:
            Lap time penalty in seconds
        """
        return fuel_weight * self.WEIGHT_LAP_TIME_PENALTY

    def get_degradation_multiplier(self, fuel_weight: float) -> float:
        """
        Calculate tyre degradation multiplier from fuel weight.

        Higher weight = faster tyre wear

        Args:
            fuel_weight: Fuel weight in kg

        Returns:
            Degradation multiplier (1.0 = no change)
        """
        # Baseline at 50kg, increase by 1% per 10kg
        baseline_fuel = 50.0
        fuel_delta = fuel_weight - baseline_fuel
        multiplier = 1.0 + (fuel_delta / 100.0) * self.WEIGHT_DEGRADATION_MULTIPLIER
        return max(0.95, multiplier)  # Floor at 5% reduction minimum

    def optimal_fuel_map_for_stint(self, stint_laps: int, total_race_laps: int,
                                   is_final_stint: bool = False) -> str:
        """
        Recommend optimal fuel map for a stint.

        Args:
            stint_laps: Number of laps in this stint
            total_race_laps: Total laps in race
            is_final_stint: Whether this is the final stint

        Returns:
            Recommended fuel map
        """
        remaining_laps = total_race_laps - stint_laps

        if is_final_stint:
            return 'PUSH'  # Push hard on final stint

        if remaining_laps > (stint_laps * 2):
            return 'ECO'  # Early race, save fuel
        elif remaining_laps > stint_laps:
            return 'BALANCED'  # Mid-race balance
        else:
            return 'PUSH'  # Late race, push


class AdvancedStrategyAnalyzer:
    """
    Advanced analysis engine for F1 strategy simulation
    Features:
    - Non-linear tyre degradation modeling
    - Lap-by-lap predictions
    - Safety margins and reliability scores
    - Risk assessment
    """

    def __init__(self, driver_data: Dict, track_data: Dict, compound_characteristics: Dict = None,
                 fuel_model: FuelModel = None, include_fuel_weight: bool = True):
        self.driver_data = driver_data
        self.track_data = track_data
        self.include_fuel_weight = include_fuel_weight

        # Initialize fuel model
        self.fuel_model = fuel_model or FuelModel()

        # Default compound characteristics (realistic F1 values)
        self.compound_chars = compound_characteristics or {
            'SOFT': {'max_life': 40, 'cliff_point': 0.75, 'cliff_severity': 0.8},
            'MEDIUM': {'max_life': 60, 'cliff_point': 0.80, 'cliff_severity': 0.5},
            'HARD': {'max_life': 90, 'cliff_point': 0.85, 'cliff_severity': 0.3},
        }

    def calculate_lap_time_with_degradation(
        self,
        base_lap_time: float,
        compound: str,
        lap_in_stint: int,
        total_stint_laps: int,
        degradation_rate: float,
        driver_delta: float,
        ambient_temp: float = 25.0,
        fuel_weight: float = 50.0,
        current_lap: int = 0,
        total_race_laps: int = 50
    ) -> float:
        """
        Calculate lap time with advanced non-linear degradation model.

        Features:
        - Non-linear degradation (accelerates as tyre ages)
        - Temperature effects on performance
        - Cliff point (sudden loss of grip)
        - Compound-specific characteristics
        - Fuel weight penalty
        """

        # Base lap time with driver adjustment
        adjusted_base = base_lap_time + driver_delta

        # Temperature effect (±0.5s per 10°C variance from 25°C)
        temp_delta = (ambient_temp - 25.0) * 0.05

        # Fuel weight effect
        fuel_penalty = 0.0
        if self.include_fuel_weight and fuel_weight > 0:
            fuel_penalty = self.fuel_model.get_lap_time_penalty(fuel_weight)

        # Tyre life ratio (0 = fresh, 1 = end of life)
        life_ratio = (lap_in_stint - 1) / max(total_stint_laps, 1)

        # Get compound characteristics
        chars = self.compound_chars.get(compound, {})
        cliff_point = chars.get('cliff_point', 0.8)
        cliff_severity = chars.get('cliff_severity', 0.5)

        # Adjust degradation rate based on fuel weight
        adjusted_degradation_rate = degradation_rate
        if self.include_fuel_weight and fuel_weight > 0:
            weight_multiplier = self.fuel_model.get_degradation_multiplier(fuel_weight)
            adjusted_degradation_rate = degradation_rate * weight_multiplier

        # Non-linear degradation model
        if life_ratio < cliff_point:
            # Linear degradation phase
            degradation = adjusted_degradation_rate * (lap_in_stint - 1)
        else:
            # Cliff phase - rapid degradation
            linear_portion = adjusted_degradation_rate * (cliff_point * total_stint_laps)
            cliff_portion = (life_ratio - cliff_point) * adjusted_degradation_rate * total_stint_laps * cliff_severity
            degradation = linear_portion + cliff_portion

        lap_time = adjusted_base + temp_delta + fuel_penalty + degradation

        return lap_time

    def simulate_strategy_advanced(
        self,
        strategy: List[str],
        total_laps: int,
        degradation_rates: Dict[str, float],
        base_times: Dict[str, float],
        driver_delta: float,
        pit_stop_loss: float,
        ambient_temp: float = 25.0,
        starting_fuel: float = 110.0
    ) -> Dict:
        """
        Advanced strategy simulation with detailed metrics including fuel weight.

        Returns:
        {
            'total_time': float,
            'pit_laps': List[int],
            'lap_times': List[float],
            'fuel_data': {
                'fuel_per_lap': List[float],
                'fuel_at_pits': List[float]
            },
            'metrics': {
                'avg_lap_time': float,
                'fastest_lap': float,
                'slowest_lap': float,
                'tyre_life_stress': float (0-1),
                'consistency_score': float (0-100),
                'pit_timing_efficiency': float (0-100),
                'avg_fuel_weight': float,
                'fuel_management_score': float (0-100)
            }
        }
        """
        total_race_time = (len(strategy) - 1) * pit_stop_loss
        stint_lengths = [total_laps // len(strategy)] * len(strategy)

        for i in range(total_laps % len(strategy)):
            stint_lengths[i] += 1

        pit_laps = []
        lap_times = []
        fuel_weights = []
        fuel_at_pits = []
        laps_completed = 0

        for stint_idx, compound in enumerate(strategy):
            stint_laps = stint_lengths[stint_idx]
            base_lap_time = base_times.get(compound, 120)
            degradation_rate = degradation_rates.get(compound, 0.1)

            for lap_in_stint in range(1, stint_laps + 1):
                current_lap = laps_completed + lap_in_stint

                # Calculate fuel weight for this lap
                num_pits = len(strategy) - 1
                fuel_weight = self.fuel_model.get_fuel_weight_at_lap(
                    current_lap, total_laps, num_pits
                ) if self.include_fuel_weight else 50.0

                fuel_weights.append(fuel_weight)

                lap_time = self.calculate_lap_time_with_degradation(
                    base_lap_time=base_lap_time,
                    compound=compound,
                    lap_in_stint=lap_in_stint,
                    total_stint_laps=stint_laps,
                    degradation_rate=degradation_rate,
                    driver_delta=driver_delta,
                    ambient_temp=ambient_temp,
                    fuel_weight=fuel_weight,
                    current_lap=current_lap,
                    total_race_laps=total_laps
                )
                lap_times.append(lap_time)
                total_race_time += lap_time

            laps_completed += stint_laps
            if stint_idx < len(strategy) - 1:
                pit_laps.append(laps_completed)
                # Record fuel weight at pit stop
                fuel_at_pits.append(fuel_weights[-1] if fuel_weights else 0)

        # Calculate metrics
        metrics = self._calculate_metrics(lap_times, strategy, stint_lengths, fuel_weights)

        return {
            'total_time': total_race_time,
            'pit_laps': pit_laps,
            'lap_times': lap_times,
            'fuel_data': {
                'fuel_per_lap': fuel_weights,
                'fuel_at_pits': fuel_at_pits
            },
            'metrics': metrics
        }

    def _calculate_metrics(self, lap_times: List[float], strategy: List[str],
                          stint_lengths: List[int], fuel_weights: List[float] = None) -> Dict:
        """Calculate detailed performance metrics"""
        lap_times_array = np.array(lap_times)

        metrics = {
            'avg_lap_time': float(np.mean(lap_times_array)),
            'fastest_lap': float(np.min(lap_times_array)),
            'slowest_lap': float(np.max(lap_times_array)),
            'lap_time_std': float(np.std(lap_times_array)),
            'consistency_score': self._calculate_consistency_score(lap_times_array),
            'tyre_life_stress': self._calculate_tyre_stress(strategy, stint_lengths),
            'pit_timing_efficiency': self._calculate_pit_efficiency(lap_times, stint_lengths)
        }

        # Add fuel metrics if available
        if fuel_weights and self.include_fuel_weight:
            fuel_array = np.array(fuel_weights)
            metrics['avg_fuel_weight'] = float(np.mean(fuel_array))
            metrics['fuel_management_score'] = self._calculate_fuel_efficiency(fuel_weights, stint_lengths)

        return metrics

    def _calculate_consistency_score(self, lap_times: np.ndarray) -> float:
        """
        Calculate consistency score (0-100).
        Higher is better (less variance).
        """
        if len(lap_times) == 0:
            return 0.0

        cv = np.std(lap_times) / np.mean(lap_times)
        # Convert CV to 0-100 score (lower CV = higher score)
        consistency = max(0, 100 - (cv * 150))
        return float(consistency)

    def _calculate_tyre_stress(self, strategy: List[str], stint_lengths: List[int]) -> float:
        """
        Calculate overall tyre life stress (0-1).
        Higher indicates tyres pushed closer to limits.
        """
        stress = 0.0
        for compound, stint_length in zip(strategy, stint_lengths):
            chars = self.compound_chars.get(compound, {})
            max_life = chars.get('max_life', 90)
            stress += (stint_length / max_life) / len(strategy)

        return float(min(1.0, stress))

    def _calculate_pit_efficiency(self, lap_times: List[float], stint_lengths: List[int]) -> float:
        """
        Calculate pit timing efficiency (0-100).
        Based on whether tyres are pitted before cliff point.
        """
        if not stint_lengths:
            return 50.0

        lap_times_array = np.array(lap_times)

        # Analyze each stint for cliff point efficiency
        efficiency_scores = []
        lap_idx = 0

        for stint_length in stint_lengths:
            stint_times = lap_times_array[lap_idx:lap_idx + stint_length]

            if len(stint_times) > 1:
                # Calculate degradation acceleration
                time_deltas = np.diff(stint_times)
                avg_degradation = np.mean(time_deltas)

                # Check if we hit the cliff (sudden jump in lap time)
                cliff_detected = False
                for delta in time_deltas[-5:]:  # Last 5 laps
                    if delta > avg_degradation * 1.5:  # 50% worse degradation
                        cliff_detected = True
                        break

                # Score: higher if we pit before cliff
                score = 100.0 if not cliff_detected else 60.0
                efficiency_scores.append(score)

            lap_idx += stint_length

        return float(np.mean(efficiency_scores)) if efficiency_scores else 50.0

    def _calculate_fuel_efficiency(self, fuel_weights: List[float], stint_lengths: List[int]) -> float:
        """
        Calculate fuel management efficiency (0-100).
        Based on optimal fuel distribution and pit timing.

        Score higher if:
        - Fuel weight decreases gradually (not sharp drops at stops)
        - Fuel managed within safety margins
        - Minimal excess fuel at finish
        """
        if not fuel_weights or not stint_lengths:
            return 50.0

        fuel_array = np.array(fuel_weights)

        # Check fuel at pit stops (ideally low but safe)
        pit_indices = np.cumsum(stint_lengths)[:-1]
        fuel_at_stops = fuel_array[pit_indices - 1] if len(pit_indices) > 0 else []

        # Ideal pit fuel: low but not empty (5-15kg)
        min_safe_fuel = 5.0
        max_ideal_fuel = 15.0

        efficiency_scores = []
        for pit_fuel in fuel_at_stops:
            if pit_fuel < min_safe_fuel:
                efficiency_scores.append(50.0)  # Risky - too low
            elif min_safe_fuel <= pit_fuel <= max_ideal_fuel:
                efficiency_scores.append(100.0)  # Perfect
            else:
                efficiency_scores.append(70.0)  # Suboptimal - too much fuel

        # Check final fuel (should be close to empty, 0-5kg)
        final_fuel = fuel_array[-1]
        if 0 <= final_fuel <= 5:
            efficiency_scores.append(100.0)
        elif final_fuel <= 10:
            efficiency_scores.append(80.0)
        else:
            efficiency_scores.append(50.0)  # Wasted fuel capacity

        return float(np.mean(efficiency_scores)) if efficiency_scores else 50.0

    def calculate_strategy_reliability(
        self,
        strategy: List[str],
        stint_lengths: List[int],
        risk_factors: Dict[str, float] = None
    ) -> Dict:
        """
        Calculate reliability and risk score for a strategy.

        Risk factors:
        - accident_probability: 0-1 (chance per lap)
        - weather_change_probability: 0-1
        - pit_error_probability: 0-1
        """

        if risk_factors is None:
            risk_factors = {
                'accident_probability': 0.002,
                'weather_change_probability': 0.01,
                'pit_error_probability': 0.01
            }

        # Calculate success probability
        total_laps = sum(stint_lengths)
        accident_survival = (1 - risk_factors['accident_probability']) ** total_laps
        weather_survival = (1 - risk_factors['weather_change_probability']) ** total_laps
        pit_success = (1 - risk_factors['pit_error_probability']) ** (len(strategy) - 1)

        overall_reliability = accident_survival * weather_survival * pit_success

        # Calculate vulnerability to specific risks
        vulnerability = {
            'high_accident_risk': any(sl > 50 for sl in stint_lengths),  # Long stints
            'high_weather_sensitivity': len(strategy) > 2,  # Many stints = more weather changes
            'high_pit_complexity': len(strategy) > 2
        }

        return {
            'reliability_score': float(overall_reliability * 100),
            'accident_survival_prob': float(accident_survival * 100),
            'weather_survival_prob': float(weather_survival * 100),
            'pit_success_prob': float(pit_success * 100),
            'vulnerability_assessment': vulnerability
        }

    def perform_sensitivity_analysis(
        self,
        strategy: List[str],
        total_laps: int,
        degradation_rates: Dict[str, float],
        base_times: Dict[str, float],
        driver_delta: float,
        pit_stop_loss: float,
        parameter: str = 'pit_loss',
        variations: List[float] = None
    ) -> Dict[str, List[float]]:
        """
        Perform sensitivity analysis on key parameters.

        Parameters:
        - pit_loss: vary pit stop time
        - degradation: vary degradation rates
        - ambient_temp: vary track temperature

        Returns:
        {
            'variations': [param values],
            'times': [corresponding total times],
            'deltas': [time differences from baseline]
        }
        """

        if variations is None:
            variations = [-10, -5, 0, 5, 10]  # ±10%

        baseline_result = self.simulate_strategy_advanced(
            strategy, total_laps, degradation_rates, base_times, driver_delta, pit_stop_loss
        )
        baseline_time = baseline_result['total_time']

        results = {
            'variations': [],
            'times': [],
            'deltas': []
        }

        for var in variations:
            if parameter == 'pit_loss':
                adjusted_pit_loss = pit_stop_loss * (1 + var / 100)
                result = self.simulate_strategy_advanced(
                    strategy, total_laps, degradation_rates, base_times, driver_delta, adjusted_pit_loss
                )
            elif parameter == 'degradation':
                adjusted_deg = {k: v * (1 + var / 100) for k, v in degradation_rates.items()}
                result = self.simulate_strategy_advanced(
                    strategy, total_laps, adjusted_deg, base_times, driver_delta, pit_stop_loss
                )
            elif parameter == 'ambient_temp':
                adjusted_temp = 25.0 + (var / 10)
                result = self.simulate_strategy_advanced(
                    strategy, total_laps, degradation_rates, base_times, driver_delta, pit_stop_loss, adjusted_temp
                )
            else:
                result = baseline_result

            results['variations'].append(var)
            results['times'].append(result['total_time'])
            results['deltas'].append(result['total_time'] - baseline_time)

        return results

    def compare_strategies(
        self,
        strategies: List[List[str]],
        total_laps: int,
        degradation_rates: Dict[str, float],
        base_times: Dict[str, float],
        driver_delta: float,
        pit_stop_loss: float
    ) -> List[Dict]:
        """
        Comprehensive comparison of multiple strategies.
        """

        results = []

        for strategy in strategies:
            sim_result = self.simulate_strategy_advanced(
                strategy, total_laps, degradation_rates, base_times, driver_delta, pit_stop_loss
            )

            reliability = self.calculate_strategy_reliability(
                strategy,
                [total_laps // len(strategy)] * len(strategy)
            )

            results.append({
                'strategy': strategy,
                'total_time': sim_result['total_time'],
                'metrics': sim_result['metrics'],
                'reliability': reliability,
                'lap_times': sim_result['lap_times']
            })

        # Sort by total time
        results.sort(key=lambda x: x['total_time'])

        return results
