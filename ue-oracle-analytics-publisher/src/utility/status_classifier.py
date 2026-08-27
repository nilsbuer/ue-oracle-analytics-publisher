"""
Status Normalizer and Classifier for Oracle Analytics Publisher job status strings.

Normalizes raw Oracle job status strings and classifies them into one of four
actionable categories: successful_terminal, failure_terminal, in_progress,
or unknown.
"""
import logging
import re
from enum import Enum

logger = logging.getLogger("UNV")

# Internal whitespace collapse pattern
_WHITESPACE_PATTERN = re.compile(r"\s+")

# Status classification sets (all entries are lowercase normalized strings)
_SUCCESSFUL_TERMINAL: frozenset[str] = frozenset({"success", "completed", "done"})

_FAILURE_TERMINAL: frozenset[str] = frozenset(
    {
        "failed",
        "error",
        "canceled",
        "cancelled",
        "output has error",
        "delivery has error",
        "update status has error",
        "deleted",
        "skipped",
        "suspended",
    }
)

_IN_PROGRESS: frozenset[str] = frozenset(
    {"scheduled", "waiting", "running", "cancelling"}
)


class StatusCategory(Enum):
    """Enumeration of Oracle job status categories.

    Values:
        SUCCESSFUL_TERMINAL: Oracle reports the job completed successfully.
        FAILURE_TERMINAL: Oracle reports the job ended in a failure state.
        IN_PROGRESS: Oracle reports the job is still executing.
        UNKNOWN: The status string did not match any known category.
    """
    SUCCESSFUL_TERMINAL = "successful_terminal"
    FAILURE_TERMINAL = "failure_terminal"
    IN_PROGRESS = "in_progress"
    UNKNOWN = "unknown"


def normalize_status(raw_status: str) -> str:
    """Normalize a raw Oracle job status string.

    Applies the following transformations in order:
    1. Strip leading and trailing whitespace.
    2. Convert to lowercase.
    3. Collapse any sequence of internal whitespace to a single space.

    Args:
        raw_status: The raw Oracle ``jobStatus`` string.

    Returns:
        The normalized status string.
    """
    normalized = raw_status.strip().lower()
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
    logger.debug("normalize_status: '%s' -> '%s'", raw_status, normalized)
    return normalized


def classify_status(raw_status: str) -> tuple[StatusCategory, str]:
    """Classify a raw Oracle job status string into a :class:`StatusCategory`.

    Normalizes the raw string first, then matches against the known status
    sets.

    Args:
        raw_status: The raw Oracle ``jobStatus`` string as returned by the
            SOAP response.

    Returns:
        A tuple of ``(category, normalized_status)`` where ``category`` is
        the :class:`StatusCategory` and ``normalized_status`` is the
        normalized form of ``raw_status``.
    """
    normalized = normalize_status(raw_status)

    if normalized in _SUCCESSFUL_TERMINAL:
        category = StatusCategory.SUCCESSFUL_TERMINAL
    elif normalized in _FAILURE_TERMINAL:
        category = StatusCategory.FAILURE_TERMINAL
    elif normalized in _IN_PROGRESS:
        category = StatusCategory.IN_PROGRESS
    else:
        category = StatusCategory.UNKNOWN

    logger.debug(
        "classify_status: normalized='%s', category=%s", normalized, category.value
    )
    return category, normalized
