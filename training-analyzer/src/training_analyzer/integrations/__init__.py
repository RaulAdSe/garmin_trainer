"""
External integrations for the Training Analyzer.

Provides OAuth-based connections to fitness platforms:
- Garmin Connect
- Strava
- Apple Health (via HealthKit bridge)
"""

from .garmin import (
    GarminConnectClient,
    GarminOAuthFlow,
    GarminWorkoutPush,
    GarminCredentials,
)

from .strava import (
    StravaClient,
    StravaOAuthFlow,
    StravaActivity,
    StravaSegment,
)

from .base import (
    IntegrationError,
    OAuthCredentials,
    OAuthFlow,
    IntegrationClient,
)

__all__ = [
    # Base classes
    "IntegrationError",
    "OAuthCredentials",
    "OAuthFlow",
    "IntegrationClient",
    # Garmin
    "GarminConnectClient",
    "GarminOAuthFlow",
    "GarminWorkoutPush",
    "GarminCredentials",
    # Strava
    "StravaClient",
    "StravaOAuthFlow",
    "StravaActivity",
    "StravaSegment",
]

