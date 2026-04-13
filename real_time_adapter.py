"""
Real-time Telemetry Adapter
Ingests race telemetry data to update strategy model parameters dynamically.
"""

from typing import Dict, List, Optional
import numpy as np


class TelemetryAdapter:
    """
    Adapts telemetry data to update model parameters mid-race.
    Examples:
    - Actual pit times vs. predicted
    - Observed tire degradation vs. predicted
    - Weather condition changes
    - Fuel consumption rates
    """

    def __init__(self):
        """Initialize with empty telemetry data."""
        self.pit_times_observed = []
        self.degradation_observed = []
        self.fuel_consumption_observed = []
        self.weather_conditions = []
        self.lap_times_observed = []

    def add_pit_stop_telemetry(self, pit_duration: float, lap_number: int):
        """
        Record observed pit stop duration.

        Args:
            pit_duration: Pit stop time in seconds
            lap_number: Lap on which pit stop occurred
        """
        self.pit_times_observed.append({
            'duration': pit_duration,
            'lap': lap_number
        })

    def add_lap_time_telemetry(self, lap_number: int, lap_time: float,
                               compound: str, tire_age: int):
        """
        Record observed lap time.

        Args:
            lap_number: Lap number
            lap_time: Actual lap time in seconds
            compound: Tire compound used
            tire_age: Age of tire in laps
        """
        self.lap_times_observed.append({
            'lap': lap_number,
            'time': lap_time,
            'compound': compound,
            'tire_age': tire_age
        })

    def add_fuel_consumption_telemetry(self, fuel_consumed: float, laps: int):
        """
        Record observed fuel consumption.

        Args:
            fuel_consumed: Fuel consumed in kilograms
            laps: Number of laps covered
        """
        if laps > 0:
            self.fuel_consumption_observed.append({
                'consumption_rate': fuel_consumed / laps,  # kg/lap
                'stint_laps': laps
            })

    def add_weather_update(self, temperature: float, track_condition: str,
                          humidity: float = 50.0):
        """
        Record weather condition update.

        Args:
            temperature: Ambient temperature in Celsius
            track_condition: 'DRY', 'HUMID', 'HOT_DRY', 'COOL_DRY', 'WET', etc.
            humidity: Relative humidity 0-100
        """
        self.weather_conditions.append({
            'temperature': temperature,
            'condition': track_condition,
            'humidity': humidity
        })

    def get_updated_pit_loss(self) -> Optional[float]:
        """
        Calculate average pit stop time from telemetry.

        Returns:
            Average pit stop duration, or None if no data
        """
        if not self.pit_times_observed:
            return None

        pit_times = [pit['duration'] for pit in self.pit_times_observed]
        return float(np.mean(pit_times))

    def get_updated_fuel_consumption_rate(self, compound: Optional[str] = None) -> Optional[float]:
        """
        Calculate fuel consumption rate from telemetry.

        Args:
            compound: Optional tire compound filter

        Returns:
            Average fuel consumption rate (kg/lap), or None if no data
        """
        if not self.fuel_consumption_observed:
            return None

        rates = [fuel['consumption_rate'] for fuel in self.fuel_consumption_observed]
        return float(np.mean(rates))

    def estimate_degradation_from_telemetry(self, compound: str = 'SOFT') -> Optional[float]:
        """
        Estimate tire degradation rate from observed lap times.

        Args:
            compound: Filter to specific tire compound

        Returns:
            Estimated degradation rate (s/lap), or None if insufficient data
        """
        if len(self.lap_times_observed) < 5:
            return None

        # Filter to same compound
        compound_laps = [lap for lap in self.lap_times_observed
                         if lap['comp'] == compound]

        if len(compound_laps) < 3:
            return None

        # Simple linear regression to find slope (degradation)
        laps_array = np.array([lap['tire_age'] for lap in compound_laps], dtype=float)
        times_array = np.array([lap['time'] for lap in compound_laps], dtype=float)

        if len(laps_array) < 2 or np.std(laps_array) == 0:
            return None

        # Linear fit: time = a + b * tire_age
        coeffs = np.polyfit(laps_array, times_array, 1)
        degradation_rate = coeffs[0]  # Slope

        return float(max(0.001, degradation_rate))

    def get_weather_condition(self) -> Optional[str]:
        """Get latest weather condition from telemetry."""
        if not self.weather_conditions:
            return None

        latest = self.weather_conditions[-1]
        return latest['condition']

    def get_ambient_temperature(self) -> Optional[float]:
        """Get latest ambient temperature from telemetry."""
        if not self.weather_conditions:
            return None

        latest = self.weather_conditions[-1]
        return latest['temperature']

    def generate_parameter_update_dict(self) -> Dict[str, float]:
        """
        Generate dictionary of updated parameters for simulation.

        Returns:
            Dict with any available updated parameters
        """
        updates = {}

        pit_loss = self.get_updated_pit_loss()
        if pit_loss is not None:
            updates['pit_stop_loss'] = pit_loss

        fuel_rate = self.get_updated_fuel_consumption_rate()
        if fuel_rate is not None:
            updates['fuel_consumption_rate'] = fuel_rate

        weather = self.get_weather_condition()
        if weather is not None:
            updates['weather'] = weather

        temp = self.get_ambient_temperature()
        if temp is not None:
            updates['ambient_temperature'] = temp

        return updates

    def clear_telemetry(self):
        """Clear all recorded telemetry data."""
        self.pit_times_observed = []
        self.degradation_observed = []
        self.fuel_consumption_observed = []
        self.weather_conditions = []
        self.lap_times_observed = []
