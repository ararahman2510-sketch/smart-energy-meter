import numpy as np
from sklearn.ensemble import IsolationForest
from typing import List, Dict, Any, Optional

# Grid emission intensity factor for India (CEA Baseline: ~0.71 kg CO2 / kWh)
CARBON_INTENSITY_KG_PER_KWH = 0.716

class AnomalyDetector:
    def __init__(self, contamination: float = 0.05):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self._fit_initial_baseline()

    def _fit_initial_baseline(self):
        standby = np.random.normal(loc=50, scale=15, size=(400, 1))
        medium = np.random.normal(loc=800, scale=200, size=(400, 1))
        high = np.random.normal(loc=2200, scale=350, size=(200, 1))
        synthetic_data = np.vstack([standby, medium, high])
        synthetic_data = np.clip(synthetic_data, 10.0, 5000.0)
        self.model.fit(synthetic_data)

    def predict(self, active_power_watts: float) -> bool:
        prediction = self.model.predict([[active_power_watts]])
        return bool(prediction[0] == -1)

def classify_appliance_nilm(delta_watts: float, power_factor: float) -> Optional[str]:
    """
    Non-Intrusive Load Monitoring (NILM) signature disaggregation
    Identifies high-draw devices based on step changes in active & reactive load.
    """
    abs_delta = abs(delta_watts)
    if abs_delta < 40:
        return None
    if 1800 <= abs_delta <= 2800 and power_factor > 0.92:
        return "Water Geyser / Electric Kettle (Resistive High Load)"
    elif 1200 <= abs_delta <= 2000 and power_factor < 0.88:
        return "Air Conditioner / Heat Pump (Inductive Motor)"
    elif 600 <= abs_delta <= 1100 and power_factor < 0.85:
        return "Microwave / Washing Machine Spin Cycle"
    elif 100 <= abs_delta <= 250:
        return "Refrigerator Compressor Cycle"
    elif 40 <= abs_delta <= 90:
        return "Entertainment Console / PC Rig"
    return "Unclassified Distributed Load"

def detect_phantom_load(recent_readings: List[Dict[str, Any]], idle_threshold_watts: float = 80.0) -> Dict[str, Any]:
    if not recent_readings:
        return {
            "is_phantom_detected": False,
            "baseline_waste_watts": 0.0,
            "estimated_monthly_loss_kwh": 0.0,
            "loss_inr": 0.0
        }

    powers = [r.get("active_power_watts", 0.0) for r in recent_readings]
    min_power = min(powers)

    is_phantom = 12.0 <= min_power <= idle_threshold_watts
    estimated_monthly_kwh = (min_power * 24 * 30) / 1000.0 if is_phantom else 0.0
    loss_inr = estimated_monthly_kwh * 6.5

    return {
        "is_phantom_detected": is_phantom,
        "baseline_waste_watts": round(min_power, 2),
        "estimated_monthly_loss_kwh": round(estimated_monthly_kwh, 2),
        "loss_inr": round(loss_inr, 2)
    }

def generate_smart_bill(total_units_kwh: float, phantom_stats: Dict[str, Any], anomaly_count: int) -> Dict[str, Any]:
    if total_units_kwh <= 100:
        base_bill = total_units_kwh * 4.50
    elif total_units_kwh <= 300:
        base_bill = (100 * 4.50) + ((total_units_kwh - 100) * 6.50)
    else:
        base_bill = (100 * 4.50) + (200 * 6.50) + ((total_units_kwh - 300) * 8.50)

    phantom_cost = phantom_stats.get("loss_inr", 0.0)
    total_bill = round(base_bill, 2)
    carbon_emitted_kg = round(total_units_kwh * CARBON_INTENSITY_KG_PER_KWH, 2)

    recommendations = []
    if phantom_stats.get("is_phantom_detected", False):
        recommendations.append(
            f"Vampire Load Detected: {phantom_stats['baseline_waste_watts']}W continuous standby draw. "
            f"Unplug AV systems, setup boxes, and chargers to save ~₹{phantom_stats['loss_inr']}/month."
        )
    else:
        recommendations.append("Idle Standby Efficiency: Good. No significant vampire draw identified.")

    if anomaly_count > 0:
        recommendations.append(
            f"Power Quality Alert: {anomaly_count} surge/leakage anomalies captured. "
            "Inspect high-draw inductive loads (refrigerator compressor, HVAC, or water pump)."
        )
    else:
        recommendations.append("Grid Stability: Voltage and current profiles are within safe operational bounds.")

    if total_units_kwh > 250:
        recommendations.append("High Slab Warning: You are near the ₹8.50/unit threshold. Shift heavy loads to off-peak hours.")

    return {
        "units_consumed_kwh": round(total_units_kwh, 2),
        "total_bill_inr": total_bill,
        "carbon_kg": carbon_emitted_kg,
        "phantom_loss_kwh": phantom_stats.get("estimated_monthly_loss_kwh", 0.0),
        "phantom_waste_inr": phantom_cost,
        "anomalies_detected": anomaly_count,
        "ai_recommendations": recommendations
    }
