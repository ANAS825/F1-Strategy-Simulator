"""
Advanced F1 Strategy Analysis Module
Contains improved degradation models, risk analysis, fuel weight modeling, and detailed metrics
"""

import numpy as np
from typing import Dict, List, Tuple
import math
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


# ============================================================================
# NEW MODELS: Enhanced degradation, Fuel curves, Driver fatigue, Bayesian
# ============================================================================

class EnhancedDegradationModel:
    """
    Advanced tire degradation modeling with weather and temperature sensitivity.
    Features:
    - Temperature-dependent grip loss
    - Dynamic cliff points based on conditions
    - Surface abrasiveness modeling
    """

    def __init__(self, track_roughness: float = 1.0, baseline_temp: float = 25.0):
        """
        Args:
            track_roughness: Surface abrasiveness multiplier (0.8-1.2 typical)
            baseline_temp: Reference temperature for degradation model
        """
        self.track_roughness = track_roughness
        self.baseline_temp = baseline_temp

    def get_temperature_degradation_multiplier(self, ambient_temp: float,
                                              tire_temp: float) -> float:
        """
        Calculate degradation multiplier based on temperature conditions.

        Cold tires degrade slower (less grip, but more durable)
        Hot tires degrade faster (more grip initially, but cliff steeper)
        """
        # Tire temp effect:  optimum ~80°C, deviations increase degradation
        optimal_tire_temp = 80.0
        tire_temp_delta = abs(tire_temp - optimal_tire_temp)
        tire_multiplier = 1.0 + (tire_temp_delta / 100.0) * 0.15  # ±15% at extreme temps

        return max(0.7, min(1.5, tire_multiplier))  # Clamp to 0.7-1.5

    def get_dynamic_cliff_point(self, compound: str, conditions_severity: float = 1.0) -> float:
        """
        Dynamic cliff point based on track/weather conditions.
        Harsher conditions = earlier cliff point

        Args:
            compound: 'SOFT', 'MEDIUM', or 'HARD'
            conditions_severity: 1.0 = normal, 1.5 = harsh (hot/abrasive), 0.7 = favorable
        """
        base_cliff_points = {
            'SOFT': 0.75,
            'MEDIUM': 0.80,
            'HARD': 0.85
        }
        base = base_cliff_points.get(compound, 0.80)
        # Harsh conditions push cliff earlier
        adjusted_cliff = base - (conditions_severity - 1.0) * 0.08
        return max(0.65, min(0.90, adjusted_cliff))

    def apply_weather_degradation_adjustment(self, base_degradation: float,
                                            weather: str = 'DRY') -> float:
        """
        Adjust degradation based on weather condition.

        Args:
            base_degradation: Original degradation rate (s/lap)
            weather: 'DRY', 'HUMID', 'HOT_DRY', 'COOL_DRY', 'LIGHT_RAIN'
        """
        weather_multipliers = {
            'DRY': 1.0,
            'HUMID': 1.1,           # Increased degradation
            'HOT_DRY': 1.25,        # High temps accelerate wear
            'COOL_DRY': 0.85,       # Cooler temps slow degradation
            'LIGHT_RAIN': 0.7,      # Wets provide protection
        }
        multiplier = weather_multipliers.get(weather, 1.0)
        return base_degradation * multiplier


class DriverFatigueModel:
    """
    Models driver fatigue and concentration loss over multiple stints.
    Simulates:
    - Physical fatigue (heavier steering, reduced braking precision)
    - Mental fatigue (concentration lapses)
    - Recovery during pit stops
    """

    def __init__(self, driver_stamina: float = 1.0):
        """
        Args:
            driver_stamina: Fitness/experience multiplier (1.0 = average, 1.5 = elite)
        """
        self.driver_stamina = driver_stamina
        # Fatigue accumulation per lap (seconds)
        self.fatigue_rate_per_lap = 0.002 / driver_stamina  # Elite drivers: 0.0013s/lap fatigue
        self.max_fatigue = 3.0  # Maximum fatigue penalty in seconds

    def calculate_fatigue_penalty(self, laps_completed: int, stints_completed: int) -> float:
        """
        Calculate accumulated fatigue penalty.

        Args:
            laps_completed: Total laps in race so far
            stints_completed: Number of pit stops completed

        Returns:
            Fatigue penalty in seconds
        """
        # Fatigue accumulates with laps completed
        base_fatigue = self.fatigue_rate_per_lap * laps_completed

        # Each pit stop provides 30-50% recovery
        recovery_per_stop = base_fatigue * 0.4 * stints_completed

        # Net fatigue (with recovery from stops)
        fatigue_penalty = max(0, base_fatigue - recovery_per_stop)

        # Cap at maximum
        return min(self.max_fatigue, fatigue_penalty)


class BayesianUncertaintyModel:
    """
    Bayesian approach to uncertainty in model parameters.
    Tracks parameter distributions learned from historical data.
    """

    def __init__(self):
        """Initialize with standard F1 parameter distributions"""
        # Mean and std deviations for key parameters
        self.param_distributions = {
            'pit_stop_loss': {'mean': 22.5, 'std': 1.2},      # seconds
            'degradation_variance': {'mean': 0.01, 'std': 0.003},  # s/lap
            'driver_delta_variance': {'mean': 0.2, 'std': 0.1},    # seconds
            'fuel_consumption_error': {'mean': 0.05, 'std': 0.02}, # kg/lap
        }

    def get_parameter_with_uncertainty(self, param_name: str,
                                      samples: int = 100) -> Tuple[float, float]:
        """
        Get parameter value with confidence interval via sampling.

        Args:
            param_name: Name of parameter to sample
            samples: Number of Monte Carlo samples

        Returns:
            (mean_value, std_dev)
        """
        if param_name not in self.param_distributions:
            return (1.0, 0.1)

        dist = self.param_distributions[param_name]
        samples_array = np.random.normal(dist['mean'], dist['std'], samples)
        return (float(np.mean(samples_array)), float(np.std(samples_array)))

    def update_from_telemetry(self, param_name: str, observed_value: float):
        """
        Update belief about parameter based on observed race data.
        """
        if param_name not in self.param_distributions:
            return

        dist = self.param_distributions[param_name]
        old_mean = dist['mean']
        old_std = dist['std']

        # Bayesian update (simplified Kalman-like update)
        alpha = 0.3  # Learning rate
        new_mean = old_mean * (1 - alpha) + observed_value * alpha
        new_std = old_std * 0.95  # Slight confidence increase

        self.param_distributions[param_name] = {'mean': new_mean, 'std': new_std}


class SafeCarModel:
    """Models safety car deployment and restart effects on strategy."""

    def __init__(self):
        self.sc_bunching_effect = 1.2  # Gap compression multiplier
        self.green_flag_lap_penalty = 0.8  # Restart lap slower

    def apply_sc_scenario(self, lap_times: List[float], sc_lap: int,
                         sc_duration_laps: int) -> List[float]:
        """
        Apply SC effects to lap times.
        """
        modified_laps = lap_times.copy()

        # Every car bunches up during SC
        if sc_lap < len(modified_laps):
            for i in range(sc_lap, min(sc_lap + sc_duration_laps, len(modified_laps))):
                modified_laps[i] *= 0.95  # Slower during SC (no racing)

            # Green flag restart lap is typically faster (DRS opportunity)
            restart_lap = sc_lap + sc_duration_laps
            if restart_lap < len(modified_laps):
                modified_laps[restart_lap] *= self.green_flag_lap_penalty

        return modified_laps


class GridPositionModel:
    """Models advantages/disadvantages of grid position in first stint."""

    def __init__(self):
        self.drs_tow_advantage = 0.6  # seconds saved from tow (leader penalty)
        self.traffic_penalty = 0.3   # seconds lost from traffic
        self.fresh_air_premium = 0.2 # benefit of being at front

    def get_first_stint_lap_adjustment(self, grid_position: int, field_size: int) -> float:
        """
        Calculate lap time adjustment for first stint based on grid position.

        Args:
            grid_position: Starting position (1 = pole, field_size = last)
            field_size: Total number of drivers

        Returns:
            Lap time adjustment in seconds
        """
        if grid_position <= 1:
            return 0.0  # Pole position: no adjustment

        if grid_position <= 5:
            # Top 5: can benefit from DRS tow
            return -self.drs_tow_advantage * (6 - grid_position) / 5
        else:
            # Back of field: suffers from traffic
            traffic_severity = (grid_position - 5) / (field_size - 5)
            return self.traffic_penalty * traffic_severity


class PitOptimizer:
    """Calculates optimal pit window timing based on tire, fuel, and track position."""

    def calculate_optimal_pit_window(self, current_lap: int, total_laps: int,
                                    tire_degradation_rate: float,
                                    tire_cliff_lap: int,
                                    fuel_required_to_finish: float) -> int:
        """
        Calculate recommended pit lap considering all constraints.

        Args:
            current_lap: Current lap in previous stint
            total_laps: Total race laps
            tire_degradation_rate: s/lap degradation
            tire_cliff_lap: Estimated lap when cliff occurs
            fuel_required_to_finish: Fuel needed for remaining stint

        Returns:
            Recommended pit lap (0 if no pit needed)
        """
        # Pit before cliff point (with 2-lap safety margin)
        pre_cliff_pit = tire_cliff_lap - 2

        # Fuel constraint: need enough to reach finish with margin
        remaining_laps = total_laps - current_lap
        pit_window_start = current_lap + (remaining_laps - 10)  # Latest pit + 10 laps buffer

        # Optimal pit is earliest of the two constraints
        optimal_pit = max(current_lap + 10, min(pre_cliff_pit, pit_window_start))

        return int(optimal_pit)


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

    def get_fuel_consumption_curve(self, lap_in_stint: int, stint_length: int,
                                  fuel_map: str = None) -> float:
        """
        Get lap-dependent fuel consumption (realistic curve, not linear).
        Models: cold start extra fuel, peak consumption, then slight decrease.

        Args:
            lap_in_stint: Lap number within current stint (1-indexed)
            stint_length: Total laps in this stint
            fuel_map: Optional override fuel map

        Returns:
            Fuel consumed on this lap (kg)
        """
        map_name = fuel_map or self.fuel_map
        base_rate = self.FUEL_MAPS.get(map_name, 2.5)

        # Normalize lap position (0 = start, 1 = end)
        lap_fraction = (lap_in_stint - 1) / max(stint_length, 1)

        # Realistic consumption curve:
        # Laps 1-3: +20% (cold tires, warming up)
        # Laps 4-N-3: normal consumption
        # Laps N-2 to N: -5% (tires worn, less grip, coast to fuel line)
        if lap_fraction < 0.1:  # First ~10% of stint
            consumption = base_rate * 1.2
        elif lap_fraction > 0.85:  # Last ~15% of stint
            consumption = base_rate * 0.95
        else:
            consumption = base_rate

        return consumption

    def get_fuel_weight_at_lap(self, current_lap: int, total_laps: int,
                               num_refueling_stops: int = 0) -> float:
        """
        Calculate remaining fuel weight at a given lap using consumption curves.

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
        laps_since_refuel = int(current_lap - (stint_number * (total_laps / (num_refueling_stops + 1))))
        stint_length = int(total_laps / (num_refueling_stops + 1)) + 1

        # Calculate consumption using curve for each lap
        fuel_consumed = 0.0
        for lap_num in range(1, laps_since_refuel + 1):
            fuel_consumed += self.get_fuel_consumption_curve(lap_num, stint_length)

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
    - Non-linear tyre degradation modeling with weather sensitivity
    - Enhanced fuel consumption curves
    - Driver fatigue modeling
    - Bayesian uncertainty handling
    - Safety car scenarios
    - Grid position advantages
    - Monte Carlo probabilistic analysis
    - Lap-by-lap predictions
    - Safety margins and reliability scores
    - Risk assessment
    """

    def __init__(self, driver_data: Dict, track_data: Dict, compound_characteristics: Dict = None,
                 fuel_model: FuelModel = None, include_fuel_weight: bool = True,
                 degradation_model: EnhancedDegradationModel = None,
                 fatigue_model: DriverFatigueModel = None,
                 uncertainty_model: BayesianUncertaintyModel = None,
                 sc_model: SafeCarModel = None,
                 grid_model: GridPositionModel = None):
        self.driver_data = driver_data
        self.track_data = track_data
        self.include_fuel_weight = include_fuel_weight

        # Initialize fuel model with consumption curves
        self.fuel_model = fuel_model or FuelModel()

        # Initialize new enhanced models
        self.degradation_model = degradation_model or EnhancedDegradationModel()
        self.fatigue_model = fatigue_model or DriverFatigueModel()
        self.uncertainty_model = uncertainty_model or BayesianUncertaintyModel()
        self.sc_model = sc_model or SafeCarModel()
        self.grid_model = grid_model or GridPositionModel()
        self.pit_optimizer = PitOptimizer()

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
        total_race_laps: int = 50,
        tire_temp: float = 80.0,
        stints_completed: int = 0,
        weather: str = 'DRY',
        track_roughness: float = 1.0,
        grid_position: int = 0,
        sc_laps: List[Tuple[int, int]] = None
    ) -> float:
        """
        Calculate lap time with comprehensive advanced degradation model.

        Features:
        - Non-linear degradation with weather/temperature sensitivity
        - Enhanced tire cliff points
        - Driver fatigue accumulation
        - Fuel weight penalty (with consumption curves)
        - Safety car effects
        - Grid position advantages
        - Bayesian uncertainty margins
        """

        # Base lap time with driver adjustment
        adjusted_base = base_lap_time + driver_delta

        # (1) Temperature effect (±0.5s per 10°C variance from 25°C)
        temp_delta = (ambient_temp - 25.0) * 0.05

        # (2) Fuel weight effect (using FuelModel)
        fuel_penalty = 0.0
        if self.include_fuel_weight and fuel_weight > 0:
            fuel_penalty = self.fuel_model.get_lap_time_penalty(fuel_weight)

        # (3) Driver fatigue penalty
        fatigue_penalty = self.fatigue_model.calculate_fatigue_penalty(current_lap, stints_completed)

        # (4) Grid position advantage (first stint only)
        grid_penalty = 0.0
        if stints_completed == 0 and grid_position > 0:
            grid_penalty = self.grid_model.get_first_stint_lap_adjustment(grid_position, 20)

        # (5) Safety car effects
        sc_penalty = 0.0
        if sc_laps:
            for sc_start, sc_duration in sc_laps:
                if sc_start <= current_lap < sc_start + sc_duration:
                    sc_penalty = -0.5  # SC zones are typically ~25s slower

        # (6) Tyre life ratio (0 = fresh, 1 = end of life)
        life_ratio = (lap_in_stint - 1) / max(total_stint_laps, 1)

        # Get compound characteristics
        chars = self.compound_chars.get(compound, {})
        cliff_point = chars.get('cliff_point', 0.8)
        cliff_severity = chars.get('cliff_severity', 0.5)

        # (7) Enhanced degradation with weather sensitivity
        adjusted_degradation_rate = degradation_rate

        # Apply weather multiplier
        adjusted_degradation_rate *= self.degradation_model.apply_weather_degradation_adjustment(
            1.0, weather
        )

        # Apply temperature multiplier to degradation
        temp_deg_multiplier = self.degradation_model.get_temperature_degradation_multiplier(
            ambient_temp, tire_temp
        )
        adjusted_degradation_rate *= temp_deg_multiplier

        # Apply fuel weight multiplier
        if self.include_fuel_weight and fuel_weight > 0:
            weight_multiplier = self.fuel_model.get_degradation_multiplier(fuel_weight)
            adjusted_degradation_rate *= weight_multiplier

        # Apply track roughness multiplier
        adjusted_degradation_rate *= track_roughness

        # (8) Dynamic cliff point based on conditions
        severity_factor = max(0.7, min(1.5, temp_deg_multiplier))
        dynamic_cliff_point = self.degradation_model.get_dynamic_cliff_point(compound, severity_factor)

        # (9) Non-linear degradation model with dynamic cliff
        if life_ratio < dynamic_cliff_point:
            # Linear degradation phase
            degradation = adjusted_degradation_rate * (lap_in_stint - 1)
        else:
            # Cliff phase - rapid degradation
            linear_portion = adjusted_degradation_rate * (dynamic_cliff_point * total_stint_laps)
            cliff_portion = (life_ratio - dynamic_cliff_point) * adjusted_degradation_rate * total_stint_laps * cliff_severity
            degradation = linear_portion + cliff_portion

        # Final lap time
        lap_time = adjusted_base + temp_delta + fuel_penalty + fatigue_penalty + grid_penalty + sc_penalty + degradation

        return max(base_lap_time * 0.5, lap_time)  # Safety: don't go below 50% of base (signifies error)

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

    def perform_monte_carlo_analysis(
        self,
        strategy: List[str],
        total_laps: int,
        degradation_rates: Dict[str, float],
        base_times: Dict[str, float],
        driver_delta: float,
        pit_stop_loss: float,
        num_simulations: int = 1000,
        parameter_uncertainty: Dict[str, Tuple[float, float]] = None
    ) -> Dict:
        """
        Monte Carlo probabilistic analysis of a strategy.
        Runs multiple simulations with parameter variations to get outcome distributions.

        Args:
            strategy: Tire strategy
            total_laps: Total race laps
            degradation_rates: Base degradation rates
            base_times: Base lap times
            driver_delta: Driver pace delta
            pit_stop_loss: Pit stop time loss
            num_simulations: Number of MC simulations to run
            parameter_uncertainty: Dict of param -> (mean, std_dev) for distributions

        Returns:
            {
                'mean_time': float,
                'std_dev': float,
                'best_case': float (5th percentile),
                'worst_case': float (95th percentile),
                'win_probability': float (0-1),
                'results_distribution': List[float] (all simulation times),
                'percentiles': Dict (5th, 25th, 50th, 75th, 95th)
            }
        """
        if parameter_uncertainty is None:
            # Default uncertainty distributions
            parameter_uncertainty = {
                'pit_loss_std': 0.5,        # ±0.5s variability in pit stops
                'degradation_std': 0.01,   # ±0.01 s/lap variability
                'driver_delta_std': 0.1,   # ±0.1s variability in pace
                'ambient_temp_std': 3.0,   # ±3°C temperature variance
            }

        results_times = []

        for sim_num in range(num_simulations):
            # Sample parameters from distributions
            varied_pit_loss = pit_stop_loss + np.random.normal(0, parameter_uncertainty.get('pit_loss_std', 0.5))
            varied_pit_loss = max(15, varied_pit_loss)  # Pit loss can't be < 15s

            varied_degradation = {
                k: max(0.001, v + np.random.normal(0, parameter_uncertainty.get('degradation_std', 0.01)))
                for k, v in degradation_rates.items()
            }

            varied_driver_delta = driver_delta + np.random.normal(0, parameter_uncertainty.get('driver_delta_std', 0.1))

            varied_ambient_temp = 25 + np.random.normal(0, parameter_uncertainty.get('ambient_temp_std', 3.0))
            varied_ambient_temp = max(10, min(40, varied_ambient_temp))  # Clamp to 10-40°C

            # Run simulation with varied parameters
            try:
                result = self.simulate_strategy_advanced(
                    strategy=strategy,
                    total_laps=total_laps,
                    degradation_rates=varied_degradation,
                    base_times=base_times,
                    driver_delta=varied_driver_delta,
                    pit_stop_loss=varied_pit_loss,
                    ambient_temp=varied_ambient_temp,
                    starting_fuel=110.0
                )
                results_times.append(result['total_time'])
            except Exception as e:
                # If simulation fails, skip this iteration
                continue

        if not results_times:
            return {
                'mean_time': 0,
                'std_dev': 0,
                'best_case': 0,
                'worst_case': 0,
                'win_probability': 0,
                'results_distribution': [],
                'percentiles': {}
            }

        results_array = np.array(results_times)

        # Calculate statistics
        mean_time = float(np.mean(results_array))
        std_dev = float(np.std(results_array))
        best_case = float(np.percentile(results_array, 5))
        worst_case = float(np.percentile(results_array, 95))

        # Calculate percentiles
        percentiles = {
            'p5': float(np.percentile(results_array, 5)),
            'p25': float(np.percentile(results_array, 25)),
            'p50': float(np.percentile(results_array, 50)),
            'p75': float(np.percentile(results_array, 75)),
            'p95': float(np.percentile(results_array, 95)),
        }

        # Win probability (assuming typical opponent time ~10 seconds better than baseline)
        # This is probabilistic: what % of simulations beat a reference time
        opponent_reference = mean_time - 5  # Optimistic assumption
        win_probability = float(np.sum(results_array < opponent_reference) / len(results_array))

        return {
            'mean_time': mean_time,
            'std_dev': std_dev,
            'best_case': best_case,
            'worst_case': worst_case,
            'win_probability': max(0, min(1, win_probability)),
            'results_distribution': [float(x) for x in results_times[:100]],  # Sample for frontend
            'percentiles': percentiles,
            'num_simulations_completed': len(results_times)
        }

    def calculate_optimal_pit_window(
        self,
        current_stint_laps: int,
        total_laps: int,
        degradation_rate: float,
        stint_length_estimate: int
    ) -> Dict[str, int]:
        """
        Calculate optimal pit window for next stop.

        Returns:
            {
                'earliest_lap': int,  # Earliest safe pit lap
                'optimal_lap': int,   # Recommended pit lap
                'latest_lap': int,    # Latest safe pit lap
                'pit_before_cliff': bool
            }
        """
        # Estimate cliff point (80% of stint)
        cliff_lap = int(stint_length_estimate * 0.80)

        earliest_lap = current_stint_laps + max(5, int(stint_length_estimate * 0.4))
        optimal_lap = min(cliff_lap - 2, earliest_lap + int(stint_length_estimate * 0.3))
        latest_lap = cliff_lap - 1

        return {
            'earliest_lap': earliest_lap,
            'optimal_lap': optimal_lap,
            'latest_lap': latest_lap,
            'pit_before_cliff': optimal_lap < cliff_lap
        }
