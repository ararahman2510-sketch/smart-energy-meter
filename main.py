import os
import time
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from ml_engine import AnomalyDetector, detect_phantom_load, generate_smart_bill

app = FastAPI(
    title="AI Smart Energy Meter Cloud API",
    description="Real-time ingestion, Isolation Forest anomaly detection, and smart billing.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = os.getenv("MONGO_URI", "")
db_collection = None

if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
        client.admin.command('ping')
        db = client["smart_meter_db"]
        db_collection = db["telemetry_logs"]
        print("Connected to MongoDB Atlas successfully.")
    except Exception as e:
        print(f"MongoDB connection failed: {e}. Running in Memory-Buffer mode.")
        db_collection = None
else:
    print("No MONGO_URI configured. Running purely in Cloud Memory-Buffer mode.")

detector = AnomalyDetector()
TELEMETRY_BUFFER: List[dict] = []
BUFFER_MAX_SIZE = 200

class TelemetryPayload(BaseModel):
    meter_id: str = Field(..., example="METER_01")
    timestamp: float = Field(default_factory=time.time)
    voltage: float = Field(..., ge=0.0, le=500.0, example=230.5)
    current: float = Field(..., ge=0.0, le=100.0, example=4.2)
    power_factor: float = Field(..., ge=0.0, le=1.0, example=0.95)
    active_power_watts: float = Field(..., ge=0.0, example=919.69)
    is_idle: bool = Field(default=False)

@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "AI Smart Meter Cloud API",
        "buffered_records": len(TELEMETRY_BUFFER),
        "db_connected": db_collection is not None
    }

@app.post("/api/v1/telemetry")
def ingest_telemetry(payload: TelemetryPayload):
    record = payload.model_dump()
    is_anomaly = detector.predict(record["active_power_watts"])
    record["is_anomaly"] = is_anomaly

    TELEMETRY_BUFFER.append(record)
    if len(TELEMETRY_BUFFER) > BUFFER_MAX_SIZE:
        TELEMETRY_BUFFER.pop(0)

    if db_collection is not None:
        try:
            db_collection.insert_one(record.copy())
        except PyMongoError as err:
            print(f"Failed to persist to MongoDB: {err}")

    return {
        "status": "success",
        "meter_id": record["meter_id"],
        "anomaly_detected": is_anomaly,
        "recorded_power_watts": record["active_power_watts"]
    }

@app.get("/api/v1/telemetry/recent")
def get_recent_telemetry(limit: int = 50):
    limit = max(1, min(limit, BUFFER_MAX_SIZE))
    clean_records = [
        {k: v for k, v in item.items() if k != "_id"}
        for item in TELEMETRY_BUFFER[-limit:]
    ]
    return clean_records

@app.get("/api/v1/analytics/bill")
def get_ai_smart_bill():
    if not TELEMETRY_BUFFER:
        raise HTTPException(status_code=400, detail="No telemetry data received yet.")

    step_duration_seconds = 2.0
    total_joules = sum(r["active_power_watts"] * step_duration_seconds for r in TELEMETRY_BUFFER)
    base_kwh = total_joules / 3600000.0
    simulated_accumulated_kwh = round(base_kwh * 60.0, 2)

    phantom_results = detect_phantom_load(TELEMETRY_BUFFER)
    anomaly_count = sum(1 for r in TELEMETRY_BUFFER if r.get("is_anomaly", False))

    smart_bill = generate_smart_bill(
        total_units_kwh=simulated_accumulated_kwh,
        phantom_stats=phantom_results,
        anomaly_count=anomaly_count
    )

    return {
        "meter_id": TELEMETRY_BUFFER[-1]["meter_id"],
        "buffer_sample_size": len(TELEMETRY_BUFFER),
        "phantom_analysis": phantom_results,
        "bill_details": smart_bill
    }

@app.post("/api/v1/buffer/clear")
def clear_buffer():
    TELEMETRY_BUFFER.clear()
    return {"status": "cleared", "buffer_size": 0}
