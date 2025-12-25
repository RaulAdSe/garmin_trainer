#!/usr/bin/env python3
"""
Training Analyzer CLI.

Fetch and analyze workout data from Garmin Connect.

Usage:
    training fetch              # Fetch recent activities
    training analyze            # Analyze latest workout
"""

import argparse


def main():
    parser = argparse.ArgumentParser(description="Training Analyzer CLI")
    parser.add_argument("command", nargs="?", default="help")

    args = parser.parse_args()

    print("Training Analyzer - Coming Soon!")
    print()
    print("This app will provide:")
    print("  - Per-workout AI coaching")
    print("  - Pace & HR analysis")
    print("  - Training load tracking")
    print("  - Performance trends")


if __name__ == "__main__":
    main()
