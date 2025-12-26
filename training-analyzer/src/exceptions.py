"""
Custom exceptions for the Reactive Training App.

This module defines a hierarchy of exceptions that provide clear error
handling throughout the application. Each exception includes:
- A descriptive message
- An error code for API responses
- HTTP status code mapping
- Optional details for debugging
"""

from typing import Any, Dict, Optional
from enum import Enum


class ErrorCode(str, Enum):
    """Error codes for consistent API error responses."""

    # General errors (1000-1099)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    FORBIDDEN = "FORBIDDEN"
    UNAUTHORIZED = "UNAUTHORIZED"

    # Workout errors (2000-2099)
    WORKOUT_NOT_FOUND = "WORKOUT_NOT_FOUND"
    WORKOUT_ALREADY_EXISTS = "WORKOUT_ALREADY_EXISTS"
    WORKOUT_VALIDATION_ERROR = "WORKOUT_VALIDATION_ERROR"
    WORKOUT_ANALYSIS_FAILED = "WORKOUT_ANALYSIS_FAILED"

    # Plan errors (3000-3099)
    PLAN_NOT_FOUND = "PLAN_NOT_FOUND"
    PLAN_ALREADY_EXISTS = "PLAN_ALREADY_EXISTS"
    PLAN_VALIDATION_ERROR = "PLAN_VALIDATION_ERROR"
    PLAN_GENERATION_FAILED = "PLAN_GENERATION_FAILED"
    PLAN_ADAPTATION_FAILED = "PLAN_ADAPTATION_FAILED"
    PLAN_ALREADY_ACTIVE = "PLAN_ALREADY_ACTIVE"

    # LLM errors (4000-4099)
    LLM_SERVICE_UNAVAILABLE = "LLM_SERVICE_UNAVAILABLE"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    LLM_RESPONSE_INVALID = "LLM_RESPONSE_INVALID"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_API_ERROR = "LLM_API_ERROR"

    # FIT/Garmin errors (5000-5099)
    FIT_ENCODING_ERROR = "FIT_ENCODING_ERROR"
    FIT_DECODING_ERROR = "FIT_DECODING_ERROR"
    GARMIN_CONNECTION_ERROR = "GARMIN_CONNECTION_ERROR"
    GARMIN_UPLOAD_FAILED = "GARMIN_UPLOAD_FAILED"
    GARMIN_NOT_CONFIGURED = "GARMIN_NOT_CONFIGURED"

    # Data/Database errors (6000-6099)
    DATABASE_ERROR = "DATABASE_ERROR"
    DATA_INTEGRITY_ERROR = "DATA_INTEGRITY_ERROR"
    DATA_NOT_FOUND = "DATA_NOT_FOUND"


class ReactiveTrainingError(Exception):
    """
    Base exception for all Reactive Training App errors.

    Attributes:
        message: Human-readable error message
        code: Error code from ErrorCode enum
        status_code: HTTP status code for API responses
        details: Optional dictionary with additional error details
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response."""
        result: Dict[str, Any] = {
            "error": {
                "code": self.code.value,
                "message": self.message,
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        return result

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code.value}, message={self.message!r})"


# ============================================================================
# Validation Errors (400)
# ============================================================================

class ValidationError(ReactiveTrainingError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details=error_details,
        )


class WorkoutValidationError(ValidationError):
    """Raised when workout data validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, field=field, details=details)
        self.code = ErrorCode.WORKOUT_VALIDATION_ERROR


class PlanValidationError(ValidationError):
    """Raised when plan data validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, field=field, details=details)
        self.code = ErrorCode.PLAN_VALIDATION_ERROR


# ============================================================================
# Not Found Errors (404)
# ============================================================================

class NotFoundError(ReactiveTrainingError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        message = f"{resource_type} with ID '{resource_id}' not found"
        error_details = details or {}
        error_details["resource_type"] = resource_type
        error_details["resource_id"] = resource_id
        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            status_code=404,
            details=error_details,
        )


class WorkoutNotFoundError(NotFoundError):
    """Raised when a workout is not found."""

    def __init__(self, workout_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            resource_type="Workout",
            resource_id=workout_id,
            details=details,
        )
        self.code = ErrorCode.WORKOUT_NOT_FOUND


class PlanNotFoundError(NotFoundError):
    """Raised when a training plan is not found."""

    def __init__(self, plan_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            resource_type="Training Plan",
            resource_id=plan_id,
            details=details,
        )
        self.code = ErrorCode.PLAN_NOT_FOUND


# ============================================================================
# Conflict Errors (409)
# ============================================================================

class ConflictError(ReactiveTrainingError):
    """Raised when there's a resource conflict."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.CONFLICT,
            status_code=409,
            details=details,
        )


class PlanAlreadyActiveError(ConflictError):
    """Raised when trying to activate a plan when another is already active."""

    def __init__(
        self,
        active_plan_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        error_details["active_plan_id"] = active_plan_id
        super().__init__(
            message=f"Cannot activate plan. Plan '{active_plan_id}' is already active.",
            details=error_details,
        )
        self.code = ErrorCode.PLAN_ALREADY_ACTIVE


# ============================================================================
# LLM Service Errors (500/503)
# ============================================================================

class LLMError(ReactiveTrainingError):
    """Base class for LLM-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.LLM_API_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class LLMServiceUnavailableError(LLMError):
    """Raised when the LLM service is unavailable."""

    def __init__(
        self,
        message: str = "LLM service is currently unavailable",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.LLM_SERVICE_UNAVAILABLE,
            status_code=503,
            details=details,
        )


class LLMRateLimitError(LLMError):
    """Raised when LLM rate limits are hit."""

    def __init__(
        self,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        if retry_after:
            error_details["retry_after_seconds"] = retry_after
        super().__init__(
            message="LLM service rate limit exceeded. Please try again later.",
            code=ErrorCode.LLM_RATE_LIMITED,
            status_code=429,
            details=error_details,
        )


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""

    def __init__(
        self,
        timeout_seconds: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        if timeout_seconds:
            error_details["timeout_seconds"] = timeout_seconds
        super().__init__(
            message="LLM request timed out",
            code=ErrorCode.LLM_TIMEOUT,
            status_code=504,
            details=error_details,
        )


class LLMResponseInvalidError(LLMError):
    """Raised when LLM response cannot be parsed."""

    def __init__(
        self,
        message: str = "Failed to parse LLM response",
        raw_response: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        if raw_response:
            error_details["raw_response_preview"] = raw_response[:500]
        super().__init__(
            message=message,
            code=ErrorCode.LLM_RESPONSE_INVALID,
            status_code=500,
            details=error_details,
        )


# ============================================================================
# Analysis Errors
# ============================================================================

class AnalysisError(ReactiveTrainingError):
    """Raised when workout analysis fails."""

    def __init__(
        self,
        message: str,
        workout_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        if workout_id:
            error_details["workout_id"] = workout_id
        super().__init__(
            message=message,
            code=ErrorCode.WORKOUT_ANALYSIS_FAILED,
            status_code=500,
            details=error_details,
        )


# ============================================================================
# Plan Generation Errors
# ============================================================================

class PlanGenerationError(ReactiveTrainingError):
    """Raised when plan generation fails."""

    def __init__(
        self,
        message: str,
        phase: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        if phase:
            error_details["failed_at_phase"] = phase
        super().__init__(
            message=message,
            code=ErrorCode.PLAN_GENERATION_FAILED,
            status_code=500,
            details=error_details,
        )


class PlanAdaptationError(ReactiveTrainingError):
    """Raised when plan adaptation fails."""

    def __init__(
        self,
        message: str,
        plan_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        if plan_id:
            error_details["plan_id"] = plan_id
        super().__init__(
            message=message,
            code=ErrorCode.PLAN_ADAPTATION_FAILED,
            status_code=500,
            details=error_details,
        )


# ============================================================================
# FIT/Garmin Errors
# ============================================================================

class FITError(ReactiveTrainingError):
    """Base class for FIT file errors."""
    pass


class FITEncodingError(FITError):
    """Raised when FIT file encoding fails."""

    def __init__(
        self,
        message: str = "Failed to encode FIT file",
        workout_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        if workout_id:
            error_details["workout_id"] = workout_id
        super().__init__(
            message=message,
            code=ErrorCode.FIT_ENCODING_ERROR,
            status_code=500,
            details=error_details,
        )


class FITDecodingError(FITError):
    """Raised when FIT file decoding fails."""

    def __init__(
        self,
        message: str = "Failed to decode FIT file",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.FIT_DECODING_ERROR,
            status_code=400,
            details=details,
        )


class GarminConnectionError(ReactiveTrainingError):
    """Raised when Garmin Connect connection fails."""

    def __init__(
        self,
        message: str = "Failed to connect to Garmin Connect",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.GARMIN_CONNECTION_ERROR,
            status_code=503,
            details=details,
        )


class GarminNotConfiguredError(ReactiveTrainingError):
    """Raised when Garmin Connect is not configured."""

    def __init__(
        self,
        message: str = "Garmin Connect integration not configured",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.GARMIN_NOT_CONFIGURED,
            status_code=501,
            details=details,
        )


# ============================================================================
# Database Errors
# ============================================================================

class DatabaseError(ReactiveTrainingError):
    """Raised when a database operation fails."""

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        if operation:
            error_details["operation"] = operation
        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_ERROR,
            status_code=500,
            details=error_details,
        )


class DataIntegrityError(DatabaseError):
    """Raised when data integrity is violated."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message=message, details=details)
        self.code = ErrorCode.DATA_INTEGRITY_ERROR
