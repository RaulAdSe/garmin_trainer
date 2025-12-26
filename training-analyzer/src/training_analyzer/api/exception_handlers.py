"""
Exception handlers for the FastAPI application.

This module registers exception handlers that convert application
exceptions to appropriate HTTP responses with consistent formatting.
"""

from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from ..exceptions import (
    ReactiveTrainingError,
    ValidationError,
    NotFoundError,
    ConflictError,
    LLMError,
    LLMRateLimitError,
    FITError,
    DatabaseError,
)


def create_error_response(
    status_code: int,
    code: str,
    message: str,
    details: Dict[str, Any] | None = None,
) -> JSONResponse:
    """Create a standardized error response."""
    content: Dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        content["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=content)


async def reactive_training_error_handler(
    request: Request,
    exc: ReactiveTrainingError,
) -> JSONResponse:
    """Handle all ReactiveTrainingError exceptions."""
    return create_error_response(
        status_code=exc.status_code,
        code=exc.code.value,
        message=exc.message,
        details=exc.details if exc.details else None,
    )


async def pydantic_validation_error_handler(
    request: Request,
    exc: PydanticValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        loc = ".".join(str(x) for x in error["loc"])
        errors.append({
            "field": loc,
            "message": error["msg"],
            "type": error["type"],
        })

    return create_error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"errors": errors},
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected exceptions."""
    import logging
    import traceback

    logger = logging.getLogger("reactive_training.api")
    logger.error(
        f"Unhandled exception: {exc}\n{traceback.format_exc()}"
    )

    return create_error_response(
        status_code=500,
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI application.

    Args:
        app: The FastAPI application instance
    """
    # Register handlers for our custom exceptions
    app.add_exception_handler(ReactiveTrainingError, reactive_training_error_handler)

    # Register handler for Pydantic validation errors
    app.add_exception_handler(PydanticValidationError, pydantic_validation_error_handler)

    # Register generic handler for unexpected exceptions
    # Note: This should be last as it catches all Exception types
    app.add_exception_handler(Exception, generic_exception_handler)
