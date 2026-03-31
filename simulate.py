import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pickle
import warnings
import os
from itertools import product
from typing import Dict, List, Any

from advanced_analysis import AdvancedStrategyAnalyzer

warnings.filterwarnings("ignore")

# --- Helper Functions ---

def generate_strategies():
    """Generates all valid 1, 2, and 3-stop strategies."""
    compounds = ['SOFT', 'MEDIUM', 'HARD']
    strategies = {}

    # 1-Stop (6 permutations)
    for p in product(compounds, repeat=2):
        if len(set(p)) > 1:
            strategies[f"1-Stop ({p[0][0]}-{p[1][0]})"] = list(p)

    # 2-Stop (21 valid permutations)
    for p in product(compounds, repeat=3):
        if len(set(p)) > 1:
            strategies[f"2-Stop ({p[0][0]}-{p[1][0]}-{p[2][0]})"] = list(p)

    # 3-Stop (60 valid permutations)
    for p in product(compounds, repeat=4):
        if len(set(p)) > 1:
            strategies[f"3-Stop ({p[0][0]}-{p[1][0]}-{p[2][0]}-{p[3][0]})"] = list(p)

    print(f"Generated {len(strategies)} potential strategies for simulation.")
    return strategies

def apply_sanity_checks_and_fallbacks(driver_factors, grid_avg_deg, track_baseline_deg, base_times):
    print("\n--- Applying Fallbacks and Sanity Checks ---")
    baseline_degradation_hardcoded = {'SOFT': 0.100, 'MEDIUM': 0.071, 'HARD': 0.055}

    # --- 1. Fallbacks for Realistic Base Times ---
    base_times_copy = base_times.copy()
    if 'MEDIUM' not in base_times:
        if 'SOFT' in base_times_copy: base_times['MEDIUM'] = base_times_copy['SOFT'] + 0.7
        elif 'HARD' in base_times_copy: base_times['MEDIUM'] = base_times_copy['HARD'] - 0.8
    if 'HARD' not in base_times:
        if 'MEDIUM' in base_times: base_times['HARD'] = base_times['MEDIUM'] + 0.8
        elif 'SOFT' in base_times_copy: base_times['HARD'] = base_times_copy['SOFT'] + 1.5
    if 'SOFT' not in base_times:
        if 'MEDIUM' in base_times: base_times['SOFT'] = base_times['MEDIUM'] - 0.7
        elif 'HARD' in base_times: base_times['SOFT'] = base_times['HARD'] - 1.5
    
    # Fill any completely missing base times with a high value
    for c in ['SOFT', 'MEDIUM', 'HARD']:
        if c not in base_times:
            print(f"WARNING: No base time data for {c}. Using 120s fallback.")
            base_times[c] = 120 

    final_deg_rates = {}
    def is_sane(rate):
        return rate is not None and 0.005 < rate < 0.5

    for compound in ['SOFT', 'MEDIUM', 'HARD']:
        effective_track_baseline = track_baseline_deg.get(compound)
        if not is_sane(effective_track_baseline):
            effective_track_baseline = grid_avg_deg.get(compound)
            if not is_sane(effective_track_baseline):
                effective_track_baseline = baseline_degradation_hardcoded[compound]
                print(f"WARNING: Track & Grid baseline for {compound} unrealistic. Using hardcoded baseline.")
            else:
                print(f"INFO: Track baseline for {compound} unrealistic. Using season grid average baseline.")
        else:
            print(f"INFO: Using track-specific baseline for {compound}: {effective_track_baseline:.4f} s/lap")

        driver_factor = driver_factors.get(compound, 1.0)
        if driver_factor < 0.5 or driver_factor > 2.0:
            print(f"WARNING: Driver degradation factor for {compound} ({driver_factor:.2f}) is extreme. Capping to 1.0.")
            driver_factor = 1.0

        calculated_deg_rate = effective_track_baseline * driver_factor

        if is_sane(calculated_deg_rate):
            final_deg_rates[compound] = calculated_deg_rate
            print(f"  -> Final {compound} degradation for driver: {calculated_deg_rate:.4f} s/lap")
        else:
            final_deg_rates[compound] = baseline_degradation_hardcoded[compound]
            print(f"ERROR: Calculated final {compound} degradation ({calculated_deg_rate:.4f}) unrealistic. Reverting to baseline.")

    return final_deg_rates, base_times


def format_time(seconds):
    hours = int(seconds // 3600); minutes = int((seconds % 3600) // 60); secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def simulate_strategy(strategy, total_laps, degradation_rates, realistic_base_times, driver_delta, pit_stop_loss):
    total_race_time = (len(strategy) - 1) * pit_stop_loss
    stint_lengths = [total_laps // len(strategy)] * len(strategy)
    for i in range(total_laps % len(strategy)): stint_lengths[i] += 1
    pit_laps, laps_completed = [], 0

    for i, compound in enumerate(strategy):
        stint_laps = stint_lengths[i]
        base_lap_time = realistic_base_times.get(compound, 120)
        driver_adjusted_base_time = base_lap_time + driver_delta
        degradation_rate = degradation_rates.get(compound, 0.1)
        for lap_in_stint in range(1, stint_laps + 1):
            degradation_offset = (lap_in_stint - 1) * degradation_rate
            total_race_time += driver_adjusted_base_time + degradation_offset
        laps_completed += stint_laps
        if i < len(strategy) - 1:
            pit_laps.append(laps_completed)
    return total_race_time, pit_laps


def visualize_strategies(sorted_results, total_laps, driver, track, final_degradation_rates):
    # This function is no longer called by the API, but can be kept for other testing
    pass

# --- 4. Main Execution Block (Lookup & Simulate) ---

# --- FIX: Renamed arguments to match FastAPI request ---
def run_simulation(driver_name: str, race_name: str, pit_stop_loss: float, db: Dict) -> Dict:
    """
    Main function to run the simulation with advanced analysis.
    Takes driver name, race name, pit loss, and the loaded database.
    Returns a dictionary with all simulation results including advanced metrics.
    """

    # --- Look up all data from the database ---
    try:
        track_data = db['track_models'][race_name]
        driver_data = db['driver_performance'][driver_name]
        grid_avg_degradation = db['driver_performance']['GRID_AVG']['degradation_rates']

        # Get data for simulation
        track_baseline_deg = track_data['baseline_degradation']
        realistic_base_times = track_data['realistic_base_times']
        total_laps = track_data['total_laps']
        degradation_factors = driver_data['degradation_factors']
        avg_lap_delta = driver_data['avg_lap_delta']

    except KeyError as e:
        print(f"❌ ERROR: Could not find required data in database: {e}")
        return {"error": f"Could not find required data for {e}. This driver or track may not be in the database."}

    # Generate all possible strategies
    strategies_to_test = generate_strategies()

    # Combine data and apply sanity checks
    final_degradation_rates, realistic_base_times = apply_sanity_checks_and_fallbacks(
        degradation_factors, grid_avg_degradation, track_baseline_deg, realistic_base_times
    )

    print(f"\nParameters (after fallbacks & sanity checks):")
    print(f"  - Total Laps: {total_laps}")
    print(f"  - Pit Stop Time Loss: {pit_stop_loss}s")
    print(f"  - Realistic Base Times: {realistic_base_times}")
    print(f"  - Driver Pace Delta: {avg_lap_delta:+.3f}s")
    print(f"  - Final Degradation Rates (s/lap): {final_degradation_rates}\n")

    # Initialize advanced analyzer
    analyzer = AdvancedStrategyAnalyzer(
        driver_data={'delta': avg_lap_delta},
        track_data=track_data
    )

    simulation_results = {}
    for name, strategy in strategies_to_test.items():
        if all(c in final_degradation_rates and c in realistic_base_times for c in strategy):
            # Use advanced simulation for richer metrics
            advanced_result = analyzer.simulate_strategy_advanced(
                strategy,
                total_laps,
                final_degradation_rates,
                realistic_base_times,
                avg_lap_delta,
                pit_stop_loss
            )

            # Also calculate reliability metrics
            stint_lengths = [total_laps // len(strategy)] * len(strategy)
            for i in range(total_laps % len(strategy)):
                stint_lengths[i] += 1

            reliability = analyzer.calculate_strategy_reliability(strategy, stint_lengths)

            simulation_results[name] = {
                'time': advanced_result['total_time'],
                'pits': advanced_result['pit_laps'],
                'compounds': strategy,
                'metrics': advanced_result['metrics'],
                'reliability': reliability,
                'lap_times': advanced_result['lap_times']
            }

    if not simulation_results:
        return {"error": "No valid strategies could be simulated based on the available data."}

    best_strategy_name = min(simulation_results, key=lambda k: simulation_results[k]['time'])
    sorted_results = sorted(simulation_results.items(), key=lambda item: item[1]['time'])

    # Calculate sensitivity analysis for the optimal strategy
    optimal_strategy = simulation_results[best_strategy_name]['compounds']
    sensitivity_analysis = analyzer.perform_sensitivity_analysis(
        optimal_strategy,
        total_laps,
        final_degradation_rates,
        realistic_base_times,
        avg_lap_delta,
        pit_stop_loss,
        parameter='pit_loss'
    )

    # --- Prepare JSON Response ---
    
    # 1. Simulation Parameters
    sim_params = {
        "driver": driver_name,
        "race": race_name,
        "total_laps": int(total_laps),
        "pit_stop_loss": float(pit_stop_loss),
        "final_degradation_rates": final_degradation_rates
    }

    # 2. Optimal Strategy with advanced metrics
    optimal_data = simulation_results[best_strategy_name]
    optimal_strategy = {
        "name": best_strategy_name,
        "pit_laps": [int(p) for p in optimal_data['pits']],
        "metrics": optimal_data['metrics'],
        "reliability": optimal_data['reliability']
    }

    # 3. Top 3 Results with advanced analysis
    top_3_results = []
    for name, results in sorted_results[:3]:
        total_time = results['time']
        pit_laps_list = results['pits']

        pit_laps_clean = [int(p) for p in pit_laps_list]
        pit_string = f"Pits on Laps: {pit_laps_clean}" if pit_laps_clean else "No Pit Stops"

        delta_string = f"(+{total_time - simulation_results[best_strategy_name]['time']:.3f}s)" if name != best_strategy_name else ""

        top_3_results.append({
            "name": name,
            "pit_stops_text": pit_string,
            "total_time_str": format_time(total_time),
            "delta_str": delta_string,
            "metrics": results.get('metrics', {}),
            "reliability": results.get('reliability', {})
        })

    # 4. Visualization Data
    viz_data = []
    for name, results in sorted_results[:3]:
        compounds_list = results['compounds']
        stint_lengths = [total_laps // len(compounds_list)] * len(compounds_list)
        for k in range(total_laps % len(compounds_list)): stint_lengths[k] += 1
        
        stints = []
        for j, stint_laps in enumerate(stint_lengths):
            stints.append({
                "compound": compounds_list[j],
                "laps": int(stint_laps) # <--- FIX
            })
        
        viz_data.append({
            "name": name,
            "stints": stints
        })

    # 5. Advanced analysis data
    advanced_data = {
        "sensitivity_analysis": {
            "pit_loss_variations": sensitivity_analysis['variations'],
            "times": [float(t) for t in sensitivity_analysis['times']],
            "deltas": [float(d) for d in sensitivity_analysis['deltas']]
        }
    }

    # 6. Final JSON object with all enhanced data
    return {
        "simulation_parameters": sim_params,
        "optimal_strategy": optimal_strategy,
        "top_3_results": top_3_results,
        "visualization_data": viz_data,
        "advanced_analysis": advanced_data
    }

