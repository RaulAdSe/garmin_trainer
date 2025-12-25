"""Garmin Connect API client using garth library."""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List

import garth

from garmin_client.db.models import (
    DailyWellness, SleepData, HRVData, StressData, ActivityData
)


class GarminClient:
    """Client for fetching wellness data from Garmin Connect."""

    def __init__(self, token_dir: Optional[Path] = None):
        """Initialize the client.

        Args:
            token_dir: Directory to store authentication tokens.
                      Defaults to ~/.garmin_tokens
        """
        self.token_dir = token_dir or Path.home() / ".garmin_tokens"
        self._authenticated = False

    def authenticate(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        """Authenticate with Garmin Connect.

        Will try to resume existing session first, then fall back to
        fresh login if needed.

        Args:
            email: Garmin account email (or GARMIN_EMAIL env var)
            password: Garmin account password (or GARMIN_PASSWORD env var)

        Returns:
            True if authentication successful
        """
        email = email or os.environ.get("GARMIN_EMAIL")
        password = password or os.environ.get("GARMIN_PASSWORD")

        # Try to resume existing session
        if self.token_dir.exists():
            try:
                garth.resume(self.token_dir)
                # Verify session is still valid
                garth.connectapi("/userprofile-service/socialProfile")
                self._authenticated = True
                return True
            except Exception:
                pass  # Session expired, try fresh login

        # Fresh authentication
        if not email or not password:
            raise ValueError(
                "GARMIN_EMAIL and GARMIN_PASSWORD environment variables required"
            )

        try:
            garth.login(email, password)
            self.token_dir.mkdir(parents=True, exist_ok=True)
            garth.save(self.token_dir)
            self._authenticated = True
            return True
        except Exception as e:
            raise RuntimeError(f"Authentication failed: {e}")

    def _ensure_authenticated(self):
        """Ensure client is authenticated."""
        if not self._authenticated:
            self.authenticate()

    def fetch_sleep(self, date_str: str) -> Optional[SleepData]:
        """Fetch sleep data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            SleepData object or None if not available
        """
        self._ensure_authenticated()

        try:
            data = garth.connectapi(
                f"/wellness-service/wellness/dailySleep?date={date_str}"
            )

            if not data:
                return None

            # Extract sleep stages
            deep = data.get("deepSleepSeconds", 0) or 0
            light = data.get("lightSleepSeconds", 0) or 0
            rem = data.get("remSleepSeconds", 0) or 0
            awake = data.get("awakeSleepSeconds", 0) or 0
            total = deep + light + rem

            # Calculate efficiency
            total_in_bed = total + awake
            efficiency = (total / total_in_bed * 100) if total_in_bed > 0 else 0

            return SleepData(
                date=date_str,
                sleep_start=data.get("sleepStartTimestampLocal"),
                sleep_end=data.get("sleepEndTimestampLocal"),
                total_sleep_seconds=total,
                deep_sleep_seconds=deep,
                light_sleep_seconds=light,
                rem_sleep_seconds=rem,
                awake_seconds=awake,
                sleep_score=data.get("sleepScores", {}).get("overall", {}).get("value"),
                sleep_efficiency=round(efficiency, 1),
                avg_spo2=data.get("avgOxygenSaturation"),
                avg_respiration=data.get("avgSleepRespirationValue"),
            )
        except Exception as e:
            print(f"  Warning: Could not fetch sleep data: {e}")
            return None

    def fetch_hrv(self, date_str: str) -> Optional[HRVData]:
        """Fetch HRV data for a specific date."""
        self._ensure_authenticated()

        try:
            data = garth.connectapi(f"/hrv-service/hrv/{date_str}")

            if not data:
                return None

            summary = data.get("hrvSummary", {})
            baseline = summary.get("baseline", {})

            return HRVData(
                date=date_str,
                hrv_weekly_avg=summary.get("weeklyAvg"),
                hrv_last_night_avg=summary.get("lastNightAvg"),
                hrv_last_night_5min_high=summary.get("lastNight5MinHigh"),
                hrv_status=summary.get("status"),
                baseline_low=baseline.get("lowUpper"),
                baseline_balanced_low=baseline.get("balancedLow"),
                baseline_balanced_upper=baseline.get("balancedUpper"),
            )
        except Exception as e:
            print(f"  Warning: Could not fetch HRV data: {e}")
            return None

    def fetch_stress(self, date_str: str) -> Optional[StressData]:
        """Fetch stress and body battery data for a specific date."""
        self._ensure_authenticated()

        stress_data = None
        bb_data = None

        # Fetch stress data
        try:
            stress_data = garth.connectapi(
                f"/wellness-service/wellness/dailyStress/{date_str}"
            )
        except Exception as e:
            print(f"  Warning: Could not fetch stress data: {e}")

        # Fetch body battery data
        try:
            bb_result = garth.connectapi(
                f"/wellness-service/wellness/bodyBattery/reports/daily"
                f"?startDate={date_str}&endDate={date_str}"
            )
            if bb_result and len(bb_result) > 0:
                bb_data = bb_result[0]
        except Exception as e:
            print(f"  Warning: Could not fetch body battery data: {e}")

        if not stress_data and not bb_data:
            return None

        return StressData(
            date=date_str,
            avg_stress_level=stress_data.get("overallStressLevel") if stress_data else None,
            max_stress_level=stress_data.get("maxStressLevel") if stress_data else None,
            rest_stress_duration=stress_data.get("restStressDuration", 0) if stress_data else 0,
            low_stress_duration=stress_data.get("lowStressDuration", 0) if stress_data else 0,
            medium_stress_duration=stress_data.get("mediumStressDuration", 0) if stress_data else 0,
            high_stress_duration=stress_data.get("highStressDuration", 0) if stress_data else 0,
            body_battery_charged=bb_data.get("charged") if bb_data else None,
            body_battery_drained=bb_data.get("drained") if bb_data else None,
            body_battery_high=bb_data.get("highBB") if bb_data else None,
            body_battery_low=bb_data.get("lowBB") if bb_data else None,
        )

    def fetch_activity(self, date_str: str) -> Optional[ActivityData]:
        """Fetch daily activity data (steps, calories, etc.)."""
        self._ensure_authenticated()

        try:
            # Fetch steps data
            steps_data = garth.connectapi(
                f"/usersummary-service/stats/steps/daily/{date_str}/{date_str}"
            )

            if not steps_data or len(steps_data) == 0:
                return None

            day_data = steps_data[0]

            return ActivityData(
                date=date_str,
                steps=day_data.get("totalSteps", 0),
                steps_goal=day_data.get("stepGoal", 10000),
                total_distance_m=day_data.get("totalDistance", 0),
                # Note: active_calories and intensity_minutes may need different endpoints
            )
        except Exception as e:
            print(f"  Warning: Could not fetch activity data: {e}")
            return None

    def fetch_wellness(self, date_str: str) -> DailyWellness:
        """Fetch all wellness data for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            DailyWellness object with all available metrics
        """
        self._ensure_authenticated()

        print(f"Fetching wellness data for {date_str}...")

        # Fetch all data sources
        sleep = self.fetch_sleep(date_str)
        hrv = self.fetch_hrv(date_str)
        stress = self.fetch_stress(date_str)
        activity = self.fetch_activity(date_str)

        # Build raw JSON for debugging
        raw_data = {
            "sleep": sleep.to_dict() if sleep else None,
            "hrv": hrv.to_dict() if hrv else None,
            "stress": stress.to_dict() if stress else None,
            "activity": activity.to_dict() if activity else None,
        }

        wellness = DailyWellness(
            date=date_str,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            sleep=sleep,
            hrv=hrv,
            stress=stress,
            activity=activity,
            raw_json=json.dumps(raw_data),
        )

        # Print summary
        sleep_hours = sleep.total_sleep_hours if sleep else "?"
        steps = activity.steps if activity else "?"
        bb = stress.body_battery_charged if stress else "?"
        hrv_val = hrv.hrv_last_night_avg if hrv else "?"

        print(f"  Sleep: {sleep_hours}h | Steps: {steps} | BB: +{bb} | HRV: {hrv_val}ms")

        return wellness

    def fetch_training_readiness(self, date_str: str) -> Optional[dict]:
        """Fetch Garmin's Training Readiness score (0-100).

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Dict with score (0-100), level (LOW/FAIR/GOOD/PRIME), and feedback factors
            or None if not available
        """
        self._ensure_authenticated()

        try:
            data = garth.connectapi(f"/metrics-service/metrics/trainingreadiness/{date_str}")

            if not data:
                return None

            return {
                "date": date_str,
                "score": data.get("score"),
                "level": data.get("level"),  # LOW, FAIR, GOOD, PRIME
                "hrv_feedback": data.get("hrvFeedback"),
                "sleep_feedback": data.get("sleepFeedback"),
                "recovery_feedback": data.get("recoveryTimeFeedback"),
                "acclimation_feedback": data.get("acclimationFeedback"),
                "primary_feedback": data.get("primaryFeedback"),
            }
        except Exception as e:
            print(f"  Warning: Could not fetch training readiness: {e}")
            return None

    def fetch_sleep_need(self, date_str: str) -> Optional[dict]:
        """Fetch personalized sleep need based on strain.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Dict with baselineSleepNeed, recommendedSleepNeed (in seconds)
            or None if not available
        """
        self._ensure_authenticated()

        try:
            data = garth.connectapi(f"/wellness-service/wellness/sleepNeed/{date_str}")

            if not data:
                return None

            return {
                "date": date_str,
                "baseline_sleep_need_seconds": data.get("baselineSleepNeedSeconds"),
                "recommended_sleep_need_seconds": data.get("recommendedSleepNeedSeconds"),
                "sleep_debt_seconds": data.get("sleepDebtSeconds"),
            }
        except Exception as e:
            print(f"  Warning: Could not fetch sleep need: {e}")
            return None

    def fetch_respiration(self, date_str: str) -> Optional[dict]:
        """Fetch overnight respiration data.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Dict with respiration metrics or None if not available
        """
        self._ensure_authenticated()

        try:
            data = garth.connectapi(f"/wellness-service/wellness/dailyRespirationData/{date_str}")

            if not data:
                return None

            return {
                "date": date_str,
                "avg_waking_respiration": data.get("avgWakingRespirationValue"),
                "avg_sleep_respiration": data.get("avgSleepRespirationValue"),
                "highest_respiration": data.get("highestRespirationValue"),
                "lowest_respiration": data.get("lowestRespirationValue"),
            }
        except Exception as e:
            print(f"  Warning: Could not fetch respiration data: {e}")
            return None

    def fetch_wellness_range(
        self,
        days: int = 7,
        end_date: Optional[str] = None,
    ) -> List[DailyWellness]:
        """Fetch wellness data for multiple days.

        Args:
            days: Number of days to fetch
            end_date: End date (defaults to today)

        Returns:
            List of DailyWellness objects
        """
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end = datetime.now().date()

        results = []
        for i in range(days):
            date_str = (end - timedelta(days=i)).isoformat()
            try:
                wellness = self.fetch_wellness(date_str)
                results.append(wellness)
            except Exception as e:
                print(f"  Error fetching {date_str}: {e}")

        return results
