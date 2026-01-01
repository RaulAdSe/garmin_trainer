"""Prompt sanitization utilities for LLM injection risk mitigation.

This module provides basic input sanitization for user messages before they
are passed to the LLM. It does NOT block requests, only logs suspicious
patterns for monitoring.

The goal is defense-in-depth: detect and monitor potential injection attempts
while relying on the LLM's built-in safety measures and the single-user nature
of this application.

Security Context:
- Single-user application
- LLM has read-only data access
- Rate limiting applied at API level
- This is a monitoring/alerting layer, not a blocking layer
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class InjectionRiskLevel(Enum):
    """Risk level for detected injection patterns."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SanitizationResult:
    """Result of prompt sanitization analysis."""
    original_message: str
    risk_level: InjectionRiskLevel
    patterns_detected: List[str]
    warnings: List[str]
    is_suspicious: bool

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "risk_level": self.risk_level.value,
            "patterns_detected": self.patterns_detected,
            "warnings": self.warnings,
            "is_suspicious": self.is_suspicious,
            "message_length": len(self.original_message),
        }


# Common injection patterns to detect
# These are patterns that may indicate prompt injection attempts
INJECTION_PATTERNS: List[Tuple[str, str, InjectionRiskLevel]] = [
    # Instruction override attempts (HIGH risk)
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|guidelines?)",
     "instruction_override", InjectionRiskLevel.HIGH),
    (r"disregard\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|guidelines?)",
     "instruction_override", InjectionRiskLevel.HIGH),
    (r"forget\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|guidelines?)",
     "instruction_override", InjectionRiskLevel.HIGH),
    (r"override\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|guidelines?)",
     "instruction_override", InjectionRiskLevel.HIGH),

    # System prompt extraction attempts (HIGH risk)
    (r"(show|reveal|display|print|output|tell\s+me)\s+(your|the)\s+system\s+prompt",
     "system_prompt_extraction", InjectionRiskLevel.HIGH),
    (r"what\s+(is|are)\s+your\s+(system\s+)?(instructions?|prompts?|rules?|guidelines?)",
     "system_prompt_extraction", InjectionRiskLevel.HIGH),
    (r"(repeat|echo|recite)\s+(your|the)\s+(system\s+)?(prompt|instructions?)",
     "system_prompt_extraction", InjectionRiskLevel.HIGH),

    # Role manipulation attempts (HIGH risk)
    (r"you\s+are\s+now\s+(a|an|the)\s+",
     "role_manipulation", InjectionRiskLevel.HIGH),
    (r"pretend\s+(you\s+are|to\s+be)\s+(a|an|the)\s+",
     "role_manipulation", InjectionRiskLevel.HIGH),
    (r"act\s+as\s+(a|an|the|if\s+you\s+were)\s+",
     "role_manipulation", InjectionRiskLevel.MEDIUM),
    (r"from\s+now\s+on\s+(you\s+)?(are|will|must|should)",
     "role_manipulation", InjectionRiskLevel.HIGH),

    # Developer/admin mode attempts (HIGH risk)
    (r"(enter|enable|activate|switch\s+to)\s+(developer|admin|debug|root|sudo)\s+mode",
     "privilege_escalation", InjectionRiskLevel.HIGH),
    (r"(developer|admin|debug|root|sudo)\s+mode\s+(enabled|activated|on)",
     "privilege_escalation", InjectionRiskLevel.HIGH),
    (r"\[system\]|\[admin\]|\[developer\]|\[debug\]",
     "fake_system_tag", InjectionRiskLevel.HIGH),

    # Jailbreak attempts (MEDIUM-HIGH risk)
    (r"(dan|do\s+anything\s+now)\s+(mode|prompt|jailbreak)",
     "jailbreak_attempt", InjectionRiskLevel.HIGH),
    (r"(ignore|bypass|circumvent|break|escape)\s+(safety|security|restrictions?|filters?|rules?)",
     "jailbreak_attempt", InjectionRiskLevel.HIGH),

    # Output format manipulation (MEDIUM risk)
    (r"(respond|reply|answer)\s+(only\s+)?(with|in)\s+(json|xml|code|base64|hex)",
     "output_manipulation", InjectionRiskLevel.MEDIUM),
    (r"(encode|encrypt|obfuscate)\s+(your|the)\s+(response|output|answer)",
     "output_manipulation", InjectionRiskLevel.MEDIUM),

    # Hidden instruction patterns (MEDIUM risk)
    (r"<\s*(system|admin|hidden|secret)\s*>",
     "hidden_instruction", InjectionRiskLevel.MEDIUM),
    (r"\[\s*(system|admin|hidden|secret)\s*\]",
     "hidden_instruction", InjectionRiskLevel.MEDIUM),

    # Data exfiltration attempts (MEDIUM risk)
    (r"(send|transmit|post|share)\s+(data|info|information)\s+to",
     "data_exfiltration", InjectionRiskLevel.MEDIUM),
    (r"(make|send|call)\s+(a|an)?\s*(api|http|web)\s*(request|call)",
     "data_exfiltration", InjectionRiskLevel.MEDIUM),

    # Prompt leaking (LOW risk)
    (r"(what|how)\s+(is|are|was)\s+(your|this)\s+(prompt|training|fine-?tuning)",
     "prompt_leak_attempt", InjectionRiskLevel.LOW),
]


def detect_injection_patterns(message: str) -> List[Tuple[str, InjectionRiskLevel]]:
    """Detect common injection patterns in a message.

    Args:
        message: The user's message to analyze

    Returns:
        List of (pattern_name, risk_level) tuples for detected patterns
    """
    detected = []
    message_lower = message.lower()

    for pattern, name, risk_level in INJECTION_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            detected.append((name, risk_level))

    return detected


def get_highest_risk_level(
    patterns: List[Tuple[str, InjectionRiskLevel]]
) -> InjectionRiskLevel:
    """Get the highest risk level from detected patterns.

    Args:
        patterns: List of (pattern_name, risk_level) tuples

    Returns:
        The highest risk level found, or NONE if no patterns
    """
    if not patterns:
        return InjectionRiskLevel.NONE

    risk_order = {
        InjectionRiskLevel.NONE: 0,
        InjectionRiskLevel.LOW: 1,
        InjectionRiskLevel.MEDIUM: 2,
        InjectionRiskLevel.HIGH: 3,
    }

    max_risk = InjectionRiskLevel.NONE
    for _, risk in patterns:
        if risk_order[risk] > risk_order[max_risk]:
            max_risk = risk

    return max_risk


def sanitize_prompt(
    message: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    log_suspicious: bool = True,
) -> SanitizationResult:
    """Analyze and sanitize a user prompt for injection risks.

    This function:
    1. Detects common injection patterns
    2. Logs suspicious inputs for monitoring
    3. Returns analysis results (does NOT block or modify the message)

    Args:
        message: The user's message to analyze
        user_id: Optional user ID for logging context
        session_id: Optional session ID for logging context
        log_suspicious: Whether to log suspicious patterns (default True)

    Returns:
        SanitizationResult with analysis details
    """
    # Detect patterns
    detected_patterns = detect_injection_patterns(message)
    risk_level = get_highest_risk_level(detected_patterns)

    # Build warnings based on detected patterns
    warnings = []
    pattern_names = [name for name, _ in detected_patterns]

    if "instruction_override" in pattern_names:
        warnings.append("Message contains instruction override attempt")
    if "system_prompt_extraction" in pattern_names:
        warnings.append("Message attempts to extract system prompt")
    if "role_manipulation" in pattern_names:
        warnings.append("Message attempts to manipulate AI role")
    if "privilege_escalation" in pattern_names:
        warnings.append("Message attempts privilege escalation")
    if "jailbreak_attempt" in pattern_names:
        warnings.append("Message contains potential jailbreak attempt")
    if "data_exfiltration" in pattern_names:
        warnings.append("Message may attempt data exfiltration")

    is_suspicious = risk_level in (InjectionRiskLevel.MEDIUM, InjectionRiskLevel.HIGH)

    result = SanitizationResult(
        original_message=message,
        risk_level=risk_level,
        patterns_detected=pattern_names,
        warnings=warnings,
        is_suspicious=is_suspicious,
    )

    # Log suspicious inputs for monitoring
    if log_suspicious and is_suspicious:
        log_suspicious_input(result, user_id, session_id)

    return result


def log_suspicious_input(
    result: SanitizationResult,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Log a suspicious input for monitoring and analysis.

    Args:
        result: The sanitization result to log
        user_id: Optional user ID for context
        session_id: Optional session ID for context
    """
    # Build log message with context
    context_parts = []
    if user_id:
        context_parts.append(f"user={user_id}")
    if session_id:
        context_parts.append(f"session={session_id[:8]}...")

    context_str = f" [{', '.join(context_parts)}]" if context_parts else ""

    # Truncate message for logging (don't log full potentially malicious content)
    truncated_message = result.original_message[:100]
    if len(result.original_message) > 100:
        truncated_message += "..."

    logger.warning(
        f"[PROMPT_SANITIZER] Suspicious input detected{context_str} | "
        f"risk={result.risk_level.value} | "
        f"patterns={result.patterns_detected} | "
        f"message_preview='{truncated_message}'"
    )


def get_user_warning(result: SanitizationResult) -> Optional[str]:
    """Generate an optional user-facing warning for suspicious inputs.

    This is intentionally gentle and non-blocking - just informational.

    Args:
        result: The sanitization result

    Returns:
        Optional warning message for the user, or None if not needed
    """
    if not result.is_suspicious:
        return None

    if result.risk_level == InjectionRiskLevel.HIGH:
        return (
            "Note: Your message contains patterns that may be interpreted differently "
            "than intended. If you're asking a legitimate training question, please "
            "try rephrasing it."
        )

    return None
