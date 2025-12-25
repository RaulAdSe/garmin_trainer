#!/usr/bin/env python3
"""
FastAPI service for Garmin Connect - handles complex OAuth flow.
n8n calls this via HTTP Request nodes.

Usage:
    cd /Users/rauladell/n8n-claude/scripts
    pip3 install garth fastapi uvicorn
    uvicorn api:app --host 0.0.0.0 --port 8765
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import garth

app = FastAPI(title="Garmin Fetch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TOKEN_DIR = Path(__file__).parent / ".garth_tokens"


def authenticate(email: str, password: str):
    """Authenticate with Garmin Connect."""
    # Try to resume existing session
    if TOKEN_DIR.exists():
        try:
            garth.resume(TOKEN_DIR)
            # Test if session is still valid
            garth.connectapi("/userprofile-service/socialProfile")
            return
        except Exception:
            pass  # Session expired

    # Fresh authentication
    try:
        garth.login(email, password)
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        garth.save(TOKEN_DIR)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Auth failed: {e}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/activities")
def get_activities(
    email: str = Query(..., description="Garmin email"),
    password: str = Query(..., description="Garmin password"),
    count: int = Query(default=10, ge=1, le=200),
    activity_types: str = Query(default="running,trail_running,treadmill_running")
):
    """Fetch activities from Garmin Connect."""
    authenticate(email, password)

    # Fetch activities via garth
    activities = garth.connectapi(
        "/activitylist-service/activities/search/activities",
        params={"limit": count, "start": 0}
    )

    if not activities:
        return []

    # Filter by type
    type_list = [t.strip() for t in activity_types.split(",")]

    results = []
    for activity in activities:
        act_type = activity.get("activityType", {}).get("typeKey", "unknown")
        if act_type not in type_list:
            continue

        distance = activity.get("distance", 0)
        duration = activity.get("duration", 0)

        results.append({
            "activity_id": str(activity.get("activityId")),
            "activity_type": act_type,
            "activity_name": activity.get("activityName", ""),
            "start_time": activity.get("startTimeLocal", ""),
            "distance_m": distance,
            "duration_s": duration,
            "avg_hr": activity.get("averageHR"),
            "max_hr": activity.get("maxHR"),
            "avg_cadence": activity.get("averageRunningCadenceInStepsPerMinute"),
            "avg_pace_sec_per_km": (duration / (distance / 1000)) if distance > 0 else None,
            "elevation_gain_m": activity.get("elevationGain"),
            "elevation_loss_m": activity.get("elevationLoss"),
            "training_effect_aerobic": activity.get("aerobicTrainingEffect"),
            "training_effect_anaerobic": activity.get("anaerobicTrainingEffect"),
            "vo2max": activity.get("vO2MaxValue"),
            "calories": activity.get("calories"),
            "raw_json": json.dumps(activity),
            "synced_at": datetime.utcnow().isoformat() + "Z"
        })

    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
