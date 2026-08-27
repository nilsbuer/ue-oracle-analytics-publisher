"""
Oracle HTTP Client for Oracle Analytics Publisher v2/ScheduleService.

Manages the requests.Session lifecycle, executes SOAP POST requests,
classifies HTTP and transport errors into domain exceptions, and implements
poll-phase retry logic.

Credentials must never appear in any exception message, log entry, or error
string emitted by this module.
"""
import logging
import os
import time
from typing import Optional

import certifi
import requests
import requests.exceptions

from exceptions import (
    AmbiguousSubmissionError,
    MissingJobIdError,
    OracleAuthenticationError,
    OracleAuthorizationError,
    OracleConnectionError,
    OracleEndpointNotFoundError,
    OracleParseError,
    OracleSoapFaultError,
    OracleSoapFaultStatusError,
    OracleTransientError,
)
from utility.soap_builder import (
    build_get_scheduled_report_status_envelope,
    build_schedule_report_envelope,
)
from utility.soap_parser import (
    ScheduledReportStatus,
    detect_fault,
    parse_schedule_report_return,
    parse_scheduled_report_status_return,
    parse_soap_response,
)

logger = logging.getLogger("UNV")

_CONTENT_TYPE = "text/xml; charset=utf-8"
_POLL_RETRY_BACKOFF_SECONDS = 2
_TRANSIENT_HTTP_CODES = {408, 429, 500, 502, 503, 504}


def _get_poll_retry_count() -> int:
    """Read the UE_POLL_RETRY_COUNT environment variable.

    Returns:
        Integer retry count; defaults to 3 when the variable is unset or
        cannot be parsed as a non-negative integer.
    """
    raw = os.environ.get("UE_POLL_RETRY_COUNT", "3")
    try:
        value = int(raw)
        return max(0, value)
    except ValueError:
        logger.warning(
            "UE_POLL_RETRY_COUNT='%s' is not a valid integer; defaulting to 3", raw
        )
        return 3


class OracleHttpClient:
    """Manages a requests.Session for Oracle Analytics Publisher SOAP calls.

    Handles session lifecycle, SOAP POST execution, error classification, and
    poll-phase transient retry logic. Credential values must never appear in
    any log, exception message, or raised error.

    Args:
        endpoint_url: Full SOAP endpoint URL for v2/ScheduleService.
        username: Oracle username for HTTP Basic Auth.
        password: Oracle password for HTTP Basic Auth.
        verify_tls: When True, TLS is verified using the certifi CA bundle.
            When False, TLS verification is disabled.
        connection_timeout: TCP/TLS connection timeout in seconds.
        request_timeout: Read/response timeout in seconds.
    """

    def __init__(
        self,
        endpoint_url: str,
        username: str,
        password: str,
        verify_tls: bool,
        connection_timeout: int,
        request_timeout: int,
    ) -> None:
        self._endpoint_url = endpoint_url
        self._connection_timeout = connection_timeout
        self._request_timeout = request_timeout
        self._poll_retry_count = _get_poll_retry_count()

        self._session = requests.Session()
        self._session.auth = (username, password)
        self._session.verify = certifi.where() if verify_tls else False

        logger.debug(
            "OracleHttpClient initialized: url=%s, verify_tls=%s, "
            "connect_timeout=%ds, request_timeout=%ds, poll_retry_count=%d",
            endpoint_url,
            verify_tls,
            connection_timeout,
            request_timeout,
            self._poll_retry_count,
        )

    def close(self) -> None:
        """Close the underlying requests.Session."""
        self._session.close()
        logger.debug("OracleHttpClient session closed")

    def __enter__(self) -> "OracleHttpClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def submit_report(
        self,
        job_name: str,
        **envelope_kwargs: object,
    ) -> str:
        """Execute a scheduleReport SOAP call and return the Oracle Job ID.

        Builds the SOAP envelope, posts it to the endpoint, classifies any
        HTTP or transport error, and returns the Job ID extracted from the
        SOAP response.

        Args:
            job_name: The resolved Oracle job name, used only in ambiguous
                submission error messages (no credentials included).
            **envelope_kwargs: Keyword arguments forwarded verbatim to
                :func:`build_schedule_report_envelope`.

        Returns:
            The Oracle scheduled Job ID string.

        Raises:
            OracleAuthenticationError: HTTP 401 response.
            OracleAuthorizationError: HTTP 403 response.
            OracleEndpointNotFoundError: HTTP 404 response.
            AmbiguousSubmissionError: Timeout or connection reset after the
                request body may have been transmitted.
            OracleConnectionError: Connection-level error before transmission.
            OracleSoapFaultError: SOAP Fault present in a 2xx response.
            MissingJobIdError: scheduleReportReturn absent or empty.
            OracleParseError: Malformed XML in the response.
        """
        xml_body = build_schedule_report_envelope(**envelope_kwargs)
        logger.info("Executing scheduleReport SOAP POST to %s", self._endpoint_url)
        logger.debug("scheduleReport request body size: %d bytes", len(xml_body))

        try:
            response = self._session.post(
                self._endpoint_url,
                data=xml_body,
                headers={"Content-Type": _CONTENT_TYPE},
                timeout=(self._connection_timeout, self._request_timeout),
            )
            logger.debug("scheduleReport HTTP status: %d", response.status_code)
        except requests.exceptions.ConnectionError as exc:
            # Distinguish pre-transmission vs. post-transmission failures.
            # requests wraps both cases as ConnectionError; we conservatively
            # treat any ConnectionError during submission as potentially
            # post-transmission because the TCP connection may have been
            # established before the reset occurred.
            error_str = str(exc)
            if any(
                indicator in error_str.lower()
                for indicator in ("connection refused", "name or service not known",
                                  "nodename nor servname", "no route to host",
                                  "network unreachable", "getaddrinfo failed",
                                  "eof occurred in violation")
            ):
                logger.error(
                    "Connection-level error before request transmission: %s", error_str
                )
                raise OracleConnectionError(
                    "Connection failed before request was sent to %s"
                    % self._endpoint_url
                ) from exc
            logger.error(
                "Connection error after request may have been transmitted: %s",
                error_str,
            )
            raise AmbiguousSubmissionError(
                "Connection reset during scheduleReport; Oracle may have received "
                "the request for job '%s'. Verify in Oracle Publisher before re-running."
                % job_name
            ) from exc
        except requests.exceptions.Timeout as exc:
            logger.error(
                "Timeout during scheduleReport; request body may have been transmitted"
            )
            raise AmbiguousSubmissionError(
                "Timeout during scheduleReport for job '%s'; Oracle may have received "
                "the request. Verify in Oracle Publisher before re-running." % job_name
            ) from exc

        # HTTP error classification
        if response.status_code == 401:
            logger.error("Oracle returned HTTP 401 (authentication failure)")
            raise OracleAuthenticationError(
                "Oracle rejected credentials for endpoint %s" % self._endpoint_url
            )
        if response.status_code == 403:
            logger.error("Oracle returned HTTP 403 (authorization failure)")
            raise OracleAuthorizationError(
                "Oracle denied access to endpoint %s" % self._endpoint_url
            )
        if response.status_code == 404:
            logger.error("Oracle returned HTTP 404 (endpoint not found)")
            raise OracleEndpointNotFoundError(
                "ScheduleService endpoint not found at %s" % self._endpoint_url
            )

        # Parse the SOAP response
        root = parse_soap_response(response.content)

        fault = detect_fault(root)
        if fault is not None:
            logger.error(
                "SOAP Fault in scheduleReport response: faultcode=%s, faultstring=%s",
                fault.faultcode,
                fault.faultstring,
            )
            raise OracleSoapFaultError(
                "faultcode=%s, faultstring=%s, detail=%s"
                % (fault.faultcode, fault.faultstring, fault.detail)
            )

        job_id = parse_schedule_report_return(root)
        if not job_id:
            logger.error("scheduleReportReturn absent or empty in Oracle response")
            raise MissingJobIdError(
                "Oracle scheduleReport response contained no Job ID"
            )

        logger.info("scheduleReport returned Job ID: %s", job_id)
        return job_id

    def poll_report_status(
        self,
        job_id: str,
        user_id: str,
        password: str,
    ) -> ScheduledReportStatus:
        """Execute a getScheduledReportStatus SOAP call with transient retry.

        Retries up to ``UE_POLL_RETRY_COUNT`` times on transient HTTP errors
        (408, 429, 5xx) or read timeouts with a fixed 2-second backoff between
        attempts. SOAP Faults and XML parse errors are raised immediately
        without retry.

        Args:
            job_id: Oracle scheduled Job ID to poll.
            user_id: Oracle username for the SOAP body.
            password: Oracle password for the SOAP body.

        Returns:
            A :class:`~utility.soap_parser.ScheduledReportStatus` instance.

        Raises:
            OracleSoapFaultStatusError: SOAP Fault present in a poll response.
            OracleTransientError: All transient retries exhausted.
            OracleParseError: Malformed XML in the poll response.
        """
        xml_body = build_get_scheduled_report_status_envelope(
            job_id=job_id, user_id=user_id, password=password
        )
        logger.debug(
            "Executing getScheduledReportStatus SOAP POST: job_id=%s", job_id
        )

        last_exc: Optional[Exception] = None

        for attempt in range(self._poll_retry_count + 1):
            if attempt > 0:
                logger.warning(
                    "Poll retry %d of %d for job_id=%s",
                    attempt,
                    self._poll_retry_count,
                    job_id,
                )
                time.sleep(_POLL_RETRY_BACKOFF_SECONDS)

            try:
                response = self._session.post(
                    self._endpoint_url,
                    data=xml_body,
                    headers={"Content-Type": _CONTENT_TYPE},
                    timeout=(self._connection_timeout, self._request_timeout),
                )
                logger.debug(
                    "getScheduledReportStatus HTTP status: %d", response.status_code
                )
            except requests.exceptions.Timeout as exc:
                logger.warning(
                    "Read timeout polling job_id=%s (attempt %d)", job_id, attempt + 1
                )
                last_exc = exc
                continue
            except requests.exceptions.RequestException as exc:
                # Non-transient transport error — raise immediately
                logger.error(
                    "Non-transient transport error polling job_id=%s: %s",
                    job_id,
                    str(exc),
                )
                raise OracleTransientError(
                    "Transport error while polling job %s: %s" % (job_id, str(exc))
                ) from exc

            # Transient HTTP status codes — retry
            if response.status_code in _TRANSIENT_HTTP_CODES:
                logger.warning(
                    "Transient HTTP %d polling job_id=%s (attempt %d)",
                    response.status_code,
                    job_id,
                    attempt + 1,
                )
                last_exc = requests.exceptions.HTTPError(
                    "HTTP %d" % response.status_code
                )
                continue

            # Parse the SOAP response
            root = parse_soap_response(response.content)

            fault = detect_fault(root)
            if fault is not None:
                logger.error(
                    "SOAP Fault in getScheduledReportStatus response: "
                    "job_id=%s, faultcode=%s, faultstring=%s",
                    job_id,
                    fault.faultcode,
                    fault.faultstring,
                )
                raise OracleSoapFaultStatusError(
                    "job_id=%s, faultcode=%s, faultstring=%s"
                    % (job_id, fault.faultcode, fault.faultstring)
                )

            return parse_scheduled_report_status_return(root)

        logger.error(
            "All %d poll retries exhausted for job_id=%s", self._poll_retry_count, job_id
        )
        raise OracleTransientError(
            "All %d poll retries exhausted for job %s: %s"
            % (self._poll_retry_count, job_id, str(last_exc))
        )
