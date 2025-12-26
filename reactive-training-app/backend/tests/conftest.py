"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
import sys

# Add training-analyzer to path for imports
project_root = Path(__file__).parent.parent.parent.parent
training_analyzer_path = project_root / "training-analyzer" / "src"
if str(training_analyzer_path) not in sys.path:
    sys.path.insert(0, str(training_analyzer_path))


@pytest.fixture
def mock_athlete_context():
    """Mock athlete context for testing."""
    return {
        "fitness": {
            "ctl": 45.0,
            "atl": 52.0,
            "tsb": -7.0,
            "acwr": 1.15,
            "risk_zone": "optimal",
            "daily_load": 85.0,
        },
        "physiology": {
            "max_hr": 185,
            "rest_hr": 55,
            "lthr": 165,
            "age": 35,
            "gender": "male",
            "vdot": 52.0,
        },
        "hr_zones": [
            {"zone": 1, "name": "Recovery", "min_hr": 120, "max_hr": 133},
            {"zone": 2, "name": "Aerobic", "min_hr": 133, "max_hr": 146},
            {"zone": 3, "name": "Tempo", "min_hr": 146, "max_hr": 159},
            {"zone": 4, "name": "Threshold", "min_hr": 159, "max_hr": 172},
            {"zone": 5, "name": "VO2max", "min_hr": 172, "max_hr": 185},
        ],
        "training_paces": [
            {"name": "Easy", "pace_sec_per_km": 360, "pace_formatted": "6:00/km"},
            {"name": "Tempo", "pace_sec_per_km": 300, "pace_formatted": "5:00/km"},
            {"name": "Interval", "pace_sec_per_km": 270, "pace_formatted": "4:30/km"},
        ],
        "race_goals": [
            {
                "distance": "Marathon",
                "target_time_formatted": "3:30:00",
                "race_date": "2025-04-15",
                "weeks_remaining": 16,
            }
        ],
        "readiness": {
            "score": 75,
            "zone": "green",
            "recommendation": "Ready for quality work",
        },
    }


@pytest.fixture
def mock_workout():
    """Mock workout data for testing."""
    return {
        "activity_id": "test_123",
        "date": "2025-12-25",
        "activity_type": "running",
        "activity_name": "Morning Run",
        "duration_min": 45.0,
        "distance_km": 8.5,
        "avg_hr": 152,
        "max_hr": 168,
        "pace_sec_per_km": 318,
        "hrss": 75.0,
        "trimp": 85.0,
        "zone1_pct": 5,
        "zone2_pct": 45,
        "zone3_pct": 35,
        "zone4_pct": 15,
        "zone5_pct": 0,
    }
