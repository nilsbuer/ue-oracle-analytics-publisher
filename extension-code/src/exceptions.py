"""
Exceptions module for the Oracle Analytics Publisher Asynchronous Report Scheduler extension.

This module provides:
- Base ExecutionError class
- Standard exception types (DataValidationError, UnexpectedSystemError)
- Domain-specific exceptions for Oracle Analytics Publisher interactions
- Exit code conventions

Exit code guide:
  0  — Successful execution (not an exception)
  1  — Execution failure (transport, SOAP, Oracle job, and polling errors)
  20 — Input validation error (user configuration or input error, before any Oracle API call)
"""
from typing import Optional


class ExecutionError(Exception):
    """
    The default error raised by an extension.

    All extension errors must inherit from it.

    Attrs:
        exit_code: The exit code of the extension (for UAC)
        message: The error message for status description
    """

    exit_code: int = 1
    message: str = "Execution Failed"

    def __init__(self, message: Optional[str] = None):
        """
        Initialize exception.

        Args:
            message: Optional message that will be appended to the default message.

        Note:
            To return result data with errors, use error_manager.set_result()
            before raising the exception.
        """
        if message:
            self.message = f"{self.message}: {message}"

        super().__init__(self.message)


class DataValidationError(ExecutionError):
    """Raised when an input field is invalid."""
    exit_code = 20
    message = "Data Validation Error"


class UnexpectedSystemError(ExecutionError):
    """Raised for unexpected system errors."""
    exit_code = 1
    message = "System Error"


# ---------------------------------------------------------------------------
# Input Validation
# ---------------------------------------------------------------------------

class InputValidationError(ExecutionError):
    """
    Raised when one or more input fields fail pre-flight validation.

    Use this exception when field values are missing, malformed, or violate
    business rules (e.g., invalid URL scheme, report path not ending in .xdo,
    invalid JSON in report_parameters, negative retry count). All violations
    should be collected before raising so the user receives a single,
    comprehensive error message. Exit code 20 signals a user configuration
    error that is non-retryable.
    """
    exit_code = 20
    message = "Input Validation Error"


# ---------------------------------------------------------------------------
# HTTP Authentication and Authorization Errors (submission only, non-retryable)
# ---------------------------------------------------------------------------

class OracleAuthenticationError(ExecutionError):
    """
    Raised when the Oracle Analytics Publisher SOAP endpoint returns HTTP 401.

    Indicates that the supplied credentials (username or password) were rejected
    by Oracle. The task should not be retried without correcting the credential
    configuration. Credentials must never appear in the exception message.
    """
    exit_code = 1
    message = "Oracle Authentication Error"


class OracleAuthorizationError(ExecutionError):
    """
    Raised when the Oracle Analytics Publisher SOAP endpoint returns HTTP 403.

    Indicates that the authenticated user lacks the permissions required to
    access the requested resource or execute the report. Correct the Oracle
    user's role or catalog permissions before retrying.
    """
    exit_code = 1
    message = "Oracle Authorization Error"


class OracleEndpointNotFoundError(ExecutionError):
    """
    Raised when the Oracle Analytics Publisher SOAP endpoint returns HTTP 404.

    Indicates that the schedule_service_url does not point to a valid Oracle
    ScheduleService endpoint. Verify the URL for the target environment
    (DEV, TEST, PROD) before retrying.
    """
    exit_code = 1
    message = "Oracle Endpoint Not Found"


# ---------------------------------------------------------------------------
# Transport and Connection Errors
# ---------------------------------------------------------------------------

class OracleConnectionError(ExecutionError):
    """
    Raised on a connection-level error that occurs before the request body
    has been transmitted (e.g., DNS resolution failure, connection refused,
    network unreachable).

    Because the request was never sent, there is no risk of a duplicate Oracle
    job being created. The task is non-retryable until the network or DNS
    issue is resolved.
    """
    exit_code = 1
    message = "Oracle Connection Error"


class AmbiguousSubmissionError(ExecutionError):
    """
    Raised when a timeout or connection reset occurs during the scheduleReport
    call after the request body may have already been transmitted to Oracle.

    The Oracle Publisher server may or may not have received and processed the
    request. To prevent duplicate Oracle job creation the task is not retried
    automatically. Operators must check Oracle Publisher manually using the
    job name included in this error message before deciding whether to re-run.
    Credentials must never appear in the exception message.
    """
    exit_code = 1
    message = "Ambiguous Submission Error"


class OracleTransientError(ExecutionError):
    """
    Raised when all transient-retry attempts for a getScheduledReportStatus
    poll request are exhausted.

    Transient errors include HTTP 408, 429, 5xx responses and read timeouts.
    The number of retry attempts is controlled by the UE_POLL_RETRY_COUNT
    environment variable (default 3). The overall elapsed timer is not reset
    between retries. Once all retries are exhausted this exception is raised
    and the task fails.
    """
    exit_code = 1
    message = "Oracle Transient Error"


# ---------------------------------------------------------------------------
# SOAP Response Errors
# ---------------------------------------------------------------------------

class OracleSoapFaultError(ExecutionError):
    """
    Raised when the scheduleReport SOAP response contains a Fault element.

    Indicates that Oracle rejected the report submission request. The fault
    may reflect an Oracle server error or a problem with the submitted SOAP
    request (e.g., invalid report path, unsupported format/template combination).
    Includes the faultcode and faultstring extracted from the Fault element.
    """
    exit_code = 1
    message = "Oracle SOAP Fault"


class OracleSoapFaultStatusError(ExecutionError):
    """
    Raised when a getScheduledReportStatus SOAP response contains a Fault element.

    Indicates that Oracle returned a fault while the extension was polling job
    status. Includes the Job ID being polled and the faultstring from the
    Fault element. This error is not retried regardless of the fault type.
    """
    exit_code = 1
    message = "Oracle SOAP Fault During Status Poll"


class MissingJobIdError(ExecutionError):
    """
    Raised when the scheduleReport SOAP response is a valid 2xx response with
    no SOAP Fault, but the scheduleReportReturn element is absent or empty.

    Indicates an unexpected Oracle response format where a Job ID cannot be
    extracted. Without a Job ID the extension cannot poll job status.
    """
    exit_code = 1
    message = "Missing Job ID In Oracle Response"


class OracleParseError(ExecutionError):
    """
    Raised when any Oracle SOAP response contains malformed XML that cannot
    be parsed by xml.etree.ElementTree.

    May occur during either the scheduleReport response or any
    getScheduledReportStatus response. Includes enough context to identify
    which operation returned the unparseable response.
    """
    exit_code = 1
    message = "Oracle Response Parse Error"


# ---------------------------------------------------------------------------
# Oracle Status and Business Logic Errors
# ---------------------------------------------------------------------------

class PublisherJobFailedError(ExecutionError):
    """
    Raised when Oracle Analytics Publisher returns a failure terminal status
    during the polling loop.

    Failure terminal statuses include: failed, error, canceled, cancelled,
    output has error, delivery has error, update status has error, deleted,
    skipped, suspended. The exception message includes the Oracle Job ID,
    the raw (non-normalized) status string returned by Oracle, and the Oracle
    message field from the status response.
    """
    exit_code = 1
    message = "Oracle Publisher Job Failed"


class PollTimeoutError(ExecutionError):
    """
    Raised when the elapsed polling time exceeds maximum_wait_seconds without
    Oracle returning a terminal job status.

    The exception message includes the Oracle Job ID and the last known status
    value at the time of timeout. Operators should increase maximum_wait_seconds
    or investigate the report in Oracle Publisher if it is genuinely long-running.
    """
    exit_code = 1
    message = "Poll Timeout Exceeded"


class UnknownStatusThresholdError(ExecutionError):
    """
    Raised when the count of consecutive unrecognized Oracle job status values
    exceeds the unknown_status_retry_count configuration.

    The counter increments each time Oracle returns a status string that does
    not match any known successful terminal, failure terminal, or in-progress
    value. The counter resets to zero whenever a recognized status is returned.
    The exception message includes the raw unrecognized status, the Oracle Job
    ID, and the consecutive count that triggered the threshold.
    """
    exit_code = 1
    message = "Unknown Status Threshold Exceeded"


class InconsistentJobIdError(ExecutionError):
    """
    Raised when the jobID value in a getScheduledReportStatus response differs
    from the Job ID that was submitted or preserved from a previous run.

    Indicates an unexpected Oracle response integrity issue. The exception
    message includes both the expected Job ID and the Job ID returned by Oracle
    to assist with manual investigation.
    """
    exit_code = 1
    message = "Inconsistent Job ID In Oracle Status Response"
