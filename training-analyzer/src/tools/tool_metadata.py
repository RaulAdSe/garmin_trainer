"""
Human-friendly tool status messages for the agentic AI coach.

This module provides:
1. TOOL_STATUS_MESSAGES - Human-readable status messages for each tool
2. get_tool_start_message() - Get the "in progress" message for a tool
3. get_tool_end_message() - Get the completion message with dynamic result info
4. ToolStatusEmitter - Class for emitting tool status updates during streaming

These messages help users understand what the AI agent is doing while
processing their requests.
"""

from typing import Any, Dict, Optional


# Human-friendly status messages for each tool
# Each tool has a "start" message (shown when tool begins) and
# an "end" template (shown when tool completes, may include result info)
TOOL_STATUS_MESSAGES: Dict[str, Dict[str, str]] = {
    # Query Tools
    "query_workouts": {
        "start": "Checking your workout history...",
        "end": "Found {count} workouts",
    },
    "query_wellness": {
        "start": "Gathering wellness and recovery data...",
        "end": "Retrieved {count} days of wellness data",
    },
    "get_athlete_profile": {
        "start": "Loading your fitness profile...",
        "end": "Profile loaded",
    },
    "get_training_patterns": {
        "start": "Analyzing your training patterns...",
        "end": "Patterns detected",
    },
    "get_fitness_metrics": {
        "start": "Calculating fitness trends...",
        "end": "Metrics ready",
    },
    "get_garmin_data": {
        "start": "Fetching Garmin Connect data...",
        "end": "Garmin data retrieved",
    },
    "compare_workouts": {
        "start": "Comparing workouts side-by-side...",
        "end": "Comparison complete",
    },
    # Action Tools
    "create_training_plan": {
        "start": "Designing your training plan...",
        "end": "Plan created",
    },
    "design_workout": {
        "start": "Creating a personalized workout...",
        "end": "Workout designed",
    },
    "log_note": {
        "start": "Saving your note...",
        "end": "Note saved",
    },
    "set_goal": {
        "start": "Setting your goal...",
        "end": "Goal saved",
    },
}


def get_tool_start_message(tool_name: str) -> str:
    """Get the human-friendly start message for a tool.

    Args:
        tool_name: The name of the tool (e.g., "query_workouts")

    Returns:
        A user-friendly message describing what the tool is doing,
        or a generic message if the tool is not recognized.

    Example:
        >>> get_tool_start_message("query_workouts")
        "Checking your workout history..."
    """
    if tool_name in TOOL_STATUS_MESSAGES:
        return TOOL_STATUS_MESSAGES[tool_name]["start"]

    # Default message for unknown tools
    # Convert tool_name from snake_case to a readable format
    readable_name = tool_name.replace("_", " ")
    return f"Running {readable_name}..."


def get_tool_end_message(tool_name: str, result: Any = None) -> str:
    """Get the human-friendly end message, optionally with result summary.

    This function attempts to extract useful information from the tool result
    to provide a more informative completion message.

    Args:
        tool_name: The name of the tool (e.g., "query_workouts")
        result: The result returned by the tool (optional)

    Returns:
        A user-friendly completion message, potentially with dynamic
        information extracted from the result.

    Examples:
        >>> get_tool_end_message("query_workouts", [{"id": 1}, {"id": 2}])
        "Found 2 workouts"

        >>> get_tool_end_message("get_athlete_profile", {"ctl": 45, "tsb": -8})
        "Profile loaded - CTL: 45, TSB: -8"
    """
    if tool_name not in TOOL_STATUS_MESSAGES:
        return "Done"

    base_message = TOOL_STATUS_MESSAGES[tool_name]["end"]

    # Generate dynamic messages based on result content
    if result is None:
        # Remove placeholders from message if no result
        if "{count}" in base_message:
            return base_message.replace("{count}", "0")
        return base_message

    # Handle query_workouts - count the workouts found
    if tool_name == "query_workouts":
        count = _count_items(result)
        return base_message.format(count=count)

    # Handle query_wellness - count days of data
    if tool_name == "query_wellness":
        count = _count_items(result)
        return base_message.format(count=count)

    # Handle get_athlete_profile - show key metrics summary
    if tool_name == "get_athlete_profile":
        summary = _extract_fitness_summary(result)
        if summary:
            return f"{base_message} - {summary}"
        return base_message

    # Handle get_fitness_metrics - show current values
    if tool_name == "get_fitness_metrics":
        summary = _extract_fitness_metrics_summary(result)
        if summary:
            return f"{base_message} - {summary}"
        return base_message

    # Handle get_training_patterns - show detected patterns count
    if tool_name == "get_training_patterns":
        pattern_count = _count_patterns(result)
        if pattern_count > 0:
            return f"{pattern_count} patterns detected"
        return base_message

    # Handle compare_workouts - show comparison count
    if tool_name == "compare_workouts":
        workout_count = _count_compared_workouts(result)
        if workout_count > 0:
            return f"Compared {workout_count} workouts"
        return base_message

    # Handle action tools with success/failure status
    if tool_name in ("create_training_plan", "design_workout", "log_note", "set_goal"):
        if isinstance(result, dict):
            if result.get("success") is False:
                error_msg = result.get("message", "Operation failed")
                return f"Failed: {error_msg}"
            if result.get("message"):
                return result["message"]
        return base_message

    return base_message


def _count_items(result: Any) -> int:
    """Count items in a result (works for lists, dicts with items, etc.)."""
    if isinstance(result, list):
        return len(result)
    if isinstance(result, dict):
        # Check for common list keys
        for key in ("workouts", "items", "data", "results", "activities"):
            if key in result and isinstance(result[key], list):
                return len(result[key])
        # Check for string result (from langchain tools that return formatted strings)
        if "Found" in str(result) and "workout" in str(result).lower():
            # Try to extract count from "Found X workout(s)" message
            import re
            match = re.search(r"Found (\d+)", str(result))
            if match:
                return int(match.group(1))
    if isinstance(result, str):
        # Try to extract count from formatted string output
        import re
        match = re.search(r"Found (\d+)", result)
        if match:
            return int(match.group(1))
    return 0


def _extract_fitness_summary(result: Any) -> Optional[str]:
    """Extract key fitness metrics for profile summary."""
    if not isinstance(result, dict):
        return None

    parts = []

    # Try to get CTL
    ctl = result.get("ctl")
    if ctl is None and "fitness" in result:
        ctl = result["fitness"].get("ctl")
    if ctl is not None:
        parts.append(f"CTL: {ctl:.0f}" if isinstance(ctl, float) else f"CTL: {ctl}")

    # Try to get TSB
    tsb = result.get("tsb")
    if tsb is None and "fitness" in result:
        tsb = result["fitness"].get("tsb")
    if tsb is not None:
        parts.append(f"TSB: {tsb:+.0f}" if isinstance(tsb, float) else f"TSB: {tsb}")

    # Try to get readiness score
    readiness = result.get("readiness_score")
    if readiness is None and "readiness" in result:
        readiness = result["readiness"].get("score")
    if readiness is not None:
        parts.append(f"Readiness: {readiness}")

    if parts:
        return ", ".join(parts)
    return None


def _extract_fitness_metrics_summary(result: Any) -> Optional[str]:
    """Extract key metrics from fitness metrics result."""
    if not isinstance(result, dict):
        return None

    # Check for current metrics
    current = result.get("current", {})
    if not current and isinstance(result, dict):
        current = result  # Result might be flat

    parts = []

    ctl = current.get("ctl")
    if ctl is not None:
        parts.append(f"CTL: {ctl:.0f}" if isinstance(ctl, float) else f"CTL: {ctl}")

    tsb = current.get("tsb")
    if tsb is not None:
        parts.append(f"TSB: {tsb:+.0f}" if isinstance(tsb, float) else f"TSB: {tsb}")

    # Check for trend
    trends = result.get("trends", {})
    ctl_trend = trends.get("ctl_trend")
    if ctl_trend:
        trend_emoji = {"improving": "up", "declining": "down", "stable": "stable"}.get(
            ctl_trend, ""
        )
        if trend_emoji:
            parts.append(f"Trend: {ctl_trend}")

    if parts:
        return ", ".join(parts)
    return None


def _count_patterns(result: Any) -> int:
    """Count detected patterns in training analysis result."""
    if not isinstance(result, dict):
        return 0

    # Check for detected_patterns list
    patterns = result.get("detected_patterns", [])
    if isinstance(patterns, list):
        return len(patterns)

    return 0


def _count_compared_workouts(result: Any) -> int:
    """Count workouts in comparison result."""
    if not isinstance(result, dict):
        return 0

    # Check for workouts list
    workouts = result.get("workouts", [])
    if isinstance(workouts, list):
        return len(workouts)

    # Check for insights
    insights = result.get("insights", {})
    if isinstance(insights, dict):
        return insights.get("workouts_compared", 0)

    return 0


class ToolStatusEmitter:
    """Emits tool status updates for streaming responses.

    This class provides a consistent interface for emitting tool status
    updates that can be sent to the client during streaming agent execution.

    Usage:
        emitter = ToolStatusEmitter()

        # When a tool starts
        status = emitter.on_tool_start("query_workouts")
        # Returns: {"type": "tool_start", "tool": "query_workouts",
        #           "message": "Checking your workout history..."}

        # When a tool completes
        status = emitter.on_tool_end("query_workouts", result)
        # Returns: {"type": "tool_end", "tool": "query_workouts",
        #           "message": "Found 5 workouts"}
    """

    def on_tool_start(self, tool_name: str) -> Dict[str, Any]:
        """Generate a status update when a tool starts executing.

        Args:
            tool_name: The name of the tool that is starting

        Returns:
            A dict with type="tool_start", tool name, and human-friendly message
        """
        return {
            "type": "tool_start",
            "tool": tool_name,
            "message": get_tool_start_message(tool_name),
        }

    def on_tool_end(self, tool_name: str, result: Any = None) -> Dict[str, Any]:
        """Generate a status update when a tool finishes executing.

        Args:
            tool_name: The name of the tool that completed
            result: The result returned by the tool (optional, used for
                    generating dynamic completion messages)

        Returns:
            A dict with type="tool_end", tool name, and human-friendly message
        """
        return {
            "type": "tool_end",
            "tool": tool_name,
            "message": get_tool_end_message(tool_name, result),
        }

    def on_tool_error(self, tool_name: str, error: str) -> Dict[str, Any]:
        """Generate a status update when a tool encounters an error.

        Args:
            tool_name: The name of the tool that failed
            error: The error message

        Returns:
            A dict with type="tool_error", tool name, and error message
        """
        # Get a user-friendly name for the tool
        readable_name = tool_name.replace("_", " ")
        return {
            "type": "tool_error",
            "tool": tool_name,
            "message": f"Error while {readable_name}: {error}",
        }


# Singleton instance for convenience
_status_emitter: Optional[ToolStatusEmitter] = None


def get_status_emitter() -> ToolStatusEmitter:
    """Get the singleton ToolStatusEmitter instance.

    Returns:
        The shared ToolStatusEmitter instance
    """
    global _status_emitter
    if _status_emitter is None:
        _status_emitter = ToolStatusEmitter()
    return _status_emitter


__all__ = [
    "TOOL_STATUS_MESSAGES",
    "get_tool_start_message",
    "get_tool_end_message",
    "ToolStatusEmitter",
    "get_status_emitter",
]
