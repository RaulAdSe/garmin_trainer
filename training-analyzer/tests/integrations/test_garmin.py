"""Tests for Garmin Connect integration."""

import pytest
from datetime import datetime, timedelta
from training_analyzer.integrations.garmin import (
    GarminActivity,
    GarminActivityType,
    GarminConnectClient,
    GarminCredentials,
    GarminOAuthFlow,
    GarminWorkout,
    GarminWorkoutPush,
    GarminWorkoutStep,
)
from training_analyzer.integrations.base import AuthenticationError


class TestGarminCredentials:
    """Tests for GarminCredentials."""

    def test_unauthenticated(self):
        """Test unauthenticated credentials."""
        creds = GarminCredentials(
            consumer_key="test_key",
            consumer_secret="test_secret",
        )

        assert creds.is_authenticated is False

    def test_authenticated(self):
        """Test authenticated credentials."""
        creds = GarminCredentials(
            consumer_key="test_key",
            consumer_secret="test_secret",
            access_token="access_token",
            access_token_secret="access_secret",
        )

        assert creds.is_authenticated is True

    def test_serialization(self):
        """Test credentials serialization."""
        creds = GarminCredentials(
            consumer_key="test_key",
            consumer_secret="test_secret",
            access_token="access_token",
            access_token_secret="access_secret",
            user_id="12345",
            display_name="Test User",
        )

        data = creds.to_dict()

        assert data["consumer_key"] == "test_key"
        assert data["access_token"] == "access_token"
        assert data["user_id"] == "12345"

    def test_deserialization(self):
        """Test credentials deserialization."""
        data = {
            "consumer_key": "key",
            "consumer_secret": "secret",
            "access_token": "token",
            "access_token_secret": "token_secret",
            "user_id": "123",
            "display_name": "User",
            "created_at": datetime.now().isoformat(),
        }

        creds = GarminCredentials.from_dict(data)

        assert creds.consumer_key == "key"
        assert creds.access_token == "token"
        assert creds.is_authenticated is True


class TestGarminOAuthFlow:
    """Tests for GarminOAuthFlow."""

    @pytest.fixture
    def oauth_flow(self):
        """Create OAuth flow instance."""
        return GarminOAuthFlow(
            consumer_key="test_consumer_key",
            consumer_secret="test_consumer_secret",
            callback_url="http://localhost:3000/callback",
        )

    def test_generate_nonce(self, oauth_flow):
        """Test nonce generation."""
        nonce1 = oauth_flow._generate_nonce()
        nonce2 = oauth_flow._generate_nonce()

        assert nonce1 != nonce2
        assert len(nonce1) == 32  # 16 hex bytes

    def test_generate_timestamp(self, oauth_flow):
        """Test timestamp generation."""
        ts = oauth_flow._generate_timestamp()

        assert ts.isdigit()
        assert len(ts) == 10  # Unix timestamp

    def test_percent_encode(self, oauth_flow):
        """Test percent encoding."""
        assert oauth_flow._percent_encode("hello world") == "hello%20world"
        assert oauth_flow._percent_encode("test=value&foo=bar") == "test%3Dvalue%26foo%3Dbar"

    def test_authorization_url(self, oauth_flow):
        """Test authorization URL generation."""
        url = oauth_flow.get_authorization_url("test_token")

        assert url.startswith("https://connect.garmin.com/oauthConfirm")
        assert "oauth_token=test_token" in url


class TestGarminActivity:
    """Tests for GarminActivity."""

    def test_activity_creation(self):
        """Test activity creation."""
        activity = GarminActivity(
            activity_id="123456",
            activity_type=GarminActivityType.RUNNING,
            name="Morning Run",
            start_time=datetime.now(),
            duration_sec=3600,
            distance_m=10000,
            avg_hr=150,
            max_hr=175,
        )

        assert activity.activity_id == "123456"
        assert activity.activity_type == GarminActivityType.RUNNING
        assert activity.duration_sec == 3600

    def test_activity_serialization(self):
        """Test activity serialization."""
        activity = GarminActivity(
            activity_id="123456",
            activity_type=GarminActivityType.CYCLING,
            name="Afternoon Ride",
            start_time=datetime(2024, 1, 15, 14, 30),
            duration_sec=5400,
            distance_m=45000,
            avg_power=200,
            elevation_gain_m=500,
        )

        data = activity.to_dict()

        assert data["activity_id"] == "123456"
        assert data["activity_type"] == "cycling"
        assert data["distance_m"] == 45000
        assert data["avg_power"] == 200


class TestGarminWorkout:
    """Tests for GarminWorkout."""

    def test_workout_creation(self):
        """Test workout creation."""
        workout = GarminWorkout(
            name="Tempo Run",
            sport_type="running",
            description="30 min tempo workout",
            estimated_duration_sec=2400,
        )

        assert workout.name == "Tempo Run"
        assert workout.sport_type == "running"
        assert len(workout.steps) == 0

    def test_workout_with_steps(self):
        """Test workout with steps."""
        steps = [
            GarminWorkoutStep(
                step_type="warmup",
                duration_type="time",
                duration_value=600,
                target_type="open",
            ),
            GarminWorkoutStep(
                step_type="interval",
                duration_type="distance",
                duration_value=1000,
                target_type="pace",
                target_low=240,  # 4:00/km
                target_high=250,  # 4:10/km
            ),
            GarminWorkoutStep(
                step_type="cooldown",
                duration_type="time",
                duration_value=600,
                target_type="open",
            ),
        ]

        workout = GarminWorkout(
            name="Speed Work",
            sport_type="running",
            steps=steps,
        )

        assert len(workout.steps) == 3
        assert workout.steps[1].step_type == "interval"
        assert workout.steps[1].target_low == 240

    def test_workout_to_garmin_format(self):
        """Test conversion to Garmin API format."""
        steps = [
            GarminWorkoutStep(
                step_type="warmup",
                duration_type="time",
                duration_value=600,
            ),
            GarminWorkoutStep(
                step_type="interval",
                duration_type="distance",
                duration_value=400,
                target_type="pace",
                target_low=210,
                target_high=220,
            ),
        ]

        workout = GarminWorkout(
            name="Track Session",
            sport_type="running",
            steps=steps,
            description="400m repeats",
            estimated_duration_sec=3600,
        )

        garmin_format = workout.to_garmin_format()

        assert garmin_format["workoutName"] == "Track Session"
        assert garmin_format["sportType"]["sportTypeKey"] == "running"
        assert len(garmin_format["workoutSegments"]) == 1
        assert len(garmin_format["workoutSegments"][0]["workoutSteps"]) == 2


class TestGarminConnectClient:
    """Tests for GarminConnectClient."""

    @pytest.fixture
    def authenticated_creds(self):
        """Create authenticated credentials."""
        return GarminCredentials(
            consumer_key="test_key",
            consumer_secret="test_secret",
            access_token="access_token",
            access_token_secret="access_secret",
            user_id="12345",
        )

    @pytest.fixture
    def unauthenticated_creds(self):
        """Create unauthenticated credentials."""
        return GarminCredentials(
            consumer_key="test_key",
            consumer_secret="test_secret",
        )

    def test_client_requires_auth(self, unauthenticated_creds):
        """Test that client requires authenticated credentials."""
        with pytest.raises(AuthenticationError):
            GarminConnectClient(unauthenticated_creds)

    def test_client_creation(self, authenticated_creds):
        """Test client creation with authenticated credentials."""
        client = GarminConnectClient(authenticated_creds)

        assert client.credentials.user_id == "12345"

    def test_sign_request(self, authenticated_creds):
        """Test request signing."""
        client = GarminConnectClient(authenticated_creds)

        headers = client._sign_request("GET", "https://example.com/api")

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("OAuth ")
        assert "oauth_consumer_key" in headers["Authorization"]
        assert "oauth_token" in headers["Authorization"]


class TestGarminWorkoutPush:
    """Tests for GarminWorkoutPush."""

    @pytest.fixture
    def client(self):
        """Create Garmin client."""
        creds = GarminCredentials(
            consumer_key="test_key",
            consumer_secret="test_secret",
            access_token="access_token",
            access_token_secret="access_secret",
        )
        return GarminConnectClient(creds)

    @pytest.fixture
    def push_service(self, client):
        """Create workout push service."""
        return GarminWorkoutPush(client)

    def test_push_service_creation(self, push_service, client):
        """Test push service creation."""
        assert push_service.client is client

    @pytest.mark.asyncio
    async def test_push_workout(self, push_service):
        """Test workout push (mock)."""
        workout = GarminWorkout(
            name="Test Workout",
            sport_type="running",
            steps=[
                GarminWorkoutStep(
                    step_type="warmup",
                    duration_type="time",
                    duration_value=300,
                ),
            ],
        )

        # This returns placeholder - real test would mock HTTP
        workout_id = await push_service.push_workout(workout)

        assert workout_id is not None


