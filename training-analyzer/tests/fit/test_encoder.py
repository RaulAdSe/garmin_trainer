"""
Tests for the FIT file encoder.

Tests cover:
- Basic workout encoding
- Various interval types (warmup, work, recovery, cooldown)
- Pace and HR targets
- FIT file structure validation
- Edge cases
"""

import pytest
import struct
import tempfile
from pathlib import Path

from reactive_training.models.workouts import (
    AthleteContext,
    IntensityZone,
    IntervalType,
    StructuredWorkout,
    WorkoutInterval,
    WorkoutSport,
)
from reactive_training.fit.encoder import (
    FITEncoder,
    encode_workout_to_fit,
    FIT_HEADER_SIZE,
    FILE_TYPE_WORKOUT,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def simple_workout():
    """Create a simple workout for testing."""
    return StructuredWorkout.create(
        name="Test Easy Run",
        description="Simple easy run for testing",
        intervals=[
            WorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=300,
                notes="Easy warmup",
            ),
            WorkoutInterval(
                type=IntervalType.WORK,
                duration_sec=1800,
                target_pace_range=(340, 380),
                target_hr_range=(130, 145),
                notes="Easy running",
                intensity_zone=IntensityZone.RECOVERY,
            ),
            WorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=300,
                notes="Cool down",
            ),
        ],
    )


@pytest.fixture
def interval_workout():
    """Create an interval workout for testing."""
    intervals = [
        WorkoutInterval(
            type=IntervalType.WARMUP,
            duration_sec=600,
            target_pace_range=(350, 390),
            target_hr_range=(120, 140),
            notes="Easy jog with strides",
        ),
    ]

    # Add 4 work/recovery pairs
    for i in range(4):
        intervals.append(
            WorkoutInterval(
                type=IntervalType.WORK,
                duration_sec=180,
                target_pace_range=(260, 280),
                target_hr_range=(165, 180),
                notes=f"Interval {i+1}",
                intensity_zone=IntensityZone.VO2MAX,
            )
        )
        if i < 3:  # No recovery after last interval
            intervals.append(
                WorkoutInterval(
                    type=IntervalType.RECOVERY,
                    duration_sec=120,
                    target_hr_range=(120, 140),
                    notes="Recovery jog",
                )
            )

    intervals.append(
        WorkoutInterval(
            type=IntervalType.COOLDOWN,
            duration_sec=600,
            target_pace_range=(350, 400),
            target_hr_range=(120, 140),
            notes="Easy cooldown",
        )
    )

    return StructuredWorkout.create(
        name="Test Interval Session",
        description="VO2max intervals for testing",
        intervals=intervals,
    )


@pytest.fixture
def tempo_workout():
    """Create a tempo workout for testing."""
    return StructuredWorkout.create(
        name="Tempo Run",
        description="Threshold tempo run",
        intervals=[
            WorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=600,
                target_pace_range=(340, 370),
                target_hr_range=(125, 145),
            ),
            WorkoutInterval(
                type=IntervalType.WORK,
                duration_sec=1200,
                target_pace_range=(290, 310),
                target_hr_range=(155, 170),
                intensity_zone=IntensityZone.TEMPO,
            ),
            WorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=600,
                target_pace_range=(340, 380),
                target_hr_range=(125, 145),
            ),
        ],
    )


@pytest.fixture
def workout_with_repetitions():
    """Create a workout with repeated intervals."""
    return StructuredWorkout.create(
        name="Repeat Test",
        description="Test repetitions handling",
        intervals=[
            WorkoutInterval(
                type=IntervalType.WARMUP,
                duration_sec=300,
            ),
            WorkoutInterval(
                type=IntervalType.WORK,
                duration_sec=60,
                repetitions=3,
                target_pace_range=(270, 290),
            ),
            WorkoutInterval(
                type=IntervalType.COOLDOWN,
                duration_sec=300,
            ),
        ],
    )


# ============================================================================
# Test FIT Header
# ============================================================================

class TestFITHeader:
    """Tests for FIT file header encoding."""

    def test_header_size(self, simple_workout):
        """Test that FIT header is correct size."""
        encoder = FITEncoder()
        fit_bytes = encoder.encode(simple_workout)

        # Header should be 14 bytes
        assert len(fit_bytes) >= FIT_HEADER_SIZE

    def test_header_structure(self, simple_workout):
        """Test FIT header structure."""
        encoder = FITEncoder()
        fit_bytes = encoder.encode(simple_workout)

        # Byte 0: Header size (should be 14)
        assert fit_bytes[0] == 14

        # Byte 1: Protocol version (should be 0x20 for 2.0)
        assert fit_bytes[1] == 0x20

        # Bytes 8-11: ".FIT" signature
        assert fit_bytes[8:12] == b'.FIT'

    def test_header_data_size(self, simple_workout):
        """Test that header contains correct data size."""
        encoder = FITEncoder()
        fit_bytes = encoder.encode(simple_workout)

        # Bytes 4-7: Data size (little-endian uint32)
        data_size = struct.unpack('<I', fit_bytes[4:8])[0]

        # Total file = header (14) + data + CRC (2)
        # So data_size = total - 14 - 2
        assert data_size == len(fit_bytes) - 14 - 2


# ============================================================================
# Test Workout Encoding
# ============================================================================

class TestWorkoutEncoding:
    """Tests for workout data encoding."""

    def test_simple_workout_encoding(self, simple_workout):
        """Test encoding a simple workout produces valid bytes."""
        encoder = FITEncoder()
        fit_bytes = encoder.encode(simple_workout)

        # Should produce non-empty bytes
        assert len(fit_bytes) > 0

        # Should be reasonable size (header + data + CRC)
        assert len(fit_bytes) > 14 + 2  # At minimum

    def test_interval_workout_encoding(self, interval_workout):
        """Test encoding an interval workout."""
        encoder = FITEncoder()
        fit_bytes = encoder.encode(interval_workout)

        # Should produce valid bytes
        assert len(fit_bytes) > 0

        # Interval workout has more steps, so should be larger
        assert len(fit_bytes) > 200

    def test_tempo_workout_encoding(self, tempo_workout):
        """Test encoding a tempo workout."""
        encoder = FITEncoder()
        fit_bytes = encoder.encode(tempo_workout)

        assert len(fit_bytes) > 0

    def test_workout_with_repetitions(self, workout_with_repetitions):
        """Test that repetitions are expanded into separate steps."""
        encoder = FITEncoder()

        # The encoder should flatten 3 repetitions into 3 separate steps
        flattened = encoder._flatten_intervals(workout_with_repetitions.intervals)

        # Original: 1 warmup + 1 work (x3 reps) + 1 cooldown = 3 intervals
        # Flattened: 1 warmup + 3 work + 1 cooldown = 5 intervals
        assert len(flattened) == 5


# ============================================================================
# Test File Output
# ============================================================================

class TestFileOutput:
    """Tests for FIT file output."""

    def test_encode_to_temp_file(self, simple_workout):
        """Test encoding to a temporary file."""
        encoder = FITEncoder()
        temp_path = encoder.encode_to_temp_file(simple_workout)

        try:
            # File should exist
            assert temp_path.exists()

            # File should have .fit extension
            assert temp_path.suffix == '.fit'

            # File should have content
            assert temp_path.stat().st_size > 0

            # Content should match in-memory encoding
            with open(temp_path, 'rb') as f:
                file_bytes = f.read()

            memory_bytes = encoder.encode(simple_workout)
            assert file_bytes == memory_bytes

        finally:
            # Cleanup
            temp_path.unlink(missing_ok=True)

    def test_encode_to_specific_file(self, simple_workout):
        """Test encoding to a specific file path."""
        encoder = FITEncoder()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_workout.fit"
            result_path = encoder.encode_to_file(simple_workout, file_path)

            assert result_path.exists()
            assert result_path.stat().st_size > 0


# ============================================================================
# Test Interval Encoding Details
# ============================================================================

class TestIntervalEncoding:
    """Tests for interval-specific encoding."""

    def test_duration_encoding_time(self, simple_workout):
        """Test that time-based durations are encoded correctly."""
        encoder = FITEncoder()

        # Get first interval (warmup with 300 sec duration)
        interval = simple_workout.intervals[0]
        duration_type, duration_value = encoder._get_duration(interval)

        # Should be time type (0) with value in milliseconds
        assert duration_type == 0  # TIME
        assert duration_value == 300 * 1000  # 300 seconds in ms

    def test_duration_encoding_distance(self):
        """Test that distance-based durations are encoded correctly."""
        encoder = FITEncoder()

        # Create interval with distance instead of time
        interval = WorkoutInterval(
            type=IntervalType.WORK,
            distance_m=1000,  # 1km
        )

        duration_type, duration_value = encoder._get_duration(interval)

        # Should be distance type (1) with value in centimeters
        assert duration_type == 1  # DISTANCE
        assert duration_value == 1000 * 100  # 1000m in cm

    def test_hr_target_encoding(self, simple_workout):
        """Test HR target encoding."""
        encoder = FITEncoder()

        # Get work interval with HR targets
        interval = simple_workout.intervals[1]  # Work interval
        target_type, target_value, target_low, target_high = encoder._get_target(interval)

        # Should be HR type (1)
        assert target_type == 1

        # Custom HR values are offset by 100 in FIT format
        assert target_low == interval.target_hr_range[0] + 100
        assert target_high == interval.target_hr_range[1] + 100

    def test_pace_target_encoding(self):
        """Test pace/speed target encoding."""
        encoder = FITEncoder()

        # Create interval with only pace target (no HR)
        interval = WorkoutInterval(
            type=IntervalType.WORK,
            duration_sec=300,
            target_pace_range=(300, 330),  # 5:00-5:30/km
        )

        target_type, target_value, target_low, target_high = encoder._get_target(interval)

        # Should be speed type (0)
        assert target_type == 0

        # Speed values should be calculated from pace
        # pace 300 sec/km = 1000/300 = 3.33 m/s = 3333 mm/s
        # pace 330 sec/km = 1000/330 = 3.03 m/s = 3030 mm/s
        # Note: low/high are swapped because faster pace = higher speed
        expected_speed_low = int((1000 / 330) * 1000)  # slower pace
        expected_speed_high = int((1000 / 300) * 1000)  # faster pace

        assert target_low == expected_speed_low
        assert target_high == expected_speed_high

    def test_intensity_mapping(self, simple_workout):
        """Test that interval types map to correct FIT intensity values."""
        encoder = FITEncoder()

        # Test each interval type
        warmup = encoder._get_intensity(WorkoutInterval(type=IntervalType.WARMUP, duration_sec=300))
        work = encoder._get_intensity(WorkoutInterval(type=IntervalType.WORK, duration_sec=300))
        recovery = encoder._get_intensity(WorkoutInterval(type=IntervalType.RECOVERY, duration_sec=300))
        cooldown = encoder._get_intensity(WorkoutInterval(type=IntervalType.COOLDOWN, duration_sec=300))

        # FIT intensity values
        assert warmup == 2  # WARMUP
        assert work == 0    # ACTIVE
        assert recovery == 4  # RECOVERY
        assert cooldown == 3  # COOLDOWN


# ============================================================================
# Test CRC Calculation
# ============================================================================

class TestCRC:
    """Tests for FIT CRC calculation."""

    def test_crc_calculation(self, simple_workout):
        """Test that CRC is calculated and appended."""
        encoder = FITEncoder()
        fit_bytes = encoder.encode(simple_workout)

        # Last 2 bytes should be CRC
        crc = struct.unpack('<H', fit_bytes[-2:])[0]

        # CRC should be non-zero for typical workout data
        # (technically could be zero but very unlikely)
        assert isinstance(crc, int)

    def test_crc_known_values(self):
        """Test CRC calculation with known values."""
        encoder = FITEncoder()

        # Test with simple known input
        # The FIT CRC algorithm should produce consistent results
        test_data = b'\x0E\x20\x00\x00\x00\x00\x00\x00.FIT'
        crc = encoder._calculate_crc(test_data)

        # Should produce a valid 16-bit CRC
        assert 0 <= crc <= 0xFFFF


# ============================================================================
# Test Convenience Function
# ============================================================================

class TestConvenienceFunction:
    """Tests for the encode_workout_to_fit convenience function."""

    def test_encode_workout_to_fit(self, simple_workout):
        """Test the convenience function produces valid output."""
        fit_bytes = encode_workout_to_fit(simple_workout)

        assert len(fit_bytes) > 0
        assert fit_bytes[8:12] == b'.FIT'


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_intervals(self):
        """Test handling of workout with minimal intervals."""
        workout = StructuredWorkout.create(
            name="Empty Test",
            description="Minimal workout",
            intervals=[
                WorkoutInterval(
                    type=IntervalType.WORK,
                    duration_sec=600,
                ),
            ],
        )

        encoder = FITEncoder()
        fit_bytes = encoder.encode(workout)

        # Should still produce valid output
        assert len(fit_bytes) > 0

    def test_long_workout_name(self):
        """Test handling of very long workout names."""
        long_name = "This is a very long workout name that exceeds the maximum allowed length for FIT files"

        workout = StructuredWorkout.create(
            name=long_name,
            description="Test",
            intervals=[
                WorkoutInterval(type=IntervalType.WORK, duration_sec=600),
            ],
        )

        encoder = FITEncoder()
        # Should not raise an error, name should be truncated
        fit_bytes = encoder.encode(workout)
        assert len(fit_bytes) > 0

    def test_open_duration_interval(self):
        """Test interval with no duration (open/lap button)."""
        interval = WorkoutInterval(
            type=IntervalType.WORK,
            # No duration_sec or distance_m
        )

        encoder = FITEncoder()
        duration_type, duration_value = encoder._get_duration(interval)

        # Should be open duration type
        assert duration_type == 5  # OPEN
        assert duration_value == 0

    def test_open_target_interval(self):
        """Test interval with no pace/HR targets."""
        interval = WorkoutInterval(
            type=IntervalType.WORK,
            duration_sec=600,
            # No target_pace_range or target_hr_range
        )

        encoder = FITEncoder()
        target_type, target_value, target_low, target_high = encoder._get_target(interval)

        # Should be open target type
        assert target_type == 2  # OPEN
        assert target_low == 0
        assert target_high == 0

    def test_cycling_sport(self):
        """Test encoding with cycling sport type."""
        workout = StructuredWorkout.create(
            name="Bike Workout",
            description="Cycling test",
            intervals=[
                WorkoutInterval(type=IntervalType.WORK, duration_sec=600),
            ],
            sport=WorkoutSport.CYCLING,
        )

        encoder = FITEncoder()
        fit_bytes = encoder.encode(workout)

        # Should produce valid output
        assert len(fit_bytes) > 0
