"""
Advanced F1 Strategy Analysis Module
Contains improved degradation models, risk analysis, and detailed metrics
"""

import numpy as np
from typing import Dict, List, Tuple
import math

class AdvancedStrategyAnalyzer:
    """
    Advanced analysis engine for F1 strategy simulation
    Features:
    - Non-linear tyre degradation modeling
    - Lap-by-lap predictions
    - Safety margins and reliability scores
    - Risk assessment
    """

    def __init__(self, driver_data: Dict, track_data: Dict, compound_characteristics: Dict = None):
        self.driver_data = driver_data
        self.track_data = track_data

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
        ambient_temp: float = 25.0
    ) -> float:
        """
        Calculate lap time with advanced non-linear degradation model.

        Features:
        - Non-linear degradation (accelerates as tyre ages)
        - Temperature effects on performance
        - Cliff point (sudden loss of grip)
        - Compound-specific characteristics
        """

        # Base lap time with driver adjustment
        adjusted_base = base_lap_time + driver_delta

        # Temperature effect (±0.5s per 10°C variance from 25°C)
        temp_delta = (ambient_temp - 25.0) * 0.05

        # Tyre life ratio (0 = fresh, 1 = end of life)
        life_ratio = (lap_in_stint - 1) / max(total_stint_laps, 1)

        # Get compound characteristics
        chars = self.compound_chars.get(compound, {})
        cliff_point = chars.get('cliff_point', 0.8)
        cliff_severity = chars.get('cliff_severity', 0.5)

        # Non-linear degradation model
        if life_ratio < cliff_point:
            # Linear degradation phase
            degradation = degradation_rate * (lap_in_stint - 1)
        else:
            # Cliff phase - rapid degradation
            linear_portion = degradation_rate * (cliff_point * total_stint_laps)
            cliff_portion = (life_ratio - cliff_point) * degradation_rate * total_stint_laps * cliff_severity
            degradation = linear_portion + cliff_portion

        lap_time = adjusted_base + temp_delta + degradation

        return lap_time

    def simulate_strategy_advanced(
        self,
        strategy: List[str],
        total_laps: int,
        degradation_rates: Dict[str, float],
        base_times: Dict[str, float],
        driver_delta: float,
        pit_stop_loss: float,
        ambient_temp: float = 25.0
    ) -> Dict:
        """
        Advanced strategy simulation with detailed metrics.

        Returns:
        {
            'total_time': float,
            'pit_laps': List[int],
            'lap_times': List[float],
            'metrics': {
                'avg_lap_time': float,
                'fastest_lap': float,
                'slowest_lap': float,
                'tyre_life_stress': float (0-1),
                'consistency_score': float (0-100),
                'pit_timing_efficiency': float (0-100)
            }
        }
        """
        total_race_time = (len(strategy) - 1) * pit_stop_loss
        stint_lengths = [total_laps // len(strategy)] * len(strategy)

        for i in range(total_laps % len(strategy)):
            stint_lengths[i] += 1

        pit_laps = []
        lap_times = []
        laps_completed = 0

        for stint_idx, compound in enumerate(strategy):
            stint_laps = stint_lengths[stint_idx]
            base_lap_time = base_times.get(compound, 120)
            degradation_rate = degradation_rates.get(compound, 0.1)

            for lap_in_stint in range(1, stint_laps + 1):
                lap_time = self.calculate_lap_time_with_degradation(
                    base_lap_time=base_lap_time,
                    compound=compound,
                    lap_in_stint=lap_in_stint,
                    total_stint_laps=stint_laps,
                    degradation_rate=degradation_rate,
                    driver_delta=driver_delta,
                    ambient_temp=ambient_temp
                )
                lap_times.append(lap_time)
                total_race_time += lap_time

            laps_completed += stint_laps
            if stint_idx < len(strategy) - 1:
                pit_laps.append(laps_completed)

        # Calculate metrics
        metrics = self._calculate_metrics(lap_times, strategy, stint_lengths)

        return {
            'total_time': total_race_time,
            'pit_laps': pit_laps,
            'lap_times': lap_times,
            'metrics': metrics
        }

    def _calculate_metrics(self, lap_times: List[float], strategy: List[str], stint_lengths: List[int]) -> Dict:
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
