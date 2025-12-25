#!/usr/bin/env python3
"""
Garmin Connect Activity Fetcher for n8n.

Fetches activities from Garmin Connect and outputs normalized JSON to stdout.
Designed to be called by n8n Execute Command node.

Usage:
    export GARMIN_EMAIL="your@email.com"
    export GARMIN_PASSWORD="yourpassword"

    # Fetch last 10 activities
    python garmin_fetch.py --count 10

    # Fetch 100 activities for backfill
    python garmin_fetch.py --count 100

    # Fetch activities since a date
    python garmin_fetch.py --count 50 --since 2024-01-01
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import garth

# Token storage path
TOKEN_DIR = Path(__file__).parent / ".garth_tokens"


def log(message):
    """Log to stderr (so stdout stays clean for JSON output)."""
    print(message, file=sys.stderr)


def authenticate():
    """Authenticate with Garmin Connect."""
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")

    if not email or not password:
        log("Error: GARMIN_EMAIL and GARMIN_PASSWORD environment variables required")
        sys.exit(1)

    # Try to resume existing session
    if TOKEN_DIR.exists():
        try:
            garth.resume(TOKEN_DIR)
            log("Resumed existing session")
            return
        except Exception as e:
            log(f"Session expired, re-authenticating: {e}")

    # Fresh authentication
    try:
        garth.login(email, password)
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        garth.save(TOKEN_DIR)
        log("Authentication successful")
    except Exception as e:
        log(f"Authentication failed: {e}")
        sys.exit(1)


def fetch_activities(count, since_date=None):
    """Fetch activities from Garmin Connect."""
    log(f"Fetching up to {count} activities...")

    params = {"limit": count, "start": 0}

    activities = garth.connectapi(
        "/activitylist-service/activities/search/activities",
        params=params
    )

    # Filter by date if specified
    if since_date:
        activities = [
            a for a in activities
            if a.get("startTimeLocal", "")[:10] >= since_date
        ]
        log(f"Filtered to {len(activities)} activities since {since_date}")

    return activities


def fetch_activity_details(activity_id):
    """Fetch detailed metrics for a single activity."""
    return garth.connectapi(f"/activity-service/activity/{activity_id}")


def normalize_activity(activity, details=None):
    """
    Normalize activity data to match raw_activities table schema.

    Returns a dict with standardized field names and units.
    """
    activity_id = str(activity.get("activityId"))

    # Basic info
    normalized = {
        "activity_id": activity_id,
        "activity_type": activity.get("activityType", {}).get("typeKey", "unknown"),
        "activity_name": activity.get("activityName", ""),
        "start_time": activity.get("startTimeLocal", ""),
        "distance_m": activity.get("distance", 0),
        "duration_s": activity.get("duration", 0),
        "avg_hr": activity.get("averageHR"),
        "max_hr": activity.get("maxHR"),
        "avg_cadence": activity.get("averageRunningCadenceInStepsPerMinute"),
        "elevation_gain_m": activity.get("elevationGain"),
        "elevation_loss_m": activity.get("elevationLoss"),
        "calories": activity.get("calories"),
        "synced_at": datetime.utcnow().isoformat() + "Z",
    }

    # Calculate average pace (sec/km)
    if normalized["distance_m"] and normalized["distance_m"] > 0:
        distance_km = normalized["distance_m"] / 1000
        normalized["avg_pace_sec_per_km"] = normalized["duration_s"] / distance_km
    else:
        normalized["avg_pace_sec_per_km"] = None

    # Training effect and VO2max from summary (may be in different fields)
    normalized["training_effect_aerobic"] = activity.get("aerobicTrainingEffect")
    normalized["training_effect_anaerobic"] = activity.get("anaerobicTrainingEffect")
    normalized["vo2max"] = activity.get("vO2MaxValue")

    # If we have detailed data, use it to fill in missing fields
    if details:
        summary = details.get("summaryDTO", {})

        # Override with more accurate values from details if available
        if not normalized["avg_hr"] and summary.get("averageHR"):
            normalized["avg_hr"] = summary["averageHR"]
        if not normalized["max_hr"] and summary.get("maxHR"):
            normalized["max_hr"] = summary["maxHR"]
        if not normalized["training_effect_aerobic"]:
            normalized["training_effect_aerobic"] = summary.get("trainingEffect")
        if not normalized["vo2max"]:
            normalized["vo2max"] = details.get("vO2MaxValue")

    # Store raw JSON for future analysis
    raw_data = {"activity": activity}
    if details:
        raw_data["details"] = details
    normalized["raw_json"] = json.dumps(raw_data)

    return normalized


def main():
    parser = argparse.ArgumentParser(description="Fetch Garmin Connect activities")
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=10,
        help="Number of activities to fetch (default: 10)"
    )
    parser.add_argument(
        "--since", "-s",
        type=str,
        default=None,
        help="Only fetch activities since this date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Fetch detailed metrics for each activity (slower but more complete)"
    )
    parser.add_argument(
        "--activity-types",
        type=str,
        nargs="*",
        default=["running", "trail_running", "treadmill_running"],
        help="Filter by activity types (default: running types)"
    )

    args = parser.parse_args()

    # Authenticate
    authenticate()

    # Fetch activities
    activities = fetch_activities(args.count, args.since)

    if not activities:
        log("No activities found")
        print(json.dumps([]))
        return

    # Filter by activity type
    if args.activity_types:
        activities = [
            a for a in activities
            if a.get("activityType", {}).get("typeKey") in args.activity_types
        ]
        log(f"Filtered to {len(activities)} activities matching types: {args.activity_types}")

    # Normalize each activity
    results = []
    for i, activity in enumerate(activities):
        activity_id = activity.get("activityId")
        log(f"Processing {i+1}/{len(activities)}: {activity.get('activityName', 'Unknown')}")

        details = None
        if args.details:
            try:
                details = fetch_activity_details(activity_id)
            except Exception as e:
                log(f"  Warning: Could not fetch details: {e}")

        normalized = normalize_activity(activity, details)
        results.append(normalized)

    log(f"Successfully processed {len(results)} activities")

    # Output JSON to stdout (for n8n to capture)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
