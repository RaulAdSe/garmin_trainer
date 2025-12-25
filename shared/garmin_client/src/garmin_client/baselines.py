"""Personal baseline calculations for all metrics.

This module implements the core philosophy of WHOOP-style insights:
"Your HRV vs *your* 7-day avg, not 'normal'".

Key concepts:
- Rolling averages (7-day and 30-day) for all metrics
- Direction indicators showing change from personal baseline
- Recovery calculation using personal baselines instead of fixed thresholds
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import sqlite3


@dataclass
class DirectionIndicator:
    """Direction indicator showing change from baseline."""
    direction: str  # 'up', 'down', 'stable'
    change_pct: float
    baseline: float
    current: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PersonalBaselines:
    """Personal baselines calculated from historical data."""
    date: str
    hrv_7d_avg: Optional[float] = None
    hrv_30d_avg: Optional[float] = None
    rhr_7d_avg: Optional[float] = None
    rhr_30d_avg: Optional[float] = None
    sleep_7d_avg: Optional[float] = None  # hours
    sleep_30d_avg: Optional[float] = None  # hours
    strain_7d_avg: Optional[float] = None
    recovery_7d_avg: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_rolling_average(values: List[Optional[float]], days: int = 7) -> Optional[float]:
    """Calculate rolling average for the last N days.

    Args:
        values: List of values (may contain None)
        days: Number of days to include in average

    Returns:
        Rolling average or None if insufficient data
    """
    # Filter out None values
    valid_values = [v for v in values[:days] if v is not None]

    if len(valid_values) < 3:  # Require at least 3 data points
        return None

    return round(sum(valid_values) / len(valid_values), 2)


def calculate_direction(
    current: Optional[float],
    baseline: Optional[float],
    threshold_pct: float = 5.0,
    inverse: bool = False
) -> Optional[DirectionIndicator]:
    """Calculate direction indicator comparing current value to baseline.

    Args:
        current: Current value
        baseline: Baseline value to compare against
        threshold_pct: Percentage change required to register as up/down (default 5%)
        inverse: If True, lower is better (e.g., for RHR, stress)

    Returns:
        DirectionIndicator or None if insufficient data
    """
    if current is None or baseline is None or baseline == 0:
        return None

    change_pct = ((current - baseline) / baseline) * 100

    if abs(change_pct) < threshold_pct:
        direction = 'stable'
    elif change_pct > 0:
        direction = 'down' if inverse else 'up'
    else:
        direction = 'up' if inverse else 'down'

    return DirectionIndicator(
        direction=direction,
        change_pct=round(change_pct, 1),
        baseline=baseline,
        current=current
    )


def get_historical_values(
    db_path: str,
    date_str: str,
    metric: str,
    days: int = 30
) -> List[Optional[float]]:
    """Get historical values for a metric from the database.

    Args:
        db_path: Path to SQLite database
        date_str: Reference date (YYYY-MM-DD)
        metric: Metric to fetch ('hrv', 'rhr', 'sleep', 'strain', 'recovery')
        days: Number of days of history to fetch

    Returns:
        List of values, ordered from most recent to oldest (excluding reference date)
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # Calculate date range (excluding reference date, going back N days)
        ref_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_date = (ref_date - timedelta(days=days)).isoformat()
        end_date = (ref_date - timedelta(days=1)).isoformat()

        # Build query based on metric
        if metric == 'hrv':
            query = """
                SELECT h.date, h.hrv_last_night_avg as value
                FROM hrv_data h
                WHERE h.date >= ? AND h.date <= ?
                ORDER BY h.date DESC
            """
        elif metric == 'rhr':
            query = """
                SELECT dw.date, dw.resting_heart_rate as value
                FROM daily_wellness dw
                WHERE dw.date >= ? AND dw.date <= ?
                ORDER BY dw.date DESC
            """
        elif metric == 'sleep':
            query = """
                SELECT s.date, (s.total_sleep_seconds / 3600.0) as value
                FROM sleep_data s
                WHERE s.date >= ? AND s.date <= ?
                ORDER BY s.date DESC
            """
        elif metric == 'strain':
            # Strain is calculated from body battery drained, steps, and intensity minutes
            # We'll store a simplified version
            query = """
                SELECT st.date,
                    (COALESCE(st.body_battery_drained, 0) / 12.0 * 8 +
                     COALESCE(a.steps, 0) / 2000.0 * 8 +
                     COALESCE(a.intensity_minutes, 0) / 20.0 * 5) / 21.0 * 21.0 as value
                FROM stress_data st
                LEFT JOIN activity_data a ON st.date = a.date
                WHERE st.date >= ? AND st.date <= ?
                ORDER BY st.date DESC
            """
        elif metric == 'recovery':
            # Recovery is calculated from multiple factors
            # This is a simplified query - actual recovery calculation happens elsewhere
            query = """
                SELECT dw.date,
                    st.body_battery_charged as value
                FROM daily_wellness dw
                LEFT JOIN stress_data st ON dw.date = st.date
                WHERE dw.date >= ? AND dw.date <= ?
                ORDER BY dw.date DESC
            """
        else:
            return []

        rows = conn.execute(query, (start_date, end_date)).fetchall()
        return [row['value'] for row in rows]

    finally:
        conn.close()


def get_personal_baselines(db_path: str, date_str: str) -> PersonalBaselines:
    """Calculate 7-day and 30-day baselines for all metrics.

    Args:
        db_path: Path to SQLite database
        date_str: Reference date (YYYY-MM-DD)

    Returns:
        PersonalBaselines object with calculated averages
    """
    # Fetch historical values for each metric
    hrv_history = get_historical_values(db_path, date_str, 'hrv', 30)
    rhr_history = get_historical_values(db_path, date_str, 'rhr', 30)
    sleep_history = get_historical_values(db_path, date_str, 'sleep', 30)
    strain_history = get_historical_values(db_path, date_str, 'strain', 30)
    recovery_history = get_historical_values(db_path, date_str, 'recovery', 30)

    return PersonalBaselines(
        date=date_str,
        hrv_7d_avg=calculate_rolling_average(hrv_history, 7),
        hrv_30d_avg=calculate_rolling_average(hrv_history, 30),
        rhr_7d_avg=calculate_rolling_average(rhr_history, 7),
        rhr_30d_avg=calculate_rolling_average(rhr_history, 30),
        sleep_7d_avg=calculate_rolling_average(sleep_history, 7),
        sleep_30d_avg=calculate_rolling_average(sleep_history, 30),
        strain_7d_avg=calculate_rolling_average(strain_history, 7),
        recovery_7d_avg=calculate_rolling_average(recovery_history, 7),
    )


def calculate_recovery_with_baselines(
    current_hrv: Optional[float],
    current_sleep_hours: Optional[float],
    current_body_battery: Optional[float],
    baselines: PersonalBaselines
) -> Tuple[int, dict]:
    """Calculate recovery score using personal baselines.

    This replaces fixed thresholds with personal baseline comparisons:
    - HRV vs your 7-day average (not population "normal")
    - Sleep vs your typical sleep duration
    - Body Battery as raw recovery indicator

    Args:
        current_hrv: Today's HRV value
        current_sleep_hours: Hours slept last night
        current_body_battery: Body Battery charged overnight
        baselines: Personal baseline values

    Returns:
        Tuple of (recovery_score, factors_dict)
    """
    factors = {}
    scores = []

    # HRV Factor (primary signal)
    if current_hrv is not None and baselines.hrv_7d_avg is not None:
        hrv_ratio = current_hrv / baselines.hrv_7d_avg
        # Score: 100 at baseline, scales with ratio
        # Below baseline decreases score, above increases
        hrv_score = min(100, max(0, hrv_ratio * 80 + 20))
        scores.append(hrv_score * 1.5)  # Weight HRV higher

        factors['hrv'] = {
            'score': round(hrv_score, 1),
            'current': current_hrv,
            'baseline': baselines.hrv_7d_avg,
            'direction': calculate_direction(current_hrv, baselines.hrv_7d_avg),
            'weight': 1.5
        }

    # Sleep Factor
    if current_sleep_hours is not None and baselines.sleep_7d_avg is not None:
        sleep_ratio = current_sleep_hours / baselines.sleep_7d_avg
        # Score based on how well you met your personal sleep need
        sleep_score = min(100, max(0, sleep_ratio * 85 + 15))
        scores.append(sleep_score)

        factors['sleep'] = {
            'score': round(sleep_score, 1),
            'current': current_sleep_hours,
            'baseline': baselines.sleep_7d_avg,
            'direction': calculate_direction(current_sleep_hours, baselines.sleep_7d_avg),
            'weight': 1.0
        }

    # Body Battery Factor
    if current_body_battery is not None:
        # Body Battery is already 0-100, use directly
        bb_score = current_body_battery
        scores.append(bb_score)

        factors['body_battery'] = {
            'score': bb_score,
            'current': current_body_battery,
            'baseline': baselines.recovery_7d_avg,
            'direction': calculate_direction(current_body_battery, baselines.recovery_7d_avg),
            'weight': 1.0
        }

    # Calculate weighted average
    if not scores:
        return 0, factors

    # Account for weights in averaging
    total_weight = 0
    weighted_sum = 0

    if 'hrv' in factors:
        weighted_sum += factors['hrv']['score'] * 1.5
        total_weight += 1.5
    if 'sleep' in factors:
        weighted_sum += factors['sleep']['score'] * 1.0
        total_weight += 1.0
    if 'body_battery' in factors:
        weighted_sum += factors['body_battery']['score'] * 1.0
        total_weight += 1.0

    recovery = round(weighted_sum / total_weight) if total_weight > 0 else 0

    return recovery, factors


def save_baselines(db_path: str, baselines: PersonalBaselines) -> None:
    """Save calculated baselines to the database.

    Args:
        db_path: Path to SQLite database
        baselines: PersonalBaselines to save
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            INSERT OR REPLACE INTO baselines
            (date, hrv_7d_avg, hrv_30d_avg, rhr_7d_avg, rhr_30d_avg,
             sleep_7d_avg, sleep_30d_avg, strain_7d_avg, recovery_7d_avg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            baselines.date,
            baselines.hrv_7d_avg,
            baselines.hrv_30d_avg,
            baselines.rhr_7d_avg,
            baselines.rhr_30d_avg,
            baselines.sleep_7d_avg,
            baselines.sleep_30d_avg,
            baselines.strain_7d_avg,
            baselines.recovery_7d_avg,
        ))
        conn.commit()
    finally:
        conn.close()


def get_saved_baselines(db_path: str, date_str: str) -> Optional[PersonalBaselines]:
    """Get previously saved baselines from the database.

    Args:
        db_path: Path to SQLite database
        date_str: Date to fetch baselines for

    Returns:
        PersonalBaselines or None if not found
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM baselines WHERE date = ?", (date_str,)
        ).fetchone()

        if not row:
            return None

        return PersonalBaselines(
            date=row['date'],
            hrv_7d_avg=row['hrv_7d_avg'],
            hrv_30d_avg=row['hrv_30d_avg'],
            rhr_7d_avg=row['rhr_7d_avg'],
            rhr_30d_avg=row['rhr_30d_avg'],
            sleep_7d_avg=row['sleep_7d_avg'],
            sleep_30d_avg=row['sleep_30d_avg'],
            strain_7d_avg=row['strain_7d_avg'],
            recovery_7d_avg=row['recovery_7d_avg'],
        )
    finally:
        conn.close()
