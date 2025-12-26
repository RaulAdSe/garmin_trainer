"""Tests for Strava integration."""

import pytest
from datetime import datetime, timedelta
from training_analyzer.integrations.strava import (
    StravaActivity,
    StravaClient,
    StravaOAuthFlow,
    StravaSegment,
    StravaSegmentEffort,
    StravaSport,
)
from training_analyzer.integrations.base import OAuthCredentials


class TestStravaActivity:
    """Tests for StravaActivity."""

    def test_activity_creation(self):
        """Test activity creation."""
        activity = StravaActivity(
            id=123456,
            name="Morning Run",
            sport_type=StravaSport.RUN,
            start_date=datetime.now(),
            elapsed_time_sec=3600,
            moving_time_sec=3500,
            distance_m=10000,
            average_heartrate=150,
            total_elevation_gain_m=100,
        )

        assert activity.id == 123456
        assert activity.sport_type == StravaSport.RUN
        assert activity.distance_m == 10000

    def test_activity_serialization(self):
        """Test activity serialization."""
        activity = StravaActivity(
            id=789,
            name="Evening Ride",
            sport_type=StravaSport.RIDE,
            start_date=datetime(2024, 1, 15, 18, 0),
            elapsed_time_sec=7200,
            moving_time_sec=6800,
            distance_m=50000,
            average_watts=200,
            weighted_average_watts=210,
            kudos_count=15,
        )

        data = activity.to_dict()

        assert data["id"] == 789
        assert data["sport_type"] == "Ride"
        assert data["distance_m"] == 50000
        assert data["average_watts"] == 200
        assert data["kudos_count"] == 15

    def test_activity_from_api_response(self):
        """Test parsing from Strava API response."""
        api_data = {
            "id": 123456,
            "name": "Test Run",
            "sport_type": "Run",
            "start_date": "2024-01-15T10:00:00Z",
            "elapsed_time": 3600,
            "moving_time": 3500,
            "distance": 10000,
            "average_speed": 2.86,
            "average_heartrate": 150,
            "max_heartrate": 175,
            "total_elevation_gain": 100,
            "kudos_count": 10,
            "trainer": False,
        }

        activity = StravaActivity.from_api_response(api_data)

        assert activity.id == 123456
        assert activity.sport_type == StravaSport.RUN
        assert activity.elapsed_time_sec == 3600
        assert activity.average_heartrate == 150


class TestStravaSegment:
    """Tests for StravaSegment."""

    def test_segment_creation(self):
        """Test segment creation."""
        segment = StravaSegment(
            id=1234,
            name="Epic Climb",
            activity_type="Ride",
            distance_m=5000,
            average_grade=8.5,
            maximum_grade=15.0,
            elevation_high_m=500,
            elevation_low_m=75,
            effort_count=10000,
            athlete_pr_time_sec=1200,
        )

        assert segment.id == 1234
        assert segment.average_grade == 8.5
        assert segment.athlete_pr_time_sec == 1200

    def test_segment_serialization(self):
        """Test segment serialization."""
        segment = StravaSegment(
            id=5678,
            name="Fast Flat",
            activity_type="Run",
            distance_m=1000,
            average_grade=0.5,
            maximum_grade=2.0,
            elevation_high_m=105,
            elevation_low_m=100,
            city="Boston",
            country="USA",
        )

        data = segment.to_dict()

        assert data["id"] == 5678
        assert data["name"] == "Fast Flat"
        assert data["city"] == "Boston"


class TestStravaSegmentEffort:
    """Tests for StravaSegmentEffort."""

    def test_effort_creation(self):
        """Test effort creation."""
        effort = StravaSegmentEffort(
            id=111,
            segment_id=1234,
            activity_id=5678,
            elapsed_time_sec=300,
            moving_time_sec=290,
            start_date=datetime.now(),
            pr_rank=1,
            average_watts=250,
        )

        assert effort.id == 111
        assert effort.pr_rank == 1
        assert effort.average_watts == 250

    def test_effort_serialization(self):
        """Test effort serialization."""
        effort = StravaSegmentEffort(
            id=222,
            segment_id=333,
            activity_id=444,
            elapsed_time_sec=600,
            moving_time_sec=590,
            start_date=datetime(2024, 1, 15, 10, 30),
            kom_rank=5,
        )

        data = effort.to_dict()

        assert data["id"] == 222
        assert data["segment_id"] == 333
        assert data["elapsed_time_sec"] == 600


class TestStravaOAuthFlow:
    """Tests for StravaOAuthFlow."""

    @pytest.fixture
    def oauth_flow(self):
        """Create OAuth flow instance."""
        return StravaOAuthFlow(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:3000/callback",
        )

    def test_default_scope(self, oauth_flow):
        """Test default scope."""
        assert "read_all" in oauth_flow.scope
        assert "activity:read_all" in oauth_flow.scope

    def test_authorization_url(self, oauth_flow):
        """Test authorization URL generation."""
        url = oauth_flow.get_authorization_url()

        assert url.startswith("https://www.strava.com/oauth/authorize")
        assert "client_id=test_client_id" in url
        assert "redirect_uri=" in url
        assert "response_type=code" in url
        assert "scope=" in url
        assert "state=" in url

    def test_state_generation(self, oauth_flow):
        """Test state token generation."""
        state1 = oauth_flow.generate_state()
        state2 = oauth_flow.generate_state()

        # Each call generates new state
        assert state1 != state2
        # Latest state is stored
        assert oauth_flow.validate_state(state2)
        assert not oauth_flow.validate_state(state1)

    @pytest.mark.asyncio
    async def test_exchange_code(self, oauth_flow):
        """Test code exchange (mock)."""
        # This uses placeholder - real test would mock HTTP
        credentials = await oauth_flow.exchange_code("test_code")

        assert credentials.provider == "strava"
        assert credentials.access_token is not None
        assert credentials.refresh_token is not None

    @pytest.mark.asyncio
    async def test_refresh_token(self, oauth_flow):
        """Test token refresh (mock)."""
        old_credentials = OAuthCredentials(
            provider="strava",
            access_token="old_token",
            refresh_token="refresh_token",
            expires_at=datetime.now() - timedelta(hours=1),
        )

        new_credentials = await oauth_flow.refresh_token(old_credentials)

        assert new_credentials.access_token != old_credentials.access_token
        assert new_credentials.refresh_token == old_credentials.refresh_token


class TestStravaClient:
    """Tests for StravaClient."""

    @pytest.fixture
    def credentials(self):
        """Create Strava credentials."""
        return OAuthCredentials(
            provider="strava",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.now() + timedelta(hours=6),
            user_id="12345",
            user_name="Test Athlete",
        )

    @pytest.fixture
    def client(self, credentials):
        """Create Strava client."""
        return StravaClient(credentials)

    def test_client_creation(self, client, credentials):
        """Test client creation."""
        assert client.credentials.user_id == "12345"
        assert client.is_authenticated is True

    def test_wrong_provider_rejected(self):
        """Test that wrong provider credentials are rejected."""
        wrong_creds = OAuthCredentials(
            provider="garmin",
            access_token="token",
        )

        with pytest.raises(ValueError) as exc:
            StravaClient(wrong_creds)

        assert "Strava" in str(exc.value)

    def test_auth_headers(self, client):
        """Test authorization headers."""
        headers = client.get_auth_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_access_token"

    def test_is_authenticated_expired(self):
        """Test authentication check with expired token."""
        expired_creds = OAuthCredentials(
            provider="strava",
            access_token="expired_token",
            expires_at=datetime.now() - timedelta(hours=1),
        )

        client = StravaClient(expired_creds)

        assert client.is_authenticated is False

