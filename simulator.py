import time
import random
import argparse
import requests
from datetime import datetime

DEFAULT_API_URL = "http://localhost:8000/api/v1/telemetry"

def generate_reading(meter_id: str = "METER_IND_01", force_anomaly: bool = False, force_phantom: bool = False) -> dict:
    timestamp = time.time()
    voltage = round(random.uniform(220.0, 242.0), 2)
    power_factor = round(random.uniform(0.86, 0.97), 2)

    if force_anomaly or (random.random() < 0.08):
        active_power = round(random.uniform(6200.0, 9500.0), 2)
        is_idle = False
        state_label = "SURGE_ANOMALY"
    elif force_phantom or (random.random() < 0.35):
        active_power = round(random.uniform(18.0, 55.0), 2)
        power_factor = round(random.uniform(0.60, 0.78), 2)
        is_idle = True
        state_label = "PHANTOM_STANDBY"
    else:
        active_power = round(random.uniform(250.0, 2200.0), 2)
        is_idle = False
        state_label = "ACTIVE_NORMAL"

    current = round(active_power / (voltage * power_factor), 2)

    return {
        "payload": {
            "meter_id": meter_id,
            "timestamp": timestamp,
            "voltage": voltage,
            "current": current,
            "power_factor": power_factor,
            "active_power_watts": active_power,
            "is_idle": is_idle
        },
        "state_label": state_label
    }

def stream_telemetry(api_url: str, interval: float, meter_id: str):
    print("=" * 65)
    print(f"📡 Smart Meter Telemetry Simulator Online")
    print(f"Target Ingestion Endpoint : {api_url}")
    print(f"Assigned Meter ID         : {meter_id}")
    print(f"Dispatch Interval         : {interval}s")
    print("Press CTRL+C in Konsole to stop simulation.")
    print("=" * 65)

    session = requests.Session()
    packet_count = 0

    try:
        while True:
            packet_data = generate_reading(meter_id=meter_id)
            payload = packet_data["payload"]
            state = packet_data["state_label"]

            try:
                response = session.post(api_url, json=payload, timeout=4.0)
                if response.status_code == 200:
                    resp_json = response.json()
                    is_anomaly = resp_json.get("anomaly_detected", False)
                    flag_display = "⚠️ [ANOMALY DETECTED]" if is_anomaly else "✅ [NORMAL]"
                    
                    time_str = datetime.fromtimestamp(payload["timestamp"]).strftime("%H:%M:%S")
                    print(f"[{time_str}] Pkt #{packet_count:04d} | State: {state:<15} | "
                          f"{payload['active_power_watts']:>7.1f} W | {payload['voltage']} V | "
                          f"{payload['current']:>5.2f} A | {flag_display}")
                    packet_count += 1
                else:
                    print(f"❌ Server Error [{response.status_code}]: {response.text}")

            except requests.exceptions.ConnectionError:
                print(f"⚠️ Endpoint unreachable at {api_url}. Is FastAPI running?")
            except requests.exceptions.Timeout:
                print("⚠️ Request timed out.")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n🛑 Telemetry transmission terminated by user.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic Smart Meter Streamer")
    parser.add_argument("--url", type=str, default=DEFAULT_API_URL, help="Target API URL")
    parser.add_argument("--interval", type=float, default=2.0, help="Dispatch frequency in seconds")
    parser.add_argument("--meter", type=str, default="METER_IND_01", help="Virtual Meter ID")

    args = parser.parse_args()
    stream_telemetry(api_url=args.url, interval=args.interval, meter_id=args.meter)
