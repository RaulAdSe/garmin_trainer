#!/usr/bin/env python3
"""
Test Garmin Connect API connection using garth library.

Authenticates with Garmin Connect, fetches recent activities,
and prints the JSON structure to inspect available fields.

Usage:
    export GARMIN_EMAIL="your@email.com"
    export GARMIN_PASSWORD="yourpassword"
    python test_connection.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import garth

# Token storage path (relative to script directory)
TOKEN_DIR = Path(__file__).parent / ".garth_tokens"


def authenticate():
    """Authenticate with Garmin Connect and save tokens."""
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")

    if not email or not password:
        print("Error: GARMIN_EMAIL and GARMIN_PASSWORD environment variables required")
        sys.exit(1)

    # Try to load existing tokens first
    if TOKEN_DIR.exists():
        try:
            garth.resume(TOKEN_DIR)
            print(f"Resumed session from saved tokens")
            return
        except Exception as e:
            print(f"Could not resume session: {e}")
            print("Authenticating fresh...")

    # Fresh authentication
    try:
        garth.login(email, password)
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        garth.save(TOKEN_DIR)
        print("Authentication successful! Tokens saved.")
    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)


def fetch_activities(count=5):
    """Fetch recent activities from Garmin Connect."""
    print(f"\nFetching {count} most recent activities...")

    # Get activities list
    activities = garth.connectapi(
        f"/activitylist-service/activities/search/activities",
        params={"limit": count, "start": 0}
    )

    return activities


def fetch_activity_details(activity_id):
    """Fetch detailed data for a specific activity."""
    details = garth.connectapi(f"/activity-service/activity/{activity_id}")
    return details


def main():
    print("=" * 60)
    print("Garmin Connect API Test")
    print("=" * 60)

    # Authenticate
    authenticate()

    # Fetch activities
    activities = fetch_activities(5)

    if not activities:
        print("No activities found.")
        return

    print(f"\nFound {len(activities)} activities:\n")

    for i, activity in enumerate(activities, 1):
        activity_id = activity.get("activityId")
        name = activity.get("activityName", "Unnamed")
        activity_type = activity.get("activityType", {}).get("typeKey", "unknown")
        start_time = activity.get("startTimeLocal", "")
        distance = activity.get("distance", 0) / 1000  # meters to km
        duration = activity.get("duration", 0) / 60  # seconds to minutes

        print(f"{i}. [{activity_type}] {name}")
        print(f"   Date: {start_time}")
        print(f"   Distance: {distance:.2f} km | Duration: {duration:.1f} min")
        print(f"   Activity ID: {activity_id}")
        print()

    # Fetch detailed data for the most recent activity
    print("=" * 60)
    print("Detailed JSON for most recent activity:")
    print("=" * 60)

    latest_id = activities[0].get("activityId")
    details = fetch_activity_details(latest_id)

    # Pretty print the full JSON
    print(json.dumps(details, indent=2, default=str))

    # Summary of available fields
    print("\n" + "=" * 60)
    print("Available top-level fields in activity detail:")
    print("=" * 60)
    for key in sorted(details.keys()):
        value = details[key]
        value_type = type(value).__name__
        if isinstance(value, dict):
            print(f"  {key}: dict with {len(value)} keys")
        elif isinstance(value, list):
            print(f"  {key}: list with {len(value)} items")
        else:
            print(f"  {key}: {value_type}")


if __name__ == "__main__":
    main()
