"""Causality engine - learns YOUR patterns to surface actionable correlations.

This module implements Phase 4 of the WHOOP-style dashboard vision:
- Correlation detection (workout timing vs recovery)
- Pattern recognition (what improves YOUR recovery)
- Streak tracking (green days, sleep consistency)
- Trend alerts (HRV declining for 3+ days)

Key philosophy: Surface YOUR patterns, not generic advice.
"Late workouts correlate with -18% recovery next day" is personal and actionable.
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
import sqlite3


@dataclass
class Correlation:
    """A detected correlation in your data."""
    pattern_type: str  # 'negative' or 'positive'
    category: str  # 'sleep', 'workout', 'recovery', 'stress'
    title: str  # Short title
    description: str  # Detailed description with YOUR numbers
    impact: float  # Percentage impact (e.g., -18 or +12)
    confidence: float  # 0-1 based on sample size
    sample_size: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Streak:
    """A streak tracking achievement."""
    name: str
    current_count: int
    best_count: int
    is_active: bool
    last_date: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrendAlert:
    """An alert when metrics trend in concerning direction."""
    metric: str
    direction: str  # 'declining', 'improving'
    days: int  # How many days trending
    change_pct: float
    severity: str  # 'warning', 'concern', 'positive'

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WeeklySummary:
    """Comprehensive weekly behavioral summary."""
    green_days: int
    yellow_days: int
    red_days: int
    avg_recovery: float
    avg_strain: float
    avg_sleep: float
    total_sleep_debt: float
    best_day: str  # Date of highest recovery
    worst_day: str  # Date of lowest recovery
    correlations: List[Correlation]
    streaks: List[Streak]
    trend_alerts: List[TrendAlert]

    def to_dict(self) -> dict:
        return {
            'green_days': self.green_days,
            'yellow_days': self.yellow_days,
            'red_days': self.red_days,
            'avg_recovery': self.avg_recovery,
            'avg_strain': self.avg_strain,
            'avg_sleep': self.avg_sleep,
            'total_sleep_debt': self.total_sleep_debt,
            'best_day': self.best_day,
            'worst_day': self.worst_day,
            'correlations': [c.to_dict() for c in self.correlations],
            'streaks': [s.to_dict() for s in self.streaks],
            'trend_alerts': [t.to_dict() for t in self.trend_alerts],
        }


# Minimum sample sizes for confidence
MIN_SAMPLES_FOR_CORRELATION = 5
MIN_SAMPLES_FOR_HIGH_CONFIDENCE = 10


def _calculate_recovery(
    hrv: Optional[float],
    hrv_baseline: Optional[float],
    sleep_hours: Optional[float],
    sleep_baseline: Optional[float],
    body_battery: Optional[float]
) -> int:
    """Calculate recovery score from metrics."""
    scores = []
    weights = []

    if hrv is not None and hrv_baseline is not None and hrv_baseline > 0:
        hrv_ratio = hrv / hrv_baseline
        hrv_score = min(100, max(0, hrv_ratio * 80 + 20))
        scores.append(hrv_score * 1.5)
        weights.append(1.5)

    if sleep_hours is not None and sleep_baseline is not None and sleep_baseline > 0:
        sleep_ratio = sleep_hours / sleep_baseline
        sleep_score = min(100, max(0, sleep_ratio * 85 + 15))
        scores.append(sleep_score)
        weights.append(1.0)

    if body_battery is not None:
        scores.append(body_battery)
        weights.append(1.0)

    if not scores:
        return 0

    total_weight = sum(weights)
    weighted_sum = sum(scores)
    return round(weighted_sum / total_weight)


def _calculate_strain(
    body_battery_drained: Optional[int],
    steps: Optional[int],
    intensity_minutes: Optional[int]
) -> float:
    """Calculate strain score from activity data."""
    strain = 0.0

    if steps is not None:
        strain += min(8, steps / 2000)

    if body_battery_drained is not None:
        strain += min(8, body_battery_drained / 12)

    if intensity_minutes is not None:
        strain += min(5, intensity_minutes / 20)

    return round(min(21, strain), 1)


def _get_rolling_average(values: List[Optional[float]], days: int = 7) -> Optional[float]:
    """Calculate rolling average excluding None values."""
    valid = [v for v in values[:days] if v is not None]
    if len(valid) < 3:
        return None
    return sum(valid) / len(valid)


def detect_workout_timing_correlation(db_path: str, days: int = 30) -> Optional[Correlation]:
    """Detect if late workouts affect next-day recovery.

    Compare recovery after workouts ending before 6pm vs after 8pm.
    This uses body battery drain as a proxy for workout intensity.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # Get data for the past N days with next-day recovery
        rows = conn.execute("""
            SELECT
                d1.date as workout_date,
                st1.body_battery_drained as strain,
                st1.high_stress_duration as high_stress,
                h2.hrv_last_night_avg as next_hrv,
                st2.body_battery_charged as next_bb,
                s2.total_sleep_seconds as next_sleep
            FROM stress_data st1
            JOIN stress_data st2 ON date(st1.date, '+1 day') = st2.date
            LEFT JOIN daily_wellness d1 ON st1.date = d1.date
            LEFT JOIN hrv_data h2 ON st2.date = h2.date
            LEFT JOIN sleep_data s2 ON st2.date = s2.date
            WHERE st1.date >= date('now', ?)
            AND st1.body_battery_drained > 40  -- Only count significant activity days
            ORDER BY st1.date DESC
        """, (f'-{days} days',)).fetchall()

        if len(rows) < MIN_SAMPLES_FOR_CORRELATION:
            return None

        # Split into high-stress evening (proxy for late workout) vs normal
        # High stress duration in evening = likely late workout
        late_workout_recoveries = []
        early_workout_recoveries = []

        for row in rows:
            # Calculate next-day recovery
            next_sleep_hours = row['next_sleep'] / 3600 if row['next_sleep'] else None
            recovery = _calculate_recovery(
                row['next_hrv'], None, next_sleep_hours, 7.5, row['next_bb']
            )
            if recovery == 0:
                continue

            # High stress duration > 2 hours suggests late activity
            if row['high_stress'] and row['high_stress'] > 7200:  # > 2 hours
                late_workout_recoveries.append(recovery)
            elif row['high_stress'] and row['high_stress'] < 3600:  # < 1 hour
                early_workout_recoveries.append(recovery)

        if len(late_workout_recoveries) < 3 or len(early_workout_recoveries) < 3:
            return None

        avg_late = sum(late_workout_recoveries) / len(late_workout_recoveries)
        avg_early = sum(early_workout_recoveries) / len(early_workout_recoveries)

        if avg_early == 0:
            return None

        impact = ((avg_late - avg_early) / avg_early) * 100

        # Only report if significant impact (> 8%)
        if abs(impact) < 8:
            return None

        sample_size = len(late_workout_recoveries) + len(early_workout_recoveries)
        confidence = min(1.0, sample_size / MIN_SAMPLES_FOR_HIGH_CONFIDENCE)

        if impact < 0:
            return Correlation(
                pattern_type='negative',
                category='workout',
                title='Late workout impact',
                description=f"High-stress evenings correlate with {impact:.0f}% lower recovery next day",
                impact=round(impact, 1),
                confidence=round(confidence, 2),
                sample_size=sample_size
            )
        else:
            return Correlation(
                pattern_type='positive',
                category='workout',
                title='Evening activity boost',
                description=f"Active evenings correlate with +{impact:.0f}% better recovery",
                impact=round(impact, 1),
                confidence=round(confidence, 2),
                sample_size=sample_size
            )

    finally:
        conn.close()


def detect_sleep_consistency_impact(db_path: str, days: int = 30) -> Optional[Correlation]:
    """Detect impact of consistent sleep on HRV baseline.

    Compare HRV when 5+ days of 7h+ sleep vs inconsistent sleep.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT
                s.date,
                s.total_sleep_seconds / 3600.0 as sleep_hours,
                h.hrv_last_night_avg as hrv
            FROM sleep_data s
            LEFT JOIN hrv_data h ON s.date = h.date
            WHERE s.date >= date('now', ?)
            AND h.hrv_last_night_avg IS NOT NULL
            ORDER BY s.date DESC
        """, (f'-{days} days',)).fetchall()

        if len(rows) < 10:
            return None

        # Find periods of consistent 7h+ sleep (5+ days) and their HRV
        consistent_hrvs = []
        inconsistent_hrvs = []

        for i in range(len(rows) - 4):
            # Look at 5-day windows
            window = rows[i:i+5]
            window_sleep = [r['sleep_hours'] for r in window if r['sleep_hours'] is not None]

            if len(window_sleep) < 5:
                continue

            hrv = rows[i]['hrv']
            if hrv is None:
                continue

            # Check if all 5 days have 7+ hours
            if all(s >= 7.0 for s in window_sleep):
                consistent_hrvs.append(hrv)
            elif any(s < 6.0 for s in window_sleep):  # At least one bad night
                inconsistent_hrvs.append(hrv)

        if len(consistent_hrvs) < 3 or len(inconsistent_hrvs) < 3:
            return None

        avg_consistent = sum(consistent_hrvs) / len(consistent_hrvs)
        avg_inconsistent = sum(inconsistent_hrvs) / len(inconsistent_hrvs)

        if avg_inconsistent == 0:
            return None

        impact = ((avg_consistent - avg_inconsistent) / avg_inconsistent) * 100

        if abs(impact) < 5:
            return None

        sample_size = len(consistent_hrvs) + len(inconsistent_hrvs)
        confidence = min(1.0, sample_size / MIN_SAMPLES_FOR_HIGH_CONFIDENCE)

        return Correlation(
            pattern_type='positive' if impact > 0 else 'negative',
            category='sleep',
            title='Sleep consistency impact',
            description=f"5+ days of 7h+ sleep: HRV baseline {'up' if impact > 0 else 'down'} {abs(impact):.0f}%",
            impact=round(impact, 1),
            confidence=round(confidence, 2),
            sample_size=sample_size
        )

    finally:
        conn.close()


def detect_step_count_correlation(db_path: str, days: int = 30) -> Optional[Correlation]:
    """Detect if high step days correlate with better recovery."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT
                a.date,
                a.steps,
                h2.hrv_last_night_avg as next_hrv,
                st2.body_battery_charged as next_bb,
                s2.total_sleep_seconds as next_sleep
            FROM activity_data a
            JOIN hrv_data h2 ON date(a.date, '+1 day') = h2.date
            LEFT JOIN stress_data st2 ON date(a.date, '+1 day') = st2.date
            LEFT JOIN sleep_data s2 ON date(a.date, '+1 day') = s2.date
            WHERE a.date >= date('now', ?)
            AND a.steps IS NOT NULL
            ORDER BY a.date DESC
        """, (f'-{days} days',)).fetchall()

        if len(rows) < MIN_SAMPLES_FOR_CORRELATION:
            return None

        high_step_recoveries = []
        low_step_recoveries = []
        step_threshold = 8000

        for row in rows:
            next_sleep_hours = row['next_sleep'] / 3600 if row['next_sleep'] else None
            recovery = _calculate_recovery(
                row['next_hrv'], None, next_sleep_hours, 7.5, row['next_bb']
            )
            if recovery == 0:
                continue

            if row['steps'] >= step_threshold:
                high_step_recoveries.append(recovery)
            elif row['steps'] < 5000:
                low_step_recoveries.append(recovery)

        if len(high_step_recoveries) < 3 or len(low_step_recoveries) < 3:
            return None

        avg_high = sum(high_step_recoveries) / len(high_step_recoveries)
        avg_low = sum(low_step_recoveries) / len(low_step_recoveries)

        if avg_low == 0:
            return None

        impact = ((avg_high - avg_low) / avg_low) * 100

        if abs(impact) < 5:
            return None

        sample_size = len(high_step_recoveries) + len(low_step_recoveries)
        confidence = min(1.0, sample_size / MIN_SAMPLES_FOR_HIGH_CONFIDENCE)

        return Correlation(
            pattern_type='positive' if impact > 0 else 'negative',
            category='activity',
            title=f'{step_threshold // 1000}k+ step days',
            description=f"High step days ({step_threshold // 1000}k+) correlate with {'+' if impact > 0 else ''}{impact:.0f}% recovery",
            impact=round(impact, 1),
            confidence=round(confidence, 2),
            sample_size=sample_size
        )

    finally:
        conn.close()


def detect_alcohol_nights(db_path: str, days: int = 30) -> Optional[Correlation]:
    """Detect alcohol/stress impact via sudden HRV crashes (>20% below baseline).

    HRV crashes without correspondingly high strain = likely alcohol or stress.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT
                h.date,
                h.hrv_last_night_avg as hrv,
                st.body_battery_drained as drain,
                st.body_battery_charged as bb_charged,
                s.total_sleep_seconds / 3600.0 as sleep_hours
            FROM hrv_data h
            LEFT JOIN stress_data st ON h.date = st.date
            LEFT JOIN sleep_data s ON h.date = s.date
            WHERE h.date >= date('now', ?)
            AND h.hrv_last_night_avg IS NOT NULL
            ORDER BY h.date DESC
        """, (f'-{days} days',)).fetchall()

        if len(rows) < 10:
            return None

        # Calculate HRV baseline
        hrvs = [r['hrv'] for r in rows if r['hrv'] is not None]
        if len(hrvs) < 7:
            return None

        hrv_baseline = sum(hrvs[:14]) / min(14, len(hrvs))

        crash_nights = []  # HRV crash without high strain
        normal_nights = []

        for row in rows:
            if row['hrv'] is None:
                continue

            hrv_deviation = (row['hrv'] - hrv_baseline) / hrv_baseline * 100

            # HRV crash > 20% below baseline
            if hrv_deviation < -20:
                # Check if it's NOT due to high activity
                drain = row['drain'] or 0
                if drain < 60:  # Low strain day - likely alcohol/stress
                    crash_nights.append({
                        'hrv': row['hrv'],
                        'bb': row['bb_charged'],
                        'sleep': row['sleep_hours']
                    })
            elif -10 < hrv_deviation < 10:  # Normal nights
                normal_nights.append({
                    'hrv': row['hrv'],
                    'bb': row['bb_charged'],
                    'sleep': row['sleep_hours']
                })

        if len(crash_nights) < 2 or len(normal_nights) < 3:
            return None

        # Compare recovery on crash nights vs normal
        crash_recoveries = [n['bb'] for n in crash_nights if n['bb'] is not None]
        normal_recoveries = [n['bb'] for n in normal_nights if n['bb'] is not None]

        if not crash_recoveries or not normal_recoveries:
            return None

        avg_crash = sum(crash_recoveries) / len(crash_recoveries)
        avg_normal = sum(normal_recoveries) / len(normal_recoveries)

        if avg_normal == 0:
            return None

        impact = ((avg_crash - avg_normal) / avg_normal) * 100

        sample_size = len(crash_nights)
        confidence = min(1.0, sample_size / MIN_SAMPLES_FOR_HIGH_CONFIDENCE)

        return Correlation(
            pattern_type='negative',
            category='stress',
            title='HRV crash nights',
            description=f"Nights with HRV crashes (low activity days): recovery drops {abs(impact):.0f}%",
            impact=round(impact, 1),
            confidence=round(confidence, 2),
            sample_size=sample_size
        )

    finally:
        conn.close()


def get_all_correlations(db_path: str) -> List[Correlation]:
    """Get all detected correlations for the user."""
    correlations = []

    # Try each detector and collect valid correlations
    detectors = [
        detect_workout_timing_correlation,
        detect_sleep_consistency_impact,
        detect_step_count_correlation,
        detect_alcohol_nights,
    ]

    for detector in detectors:
        try:
            correlation = detector(db_path)
            if correlation is not None:
                correlations.append(correlation)
        except Exception:
            # Skip failed detectors
            pass

    # Sort by confidence (highest first)
    correlations.sort(key=lambda c: c.confidence, reverse=True)

    return correlations


# Streak tracking

def calculate_green_day_streak(db_path: str) -> Streak:
    """Track consecutive days in green recovery zone (67%+)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT
                h.date,
                h.hrv_last_night_avg as hrv,
                st.body_battery_charged as bb,
                s.total_sleep_seconds / 3600.0 as sleep_hours
            FROM hrv_data h
            LEFT JOIN stress_data st ON h.date = st.date
            LEFT JOIN sleep_data s ON h.date = s.date
            WHERE h.date >= date('now', '-60 days')
            ORDER BY h.date DESC
        """).fetchall()

        if not rows:
            return Streak(
                name='green_days',
                current_count=0,
                best_count=0,
                is_active=False,
                last_date=''
            )

        # Calculate recovery for each day and track streaks
        current_streak = 0
        best_streak = 0
        last_date = ''
        is_active = False
        in_streak = True  # Start checking from most recent

        # Get HRV baseline (7-day)
        hrvs = [r['hrv'] for r in rows if r['hrv'] is not None]
        hrv_baseline = sum(hrvs[:7]) / len(hrvs[:7]) if len(hrvs) >= 3 else None

        sleeps = [r['sleep_hours'] for r in rows if r['sleep_hours'] is not None]
        sleep_baseline = sum(sleeps[:7]) / len(sleeps[:7]) if len(sleeps) >= 3 else 7.5

        for row in rows:
            recovery = _calculate_recovery(
                row['hrv'], hrv_baseline,
                row['sleep_hours'], sleep_baseline,
                row['bb']
            )

            is_green = recovery >= 67

            if in_streak and is_green:
                current_streak += 1
                if current_streak == 1:
                    last_date = row['date']
            elif in_streak and not is_green:
                in_streak = False
                if current_streak > 0:
                    is_active = True

            # Track best streak
            if is_green:
                temp_streak = 1
                for next_row in rows[rows.index(row)+1:]:
                    next_recovery = _calculate_recovery(
                        next_row['hrv'], hrv_baseline,
                        next_row['sleep_hours'], sleep_baseline,
                        next_row['bb']
                    )
                    if next_recovery >= 67:
                        temp_streak += 1
                    else:
                        break
                best_streak = max(best_streak, temp_streak)

        return Streak(
            name='green_days',
            current_count=current_streak,
            best_count=best_streak,
            is_active=is_active and current_streak > 0,
            last_date=last_date
        )

    finally:
        conn.close()


def calculate_sleep_consistency_streak(db_path: str, threshold_hours: float = 7.0) -> Streak:
    """Track consecutive days meeting sleep target."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT date, total_sleep_seconds / 3600.0 as sleep_hours
            FROM sleep_data
            WHERE date >= date('now', '-60 days')
            AND total_sleep_seconds IS NOT NULL
            ORDER BY date DESC
        """).fetchall()

        if not rows:
            return Streak(
                name='sleep_consistency',
                current_count=0,
                best_count=0,
                is_active=False,
                last_date=''
            )

        current_streak = 0
        best_streak = 0
        last_date = ''
        is_active = False
        in_streak = True

        for i, row in enumerate(rows):
            meets_target = row['sleep_hours'] >= threshold_hours

            if in_streak and meets_target:
                current_streak += 1
                if current_streak == 1:
                    last_date = row['date']
            elif in_streak and not meets_target:
                in_streak = False
                if current_streak > 0:
                    is_active = True

            # Track best streak starting from this point
            if meets_target:
                temp_streak = 1
                for next_row in rows[i+1:]:
                    if next_row['sleep_hours'] >= threshold_hours:
                        temp_streak += 1
                    else:
                        break
                best_streak = max(best_streak, temp_streak)

        return Streak(
            name='sleep_consistency',
            current_count=current_streak,
            best_count=best_streak,
            is_active=is_active and current_streak > 0,
            last_date=last_date
        )

    finally:
        conn.close()


def calculate_step_goal_streak(db_path: str) -> Streak:
    """Track consecutive days hitting step goal."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT date, steps, steps_goal
            FROM activity_data
            WHERE date >= date('now', '-60 days')
            AND steps IS NOT NULL
            ORDER BY date DESC
        """).fetchall()

        if not rows:
            return Streak(
                name='step_goal',
                current_count=0,
                best_count=0,
                is_active=False,
                last_date=''
            )

        current_streak = 0
        best_streak = 0
        last_date = ''
        is_active = False
        in_streak = True

        for i, row in enumerate(rows):
            goal = row['steps_goal'] or 10000
            hit_goal = row['steps'] >= goal

            if in_streak and hit_goal:
                current_streak += 1
                if current_streak == 1:
                    last_date = row['date']
            elif in_streak and not hit_goal:
                in_streak = False
                if current_streak > 0:
                    is_active = True

            # Track best streak
            if hit_goal:
                temp_streak = 1
                for next_row in rows[i+1:]:
                    next_goal = next_row['steps_goal'] or 10000
                    if next_row['steps'] >= next_goal:
                        temp_streak += 1
                    else:
                        break
                best_streak = max(best_streak, temp_streak)

        return Streak(
            name='step_goal',
            current_count=current_streak,
            best_count=best_streak,
            is_active=is_active and current_streak > 0,
            last_date=last_date
        )

    finally:
        conn.close()


def get_all_streaks(db_path: str) -> List[Streak]:
    """Get all streak tracking data."""
    streaks = []

    try:
        streaks.append(calculate_green_day_streak(db_path))
    except Exception:
        pass

    try:
        streaks.append(calculate_sleep_consistency_streak(db_path))
    except Exception:
        pass

    try:
        streaks.append(calculate_step_goal_streak(db_path))
    except Exception:
        pass

    # Filter to only active streaks with count > 0
    return [s for s in streaks if s.current_count > 0]


# Trend alerts

def detect_hrv_trend(db_path: str, days: int = 7) -> Optional[TrendAlert]:
    """Alert if HRV declining for 3+ days."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT date, hrv_last_night_avg as hrv
            FROM hrv_data
            WHERE date >= date('now', ?)
            AND hrv_last_night_avg IS NOT NULL
            ORDER BY date DESC
        """, (f'-{days} days',)).fetchall()

        if len(rows) < 3:
            return None

        # Check for consistent decline/improvement
        declining_days = 0
        improving_days = 0
        first_hrv = rows[0]['hrv']
        last_hrv = rows[-1]['hrv'] if rows else first_hrv

        for i in range(len(rows) - 1):
            if rows[i]['hrv'] < rows[i+1]['hrv']:
                declining_days += 1
            elif rows[i]['hrv'] > rows[i+1]['hrv']:
                improving_days += 1

        # Calculate overall change
        if last_hrv == 0:
            return None

        change_pct = ((first_hrv - last_hrv) / last_hrv) * 100

        if declining_days >= 3 and change_pct < -10:
            return TrendAlert(
                metric='HRV',
                direction='declining',
                days=declining_days,
                change_pct=round(change_pct, 1),
                severity='concern' if change_pct < -15 else 'warning'
            )
        elif improving_days >= 3 and change_pct > 10:
            return TrendAlert(
                metric='HRV',
                direction='improving',
                days=improving_days,
                change_pct=round(change_pct, 1),
                severity='positive'
            )

        return None

    finally:
        conn.close()


def detect_sleep_trend(db_path: str, days: int = 7) -> Optional[TrendAlert]:
    """Alert if sleep duration declining."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT date, total_sleep_seconds / 3600.0 as sleep_hours
            FROM sleep_data
            WHERE date >= date('now', ?)
            AND total_sleep_seconds IS NOT NULL
            ORDER BY date DESC
        """, (f'-{days} days',)).fetchall()

        if len(rows) < 3:
            return None

        declining_days = 0
        improving_days = 0

        for i in range(len(rows) - 1):
            if rows[i]['sleep_hours'] < rows[i+1]['sleep_hours'] - 0.25:  # 15 min threshold
                declining_days += 1
            elif rows[i]['sleep_hours'] > rows[i+1]['sleep_hours'] + 0.25:
                improving_days += 1

        first_sleep = rows[0]['sleep_hours']
        last_sleep = rows[-1]['sleep_hours'] if rows else first_sleep

        if last_sleep == 0:
            return None

        change_pct = ((first_sleep - last_sleep) / last_sleep) * 100

        # Calculate absolute change in minutes
        change_mins = (first_sleep - last_sleep) * 60

        if declining_days >= 3 and change_mins < -30:
            return TrendAlert(
                metric='Sleep',
                direction='declining',
                days=declining_days,
                change_pct=round(change_pct, 1),
                severity='warning'
            )
        elif improving_days >= 3 and change_mins > 30:
            return TrendAlert(
                metric='Sleep',
                direction='improving',
                days=improving_days,
                change_pct=round(change_pct, 1),
                severity='positive'
            )

        return None

    finally:
        conn.close()


def detect_recovery_trend(db_path: str, days: int = 7) -> Optional[TrendAlert]:
    """Alert if recovery score declining."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT
                h.date,
                h.hrv_last_night_avg as hrv,
                st.body_battery_charged as bb,
                s.total_sleep_seconds / 3600.0 as sleep_hours
            FROM hrv_data h
            LEFT JOIN stress_data st ON h.date = st.date
            LEFT JOIN sleep_data s ON h.date = s.date
            WHERE h.date >= date('now', ?)
            ORDER BY h.date DESC
        """, (f'-{days} days',)).fetchall()

        if len(rows) < 3:
            return None

        # Calculate recoveries
        recoveries = []
        for row in rows:
            recovery = _calculate_recovery(
                row['hrv'], None,
                row['sleep_hours'], 7.5,
                row['bb']
            )
            if recovery > 0:
                recoveries.append(recovery)

        if len(recoveries) < 3:
            return None

        # Check trend
        declining_days = 0
        improving_days = 0

        for i in range(len(recoveries) - 1):
            if recoveries[i] < recoveries[i+1] - 5:
                declining_days += 1
            elif recoveries[i] > recoveries[i+1] + 5:
                improving_days += 1

        first_recovery = recoveries[0]
        last_recovery = recoveries[-1]

        if last_recovery == 0:
            return None

        change_pct = ((first_recovery - last_recovery) / last_recovery) * 100

        if declining_days >= 3 and change_pct < -10:
            return TrendAlert(
                metric='Recovery',
                direction='declining',
                days=declining_days,
                change_pct=round(change_pct, 1),
                severity='concern' if change_pct < -20 else 'warning'
            )
        elif improving_days >= 3 and change_pct > 10:
            return TrendAlert(
                metric='Recovery',
                direction='improving',
                days=improving_days,
                change_pct=round(change_pct, 1),
                severity='positive'
            )

        return None

    finally:
        conn.close()


def get_all_trend_alerts(db_path: str) -> List[TrendAlert]:
    """Get all trend alerts."""
    alerts = []

    try:
        alert = detect_hrv_trend(db_path)
        if alert:
            alerts.append(alert)
    except Exception:
        pass

    try:
        alert = detect_sleep_trend(db_path)
        if alert:
            alerts.append(alert)
    except Exception:
        pass

    try:
        alert = detect_recovery_trend(db_path)
        if alert:
            alerts.append(alert)
    except Exception:
        pass

    return alerts


# Weekly summary

def generate_weekly_summary(db_path: str) -> WeeklySummary:
    """Generate comprehensive weekly behavioral summary."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT
                h.date,
                h.hrv_last_night_avg as hrv,
                st.body_battery_charged as bb,
                st.body_battery_drained as bb_drained,
                s.total_sleep_seconds / 3600.0 as sleep_hours,
                a.steps,
                a.intensity_minutes
            FROM hrv_data h
            LEFT JOIN stress_data st ON h.date = st.date
            LEFT JOIN sleep_data s ON h.date = s.date
            LEFT JOIN activity_data a ON h.date = a.date
            WHERE h.date >= date('now', '-7 days')
            ORDER BY h.date DESC
        """).fetchall()

        # Get baselines from previous 7 days
        baseline_rows = conn.execute("""
            SELECT
                h.hrv_last_night_avg as hrv,
                s.total_sleep_seconds / 3600.0 as sleep_hours
            FROM hrv_data h
            LEFT JOIN sleep_data s ON h.date = s.date
            WHERE h.date >= date('now', '-14 days')
            AND h.date < date('now', '-7 days')
        """).fetchall()

        # Calculate baselines
        hrvs = [r['hrv'] for r in baseline_rows if r['hrv'] is not None]
        hrv_baseline = sum(hrvs) / len(hrvs) if hrvs else None

        sleeps = [r['sleep_hours'] for r in baseline_rows if r['sleep_hours'] is not None]
        sleep_baseline = sum(sleeps) / len(sleeps) if sleeps else 7.5

        # Process week data
        green_days = 0
        yellow_days = 0
        red_days = 0
        recoveries = []
        strains = []
        sleeps = []
        sleep_debt = 0
        best_day = ('', 0)
        worst_day = ('', 100)

        for row in rows:
            recovery = _calculate_recovery(
                row['hrv'], hrv_baseline,
                row['sleep_hours'], sleep_baseline,
                row['bb']
            )
            recoveries.append(recovery)

            strain = _calculate_strain(
                row['bb_drained'], row['steps'], row['intensity_minutes']
            )
            strains.append(strain)

            if row['sleep_hours']:
                sleeps.append(row['sleep_hours'])
                if row['sleep_hours'] < sleep_baseline:
                    sleep_debt += sleep_baseline - row['sleep_hours']

            if recovery >= 67:
                green_days += 1
            elif recovery >= 34:
                yellow_days += 1
            else:
                red_days += 1

            if recovery > best_day[1]:
                best_day = (row['date'], recovery)
            if recovery < worst_day[1]:
                worst_day = (row['date'], recovery)

        avg_recovery = sum(recoveries) / len(recoveries) if recoveries else 0
        avg_strain = sum(strains) / len(strains) if strains else 0
        avg_sleep = sum(sleeps) / len(sleeps) if sleeps else 0

        conn.close()

        # Get correlations, streaks, and alerts
        correlations = get_all_correlations(db_path)
        streaks = get_all_streaks(db_path)
        trend_alerts = get_all_trend_alerts(db_path)

        return WeeklySummary(
            green_days=green_days,
            yellow_days=yellow_days,
            red_days=red_days,
            avg_recovery=round(avg_recovery, 1),
            avg_strain=round(avg_strain, 1),
            avg_sleep=round(avg_sleep, 2),
            total_sleep_debt=round(sleep_debt, 2),
            best_day=best_day[0],
            worst_day=worst_day[0],
            correlations=correlations,
            streaks=streaks,
            trend_alerts=trend_alerts
        )

    except Exception as e:
        conn.close()
        # Return empty summary on error
        return WeeklySummary(
            green_days=0,
            yellow_days=0,
            red_days=0,
            avg_recovery=0,
            avg_strain=0,
            avg_sleep=0,
            total_sleep_debt=0,
            best_day='',
            worst_day='',
            correlations=[],
            streaks=[],
            trend_alerts=[]
        )


# Database schema updates

def create_causality_tables(db_path: str) -> None:
    """Create tables for storing detected correlations and streaks."""
    conn = sqlite3.connect(db_path)

    try:
        conn.executescript("""
            -- Detected correlations
            CREATE TABLE IF NOT EXISTS correlations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detected_at TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                impact REAL NOT NULL,
                confidence REAL NOT NULL,
                sample_size INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1
            );

            -- Streak tracking
            CREATE TABLE IF NOT EXISTS streaks (
                name TEXT PRIMARY KEY,
                current_count INTEGER DEFAULT 0,
                best_count INTEGER DEFAULT 0,
                last_date TEXT,
                is_active INTEGER DEFAULT 1
            );

            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_correlations_active ON correlations(is_active);
            CREATE INDEX IF NOT EXISTS idx_correlations_category ON correlations(category);
        """)
        conn.commit()
    finally:
        conn.close()


def save_correlation(db_path: str, correlation: Correlation) -> None:
    """Save a detected correlation to the database."""
    conn = sqlite3.connect(db_path)

    try:
        conn.execute("""
            INSERT INTO correlations
            (detected_at, pattern_type, category, title, description, impact, confidence, sample_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            correlation.pattern_type,
            correlation.category,
            correlation.title,
            correlation.description,
            correlation.impact,
            correlation.confidence,
            correlation.sample_size,
        ))
        conn.commit()
    finally:
        conn.close()


def save_streak(db_path: str, streak: Streak) -> None:
    """Save a streak to the database."""
    conn = sqlite3.connect(db_path)

    try:
        conn.execute("""
            INSERT OR REPLACE INTO streaks
            (name, current_count, best_count, last_date, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (
            streak.name,
            streak.current_count,
            streak.best_count,
            streak.last_date,
            1 if streak.is_active else 0,
        ))
        conn.commit()
    finally:
        conn.close()


def get_saved_correlations(db_path: str, active_only: bool = True) -> List[Correlation]:
    """Get saved correlations from the database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        query = "SELECT * FROM correlations"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY confidence DESC"

        rows = conn.execute(query).fetchall()

        return [
            Correlation(
                pattern_type=row['pattern_type'],
                category=row['category'],
                title=row['title'],
                description=row['description'],
                impact=row['impact'],
                confidence=row['confidence'],
                sample_size=row['sample_size'],
            )
            for row in rows
        ]
    finally:
        conn.close()


def get_saved_streaks(db_path: str) -> List[Streak]:
    """Get saved streaks from the database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute(
            "SELECT * FROM streaks WHERE is_active = 1"
        ).fetchall()

        return [
            Streak(
                name=row['name'],
                current_count=row['current_count'],
                best_count=row['best_count'],
                is_active=bool(row['is_active']),
                last_date=row['last_date'] or '',
            )
            for row in rows
        ]
    finally:
        conn.close()
