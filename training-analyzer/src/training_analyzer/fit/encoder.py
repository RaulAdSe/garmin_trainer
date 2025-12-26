"""
FIT File Encoder for Garmin workout export.

Converts StructuredWorkout objects to Garmin FIT format files that can be:
1. Transferred to Garmin devices via USB (/Garmin/NewFiles/)
2. Imported into Garmin Connect
3. Synced via Garmin Express

This module uses the fit-tool library for FIT encoding.

References:
- Garmin FIT SDK: https://developer.garmin.com/fit/
- FIT Cookbook: https://developer.garmin.com/fit/cookbook/encoding-workout-files/
"""

import datetime
import struct
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Union
import io

from ..models.workouts import (
    IntensityZone,
    IntervalType,
    StructuredWorkout,
    WorkoutInterval,
    WorkoutSport,
)


# FIT Protocol constants
FIT_HEADER_SIZE = 14
FIT_PROTOCOL_VERSION = 0x20  # 2.0
FIT_PROFILE_VERSION = 2132   # 21.32

# Message Types (Local Message IDs)
LOCAL_MESSAGE_FILE_ID = 0
LOCAL_MESSAGE_WORKOUT = 1
LOCAL_MESSAGE_WORKOUT_STEP = 2

# Global Message Numbers
MESG_NUM_FILE_ID = 0
MESG_NUM_WORKOUT = 26
MESG_NUM_WORKOUT_STEP = 27

# File Types
FILE_TYPE_WORKOUT = 5

# Manufacturers
MANUFACTURER_DEVELOPMENT = 255

# Sports
SPORT_RUNNING = 1
SPORT_CYCLING = 2
SPORT_SWIMMING = 5

# Workout Step Duration Types
DURATION_TIME = 0
DURATION_DISTANCE = 1
DURATION_OPEN = 5
DURATION_REPEAT_UNTIL_STEPS_CMPLT = 6

# Workout Step Target Types
TARGET_SPEED = 0
TARGET_HEART_RATE = 1
TARGET_OPEN = 2
TARGET_CADENCE = 3
TARGET_POWER = 4
TARGET_HR_CUSTOM = 1  # Custom HR range vs zone

# Intensity
INTENSITY_ACTIVE = 0
INTENSITY_REST = 1
INTENSITY_WARMUP = 2
INTENSITY_COOLDOWN = 3
INTENSITY_RECOVERY = 4
INTENSITY_INTERVAL = 5
INTENSITY_OTHER = 6

# Field Types
FIELD_TYPE_ENUM = 0
FIELD_TYPE_SINT8 = 1
FIELD_TYPE_UINT8 = 2
FIELD_TYPE_SINT16 = 131
FIELD_TYPE_UINT16 = 132
FIELD_TYPE_SINT32 = 133
FIELD_TYPE_UINT32 = 134
FIELD_TYPE_STRING = 7
FIELD_TYPE_FLOAT32 = 136
FIELD_TYPE_FLOAT64 = 137
FIELD_TYPE_UINT8Z = 10
FIELD_TYPE_UINT16Z = 139
FIELD_TYPE_UINT32Z = 140


class FITEncoder:
    """
    Encodes StructuredWorkout objects to Garmin FIT format.

    The FIT (Flexible and Interoperable Data Transfer) protocol is the
    standard format for Garmin fitness devices.
    """

    def __init__(self):
        """Initialize the FIT encoder."""
        self._data = bytearray()
        self._data_size = 0

    def encode(self, workout: StructuredWorkout) -> bytes:
        """
        Encode a StructuredWorkout to FIT format bytes.

        Args:
            workout: The structured workout to encode

        Returns:
            FIT file contents as bytes
        """
        self._data = bytearray()
        self._data_size = 0

        # Write data records (we'll prepend header and append CRC later)
        data_records = self._encode_workout_data(workout)

        # Build complete file
        header = self._build_header(len(data_records))
        crc = self._calculate_crc(header + data_records)

        return bytes(header + data_records + struct.pack('<H', crc))

    def encode_to_file(self, workout: StructuredWorkout, file_path: Union[str, Path]) -> Path:
        """
        Encode a workout and write to a FIT file.

        Args:
            workout: The structured workout to encode
            file_path: Path for the output FIT file

        Returns:
            Path to the created file
        """
        file_path = Path(file_path)
        fit_bytes = self.encode(workout)

        with open(file_path, 'wb') as f:
            f.write(fit_bytes)

        return file_path

    def encode_to_temp_file(self, workout: StructuredWorkout) -> Path:
        """
        Encode a workout to a temporary FIT file.

        Args:
            workout: The structured workout to encode

        Returns:
            Path to the temporary file (caller should clean up)
        """
        fit_bytes = self.encode(workout)

        # Create temp file with .fit extension
        fd, temp_path = tempfile.mkstemp(suffix='.fit', prefix='workout_')
        with open(fd, 'wb') as f:
            f.write(fit_bytes)

        return Path(temp_path)

    def _encode_workout_data(self, workout: StructuredWorkout) -> bytes:
        """Encode all workout data records."""
        data = bytearray()

        # 1. File ID message (definition + data)
        data.extend(self._encode_file_id_definition())
        data.extend(self._encode_file_id_data(workout))

        # 2. Workout message (definition + data)
        data.extend(self._encode_workout_definition(workout.name))
        data.extend(self._encode_workout_data_record(workout))

        # 3. Workout steps (definition + data for each)
        data.extend(self._encode_workout_step_definition())

        # Flatten intervals with repetitions
        steps = self._flatten_intervals(workout.intervals)

        for i, step in enumerate(steps):
            data.extend(self._encode_workout_step_data(step, i))

        return bytes(data)

    def _flatten_intervals(self, intervals: List[WorkoutInterval]) -> List[WorkoutInterval]:
        """
        Flatten intervals by expanding repetitions.

        For Garmin devices, we expand repeated intervals into individual steps.
        Repeat steps could be used for more complex repeat structures.
        """
        flattened = []
        for interval in intervals:
            if interval.repetitions > 1:
                for _ in range(interval.repetitions):
                    # Create a copy with repetitions=1
                    step = WorkoutInterval(
                        type=interval.type,
                        duration_sec=interval.duration_sec,
                        distance_m=interval.distance_m,
                        target_pace_range=interval.target_pace_range,
                        target_hr_range=interval.target_hr_range,
                        repetitions=1,
                        notes=interval.notes,
                        intensity_zone=interval.intensity_zone,
                    )
                    flattened.append(step)
            else:
                flattened.append(interval)
        return flattened

    def _build_header(self, data_size: int) -> bytes:
        """
        Build the FIT file header.

        FIT header structure (14 bytes):
        - header_size (1 byte): 14
        - protocol_version (1 byte): 0x20
        - profile_version (2 bytes): little-endian
        - data_size (4 bytes): little-endian
        - data_type (4 bytes): ".FIT"
        - header_crc (2 bytes): CRC of header bytes 0-11
        """
        header = bytearray(14)
        header[0] = FIT_HEADER_SIZE
        header[1] = FIT_PROTOCOL_VERSION
        struct.pack_into('<H', header, 2, FIT_PROFILE_VERSION)
        struct.pack_into('<I', header, 4, data_size)
        header[8:12] = b'.FIT'

        # Calculate header CRC
        header_crc = self._calculate_crc(header[:12])
        struct.pack_into('<H', header, 12, header_crc)

        return bytes(header)

    def _calculate_crc(self, data: bytes) -> int:
        """Calculate FIT CRC-16 checksum."""
        crc_table = [
            0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
            0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
        ]

        crc = 0
        for byte in data:
            # Low nibble
            tmp = crc_table[crc & 0xF]
            crc = (crc >> 4) & 0x0FFF
            crc = crc ^ tmp ^ crc_table[byte & 0xF]

            # High nibble
            tmp = crc_table[crc & 0xF]
            crc = (crc >> 4) & 0x0FFF
            crc = crc ^ tmp ^ crc_table[(byte >> 4) & 0xF]

        return crc

    # ========================================================================
    # File ID Message
    # ========================================================================

    def _encode_file_id_definition(self) -> bytes:
        """
        Encode File ID definition message.

        Definition message header: 0x40 | local_message_id
        """
        data = bytearray()

        # Record header: definition message for local message 0
        data.append(0x40 | LOCAL_MESSAGE_FILE_ID)

        # Reserved byte
        data.append(0)

        # Architecture (0 = little endian)
        data.append(0)

        # Global Message Number (file_id = 0)
        data.extend(struct.pack('<H', MESG_NUM_FILE_ID))

        # Number of fields
        fields = [
            (0, 1, FIELD_TYPE_ENUM),      # type (workout)
            (1, 2, FIELD_TYPE_UINT16),    # manufacturer
            (2, 2, FIELD_TYPE_UINT16),    # product
            (3, 4, FIELD_TYPE_UINT32Z),   # serial_number
            (4, 4, FIELD_TYPE_UINT32),    # time_created
        ]
        data.append(len(fields))

        # Field definitions
        for field_num, size, base_type in fields:
            data.append(field_num)
            data.append(size)
            data.append(base_type)

        return bytes(data)

    def _encode_file_id_data(self, workout: StructuredWorkout) -> bytes:
        """Encode File ID data message."""
        data = bytearray()

        # Record header: data message for local message 0
        data.append(LOCAL_MESSAGE_FILE_ID)

        # type = workout (5)
        data.append(FILE_TYPE_WORKOUT)

        # manufacturer = development (255)
        data.extend(struct.pack('<H', MANUFACTURER_DEVELOPMENT))

        # product = 0
        data.extend(struct.pack('<H', 0))

        # serial_number
        data.extend(struct.pack('<I', 0x12345678))

        # time_created (FIT timestamp: seconds since UTC 00:00 Dec 31 1989)
        fit_epoch = datetime.datetime(1989, 12, 31, 0, 0, 0, tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        fit_timestamp = int((now - fit_epoch).total_seconds())
        data.extend(struct.pack('<I', fit_timestamp))

        return bytes(data)

    # ========================================================================
    # Workout Message
    # ========================================================================

    def _encode_workout_definition(self, name: str) -> bytes:
        """Encode Workout definition message."""
        data = bytearray()

        # Ensure name is properly sized (max 64 bytes in FIT)
        name_bytes = name.encode('utf-8')[:63]
        name_size = len(name_bytes) + 1  # Include null terminator

        # Record header: definition message for local message 1
        data.append(0x40 | LOCAL_MESSAGE_WORKOUT)

        # Reserved byte
        data.append(0)

        # Architecture (0 = little endian)
        data.append(0)

        # Global Message Number (workout = 26)
        data.extend(struct.pack('<H', MESG_NUM_WORKOUT))

        # Fields
        fields = [
            (4, 1, FIELD_TYPE_ENUM),         # sport
            (6, name_size, FIELD_TYPE_STRING),  # wkt_name
            (8, 2, FIELD_TYPE_UINT16),       # num_valid_steps
        ]
        data.append(len(fields))

        for field_num, size, base_type in fields:
            data.append(field_num)
            data.append(size)
            data.append(base_type)

        return bytes(data)

    def _encode_workout_data_record(self, workout: StructuredWorkout) -> bytes:
        """Encode Workout data message."""
        data = bytearray()

        # Record header: data message for local message 1
        data.append(LOCAL_MESSAGE_WORKOUT)

        # Sport
        sport_map = {
            WorkoutSport.RUNNING: SPORT_RUNNING,
            WorkoutSport.CYCLING: SPORT_CYCLING,
            WorkoutSport.SWIMMING: SPORT_SWIMMING,
        }
        data.append(sport_map.get(workout.sport, SPORT_RUNNING))

        # Workout name (null-terminated string)
        name_bytes = workout.name.encode('utf-8')[:63]
        data.extend(name_bytes)
        data.append(0)  # Null terminator

        # Number of valid steps
        steps = self._flatten_intervals(workout.intervals)
        data.extend(struct.pack('<H', len(steps)))

        return bytes(data)

    # ========================================================================
    # Workout Step Messages
    # ========================================================================

    def _encode_workout_step_definition(self) -> bytes:
        """Encode Workout Step definition message."""
        data = bytearray()

        # Record header: definition message for local message 2
        data.append(0x40 | LOCAL_MESSAGE_WORKOUT_STEP)

        # Reserved byte
        data.append(0)

        # Architecture (0 = little endian)
        data.append(0)

        # Global Message Number (workout_step = 27)
        data.extend(struct.pack('<H', MESG_NUM_WORKOUT_STEP))

        # Fields for workout step
        fields = [
            (254, 2, FIELD_TYPE_UINT16),     # message_index
            (0, 24, FIELD_TYPE_STRING),      # wkt_step_name (24 chars max)
            (1, 1, FIELD_TYPE_ENUM),         # duration_type
            (2, 4, FIELD_TYPE_UINT32),       # duration_value
            (3, 1, FIELD_TYPE_ENUM),         # target_type
            (4, 4, FIELD_TYPE_UINT32),       # target_value
            (5, 4, FIELD_TYPE_UINT32),       # custom_target_value_low
            (6, 4, FIELD_TYPE_UINT32),       # custom_target_value_high
            (7, 1, FIELD_TYPE_ENUM),         # intensity
        ]
        data.append(len(fields))

        for field_num, size, base_type in fields:
            data.append(field_num)
            data.append(size)
            data.append(base_type)

        return bytes(data)

    def _encode_workout_step_data(self, interval: WorkoutInterval, step_index: int) -> bytes:
        """Encode a single Workout Step data message."""
        data = bytearray()

        # Record header: data message for local message 2
        data.append(LOCAL_MESSAGE_WORKOUT_STEP)

        # message_index
        data.extend(struct.pack('<H', step_index))

        # wkt_step_name (24 bytes, null-padded)
        step_name = self._get_step_name(interval, step_index)
        name_bytes = step_name.encode('utf-8')[:23]
        name_padded = name_bytes + bytes(24 - len(name_bytes))
        data.extend(name_padded)

        # Duration type and value
        duration_type, duration_value = self._get_duration(interval)
        data.append(duration_type)
        data.extend(struct.pack('<I', duration_value))

        # Target type and values
        target_type, target_value, target_low, target_high = self._get_target(interval)
        data.append(target_type)
        data.extend(struct.pack('<I', target_value))
        data.extend(struct.pack('<I', target_low))
        data.extend(struct.pack('<I', target_high))

        # Intensity
        intensity = self._get_intensity(interval)
        data.append(intensity)

        return bytes(data)

    def _get_step_name(self, interval: WorkoutInterval, index: int) -> str:
        """Generate a step name from the interval."""
        if interval.notes:
            return interval.notes[:23]

        type_names = {
            IntervalType.WARMUP: "Warm Up",
            IntervalType.WORK: f"Interval {index + 1}",
            IntervalType.RECOVERY: "Recovery",
            IntervalType.COOLDOWN: "Cool Down",
            IntervalType.REST: "Rest",
            IntervalType.ACTIVE_RECOVERY: "Active Recovery",
        }
        return type_names.get(interval.type, f"Step {index + 1}")

    def _get_duration(self, interval: WorkoutInterval) -> Tuple[int, int]:
        """
        Get duration type and value.

        For time-based: duration in milliseconds
        For distance-based: duration in centimeters (0.01m)
        """
        if interval.duration_sec:
            # Time duration in milliseconds
            return (DURATION_TIME, interval.duration_sec * 1000)
        elif interval.distance_m:
            # Distance in centimeters
            return (DURATION_DISTANCE, interval.distance_m * 100)
        else:
            # Open duration (lap button)
            return (DURATION_OPEN, 0)

    def _get_target(self, interval: WorkoutInterval) -> Tuple[int, int, int, int]:
        """
        Get target type and values.

        Returns: (target_type, target_value, custom_low, custom_high)

        For HR targets with custom range:
        - target_type = 1 (heart_rate)
        - target_value = 0
        - custom_low = HR bpm + 100 (offset for custom HR)
        - custom_high = HR bpm + 100

        For speed/pace targets:
        - target_type = 0 (speed)
        - custom values in mm/s (speed = 1000/pace_sec * 1000)
        """
        if interval.target_hr_range:
            # Heart rate target with custom range
            hr_low, hr_high = interval.target_hr_range
            # FIT uses offset of 100 for custom HR values
            return (TARGET_HEART_RATE, 0, hr_low + 100, hr_high + 100)

        elif interval.target_pace_range:
            # Speed target (converted from pace sec/km)
            pace_low, pace_high = interval.target_pace_range
            # Convert pace (sec/km) to speed (mm/s)
            # speed_m_s = 1000 / pace_sec_per_km
            # speed_mm_s = speed_m_s * 1000
            if pace_high > 0:
                speed_low = int((1000 / pace_high) * 1000)  # Faster pace = lower sec
            else:
                speed_low = 0
            if pace_low > 0:
                speed_high = int((1000 / pace_low) * 1000)  # Slower pace = higher sec
            else:
                speed_high = 0
            return (TARGET_SPEED, 0, speed_low, speed_high)

        else:
            # Open target
            return (TARGET_OPEN, 0, 0, 0)

    def _get_intensity(self, interval: WorkoutInterval) -> int:
        """Map interval type to FIT intensity value."""
        intensity_map = {
            IntervalType.WARMUP: INTENSITY_WARMUP,
            IntervalType.WORK: INTENSITY_ACTIVE,
            IntervalType.RECOVERY: INTENSITY_RECOVERY,
            IntervalType.COOLDOWN: INTENSITY_COOLDOWN,
            IntervalType.REST: INTENSITY_REST,
            IntervalType.ACTIVE_RECOVERY: INTENSITY_RECOVERY,
        }
        return intensity_map.get(interval.type, INTENSITY_ACTIVE)


class FITEncoderWithLibrary:
    """
    FIT Encoder using the fit-tool library.

    This is an alternative encoder that uses the fit-tool library
    instead of manual binary encoding. Use this if fit-tool is installed.
    """

    @staticmethod
    def is_available() -> bool:
        """Check if fit-tool library is available."""
        try:
            from fit_tool.fit_file_builder import FitFileBuilder
            return True
        except ImportError:
            return False

    def encode(self, workout: StructuredWorkout) -> bytes:
        """Encode workout using fit-tool library."""
        from fit_tool.fit_file_builder import FitFileBuilder
        from fit_tool.profile.messages.file_id_message import FileIdMessage
        from fit_tool.profile.messages.workout_message import WorkoutMessage
        from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
        from fit_tool.profile.profile_type import (
            FileType,
            Manufacturer,
            Sport,
            Intensity,
            WorkoutStepDuration,
            WorkoutStepTarget,
        )
        import datetime

        # File ID
        file_id = FileIdMessage()
        file_id.type = FileType.WORKOUT
        file_id.manufacturer = Manufacturer.DEVELOPMENT.value
        file_id.product = 0
        file_id.time_created = round(datetime.datetime.now().timestamp() * 1000)
        file_id.serial_number = 0x12345678

        # Workout
        workout_msg = WorkoutMessage()
        workout_msg.workout_name = workout.name
        workout_msg.sport = self._get_sport(workout.sport)

        # Flatten intervals
        steps = []
        step_messages = []

        for interval in workout.intervals:
            for _ in range(interval.repetitions):
                steps.append(interval)

        workout_msg.num_valid_steps = len(steps)

        # Create step messages
        for i, interval in enumerate(steps):
            step = WorkoutStepMessage()
            step.message_index = i
            step.workout_step_name = interval.notes or f"Step {i+1}"
            step.intensity = self._get_intensity(interval)

            # Duration
            if interval.duration_sec:
                step.duration_type = WorkoutStepDuration.TIME
                step.duration_time = float(interval.duration_sec)
            elif interval.distance_m:
                step.duration_type = WorkoutStepDuration.DISTANCE
                step.duration_distance = float(interval.distance_m)
            else:
                step.duration_type = WorkoutStepDuration.OPEN

            # Target
            if interval.target_hr_range:
                step.target_type = WorkoutStepTarget.HEART_RATE
                step.custom_target_heart_rate_low = interval.target_hr_range[0]
                step.custom_target_heart_rate_high = interval.target_hr_range[1]
            elif interval.target_pace_range:
                step.target_type = WorkoutStepTarget.SPEED
                # Convert pace to speed
                pace_low, pace_high = interval.target_pace_range
                step.custom_target_speed_low = 1000 / pace_high if pace_high > 0 else 0
                step.custom_target_speed_high = 1000 / pace_low if pace_low > 0 else 0
            else:
                step.target_type = WorkoutStepTarget.OPEN

            step_messages.append(step)

        # Build file
        builder = FitFileBuilder(auto_define=True, min_string_size=50)
        builder.add(file_id)
        builder.add(workout_msg)
        builder.add_all(step_messages)

        fit_file = builder.build()

        # Get bytes
        return fit_file.to_bytes()

    def _get_sport(self, sport: WorkoutSport):
        """Convert WorkoutSport to fit-tool Sport."""
        from fit_tool.profile.profile_type import Sport

        sport_map = {
            WorkoutSport.RUNNING: Sport.RUNNING,
            WorkoutSport.CYCLING: Sport.CYCLING,
            WorkoutSport.SWIMMING: Sport.SWIMMING,
        }
        return sport_map.get(sport, Sport.RUNNING)

    def _get_intensity(self, interval: WorkoutInterval):
        """Convert interval type to fit-tool Intensity."""
        from fit_tool.profile.profile_type import Intensity

        intensity_map = {
            IntervalType.WARMUP: Intensity.WARMUP,
            IntervalType.WORK: Intensity.ACTIVE,
            IntervalType.RECOVERY: Intensity.RECOVERY,
            IntervalType.COOLDOWN: Intensity.COOLDOWN,
            IntervalType.REST: Intensity.REST,
            IntervalType.ACTIVE_RECOVERY: Intensity.RECOVERY,
        }
        return intensity_map.get(interval.type, Intensity.ACTIVE)


def get_fit_encoder() -> FITEncoder:
    """
    Get the appropriate FIT encoder.

    Returns the library-based encoder if fit-tool is available,
    otherwise returns the manual encoder.
    """
    if FITEncoderWithLibrary.is_available():
        return FITEncoderWithLibrary()
    return FITEncoder()


def encode_workout_to_fit(workout: StructuredWorkout) -> bytes:
    """
    Convenience function to encode a workout to FIT bytes.

    Args:
        workout: The StructuredWorkout to encode

    Returns:
        FIT file contents as bytes
    """
    encoder = get_fit_encoder()
    return encoder.encode(workout)
