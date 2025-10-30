# precompute.py
#
# FASTER, PARALLEL VERSION
# Run this script AFTER 'cache_data.py'.
# It runs 100% OFFLINE from the local Colab cache.
# It creates the master database file in your Colab session.

import fastf1 as ff1
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime
import pickle
import warnings
import os
import concurrent.futures # Import the parallel processing library

warnings.filterwarnings("ignore")

# --- 1. Define Local Colab Paths ---
CACHE_PATH = "fastf1_cache/"
PKL_FILE_PATH = "strategy_database.pkl"
# ------------------------------------

# --- 2. Configuration ---
PAST_YEARS = [2022, 2023] # Data for track models
CURRENT_YEAR = 2024        # Use the most recent FULL season for driver factors
MIN_LAP_COUNT = 5
MAX_WORKERS = 10           # Number of parallel file loaders
# ---------------------

try:
    ff1.Cache.enable_cache(CACHE_PATH)
    print(f"FastF1 cache enabled (reading from {CACHE_PATH}).")
except Exception as e:
    print(f"Could not enable FastF1 cache: {e}")
    exit()

def load_event_laps(task):
    """
    Helper function to load and process a single event's laps from the cache.
    This function will be run in parallel.
    """
    year, event_name = task
    try:
        session = ff1.get_session(year, event_name, 'R')
        session.load(telemetry=False, weather=False, messages=False)
        
        # Skip wet races
        if 'WET' in session.laps['Compound'].unique() or 'INTERMEDIATE' in session.laps['Compound'].unique():
            print(f"-> Skipping wet race: {year} {event_name}")
            return None
            
        laps = session.laps.pick_quicklaps().dropna(subset=['TyreLife', 'Compound', 'LapTime', 'LapNumber', 'Driver', 'Stint'])
        laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()
        laps['EventName'] = event_name
        laps['TotalLaps'] = session.total_laps
        print(f"-> Successfully loaded: {year} {event_name}")
        return laps
    except Exception as e:
        print(f"-> ❌ ERROR loading {year} {event_name} from cache: {e}. Skipping.")
        return None

def get_clean_laps_from_cache(years, is_current_year=False):
    """
    Loads all cached data for a list of years IN PARALLEL.
    """
    print(f"\nBuilding task list for {years}...")
    tasks_to_run = []
    now_utc = pd.to_datetime('now', utc=True)

    for year in years:
        schedule = ff1.get_event_schedule(year)
        for _, event in schedule.iterrows():
            # If it's the "current year", skip future races
            if is_current_year:
                event_date_utc = event['EventDate'].tz_localize('UTC')
                if event_date_utc >= now_utc:
                    continue
            
            tasks_to_run.append((year, event['EventName']))
    
    print(f"Found {len(tasks_to_run)} events to load. Starting parallel load...")
    all_laps = []
    
    # Run all loading tasks in a parallel thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(load_event_laps, tasks_to_run))

    # Filter out any 'None' results from failed loads or wet races
    all_laps = [df for df in results if df is not None]
    
    if not all_laps:
        return None
        
    return pd.concat(all_laps)

def analyze_track_models(past_data):
    """Calculates baseline degradation and pace for EACH track."""
    print("\n--- Analyzing PAST data to build Track Models ---")
    track_models = {}
    for track_name in past_data['EventName'].unique():
        print(f"Analyzing track: {track_name}...")
        track_laps = past_data[past_data['EventName'] == track_name]

        baseline_deg = {}
        realistic_base_times = {}

        for compound in ['SOFT', 'MEDIUM', 'HARD']:
            # Calculate track degradation from all clean laps
            compound_laps = track_laps[track_laps['Compound'] == compound]
            if len(compound_laps) >= MIN_LAP_COUNT:
                res = stats.linregress(compound_laps['TyreLife'], compound_laps['LapTimeSeconds'])
                baseline_deg[compound] = res.slope

            # Calculate realistic base time from first stint laps
            first_stint_laps = track_laps[(track_laps['Stint'] == 1) & (track_laps['LapNumber'] > 1) & (track_laps['Compound'] == compound)]
            if not first_stint_laps.empty:
                realistic_base_times[compound] = first_stint_laps['LapTimeSeconds'].median()
        
        if not track_laps.empty:
            track_models[track_name] = {
                'baseline_degradation': baseline_deg,
                'realistic_base_times': realistic_base_times,
                'total_laps': track_laps['TotalLaps'].iloc[0]
            }
    return track_models

def analyze_driver_performance(current_data):
    """Calculates pace delta and degradation factors for EACH driver in the current year."""
    print("\n--- Analyzing CURRENT data to build Driver Performance Models ---")

    # 1. Get Current Year Grid Average Degradation
    grid_avg_degradation = {}
    for compound in ['SOFT', 'MEDIUM', 'HARD']:
        compound_laps = current_data[current_data['Compound'] == compound]
        if len(compound_laps) >= MIN_LAP_COUNT:
            res = stats.linregress(compound_laps['TyreLife'], compound_laps['LapTimeSeconds'])
            grid_avg_degradation[compound] = res.slope

    driver_performance = {'GRID_AVG': {'degradation_rates': grid_avg_degradation}}

    # 2. Get individual driver factors
    for driver in current_data['Driver'].unique():
        print(f"Analyzing driver: {driver}...")
        driver_laps = current_data[current_data['Driver'] == driver]

        # Calculate degradation factors
        degradation_factors = {}
        for compound in ['SOFT', 'MEDIUM', 'HARD']:
            driver_compound_laps = driver_laps[driver_laps['Compound'] == compound]
            grid_deg = grid_avg_degradation.get(compound)

            if len(driver_compound_laps) >= MIN_LAP_COUNT and grid_deg is not None and grid_deg > 0:
                res = stats.linregress(driver_compound_laps['TyreLife'], driver_compound_laps['LapTimeSeconds'])
                driver_deg = res.slope
                degradation_factors[compound] = driver_deg / grid_deg
            else:
                degradation_factors[compound] = 1.0 # Default to 1.0 (average)

        # Calculate pace deltas
        lap_deltas = []
        for event_name in current_data['EventName'].unique():
            event_laps = current_data[current_data['EventName'] == event_name]
            driver_event_laps = event_laps[event_laps['Driver'] == driver]
            if not driver_event_laps.empty:
                race_median = event_laps['LapTimeSeconds'].median()
                driver_median = driver_event_laps['LapTimeSeconds'].median()
                if not pd.isna(race_median) and not pd.isna(driver_median):
                    lap_deltas.append(driver_median - race_median)

        avg_lap_delta = np.mean(lap_deltas) if lap_deltas else 0.0

        driver_performance[driver] = {
            'degradation_factors': degradation_factors,
            'avg_lap_delta': avg_lap_delta
        }
    return driver_performance

if __name__ == '__main__':
    # Load data in parallel
    past_data = get_clean_laps_from_cache(PAST_YEARS, is_current_year=False)
    current_data = get_clean_laps_from_cache([CURRENT_YEAR], is_current_year=True)

    if past_data is None or current_data is None:
        print("❌ ERROR: Not enough data in cache. Please run 'cache_data.py' again.")
    else:
        # Analyze data (this part is fast)
        track_models = analyze_track_models(past_data)
        driver_performance = analyze_driver_performance(current_data)

        # Combine all data into one database file
        strategy_database = {
            'track_models': track_models,
            'driver_performance': driver_performance
        }

        with open(PKL_FILE_PATH, 'wb') as f:
            pickle.dump(strategy_database, f)
        print(f"\n\n✅ Pre-computation complete! Master database saved to {PKL_FILE_PATH}")