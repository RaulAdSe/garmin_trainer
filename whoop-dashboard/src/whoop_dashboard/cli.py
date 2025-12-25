#!/usr/bin/env python3
"""
WHOOP Dashboard CLI.

Fetch wellness data and calculate recovery scores.

Usage:
    whoop fetch              # Fetch today's data
    whoop fetch --days 7     # Backfill 7 days
    whoop show               # Show today's recovery
    whoop stats              # Database stats
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from garmin_client import GarminClient, Database


def calculate_recovery(wellness) -> int:
    """Calculate WHOOP-style recovery score (0-100)."""
    factors = []

    # Body Battery contribution
    if wellness.stress and wellness.stress.body_battery_charged:
        factors.append(wellness.stress.body_battery_charged)

    # HRV contribution
    if wellness.hrv and wellness.hrv.hrv_last_night_avg and wellness.hrv.hrv_weekly_avg:
        hrv_ratio = wellness.hrv.hrv_last_night_avg / wellness.hrv.hrv_weekly_avg
        factors.append(min(100, hrv_ratio * 75 + 25))

    # Sleep contribution
    if wellness.sleep:
        sleep_score = min(100, (wellness.sleep.total_sleep_hours / 8) * 85 +
                         (wellness.sleep.deep_sleep_pct / 20) * 15)
        factors.append(sleep_score)

    if not factors:
        return 0
    return round(sum(factors) / len(factors))


def get_recovery_color(recovery: int) -> str:
    """Get ANSI color for recovery level."""
    if recovery >= 67:
        return "\033[92m"  # Green
    if recovery >= 34:
        return "\033[93m"  # Yellow
    return "\033[91m"  # Red


def cmd_fetch(args):
    """Fetch wellness data."""
    # Token dir in shared folder
    token_dir = Path(__file__).parent.parent.parent.parent / "shared" / ".garth_tokens"
    client = GarminClient(token_dir=token_dir)

    db_path = Path(__file__).parent.parent.parent / "wellness.db"
    db = Database(str(db_path))

    print(f"Database: {db_path}")
    print()

    try:
        client.authenticate()
        print("Authenticated with Garmin Connect\n")
    except Exception as e:
        print(f"Authentication failed: {e}")
        sys.exit(1)

    # Determine dates
    if args.date:
        dates = [args.date]
    else:
        end = datetime.now().date()
        dates = [(end - timedelta(days=i)).isoformat() for i in range(args.days)]

    # Fetch and store
    success = 0
    for date_str in dates:
        try:
            wellness = client.fetch_wellness(date_str)
            db.save_wellness(wellness)
            success += 1
        except Exception as e:
            print(f"  Error: {e}")

    print(f"\nFetched {success}/{len(dates)} days")


def cmd_show(args):
    """Show recovery for a date."""
    db_path = Path(__file__).parent.parent.parent / "wellness.db"
    db = Database(str(db_path))

    date_str = args.date or datetime.now().date().isoformat()
    wellness = db.get_wellness(date_str)

    if not wellness:
        print(f"No data for {date_str}")
        print("Run: whoop fetch")
        sys.exit(1)

    recovery = calculate_recovery(wellness)
    color = get_recovery_color(recovery)
    reset = "\033[0m"

    print()
    print(f"  ╔══════════════════════════════╗")
    print(f"  ║         {date_str}          ║")
    print(f"  ╠══════════════════════════════╣")
    print(f"  ║                              ║")
    print(f"  ║      {color}RECOVERY: {recovery}%{reset}           ║")
    print(f"  ║                              ║")
    print(f"  ╠══════════════════════════════╣")

    if wellness.sleep:
        print(f"  ║  Sleep: {wellness.sleep.total_sleep_hours}h              ║")
        print(f"  ║  Deep: {wellness.sleep.deep_sleep_pct}% | REM: {wellness.sleep.rem_sleep_pct}%    ║")

    if wellness.hrv:
        status = wellness.hrv.hrv_status or "?"
        print(f"  ║  HRV: {wellness.hrv.hrv_last_night_avg}ms ({status})      ║")

    if wellness.stress:
        print(f"  ║  Energy: +{wellness.stress.body_battery_charged} / -{wellness.stress.body_battery_drained}        ║")

    if wellness.activity:
        pct = round(wellness.activity.steps / wellness.activity.steps_goal * 100)
        print(f"  ║  Steps: {wellness.activity.steps} ({pct}%)        ║")

    print(f"  ╚══════════════════════════════╝")
    print()


def cmd_stats(args):
    """Show database stats."""
    db_path = Path(__file__).parent.parent.parent / "wellness.db"
    db = Database(str(db_path))
    stats = db.get_stats()

    print(f"Database: {stats['db_path']}")
    print(f"Total days: {stats['total_days']}")
    if stats['earliest_date']:
        print(f"Date range: {stats['earliest_date']} to {stats['latest_date']}")


def main():
    parser = argparse.ArgumentParser(description="WHOOP Dashboard CLI")

    subparsers = parser.add_subparsers(dest="command")

    # Fetch
    fetch_p = subparsers.add_parser("fetch", help="Fetch wellness data")
    fetch_p.add_argument("--date", "-d", help="Specific date (YYYY-MM-DD)")
    fetch_p.add_argument("--days", "-n", type=int, default=1, help="Days to fetch")

    # Show
    show_p = subparsers.add_parser("show", help="Show recovery")
    show_p.add_argument("--date", "-d", help="Date to show")

    # Stats
    subparsers.add_parser("stats", help="Database stats")

    args = parser.parse_args()

    if args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "stats":
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
