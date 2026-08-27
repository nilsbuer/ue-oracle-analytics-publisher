"""Schedule and Monitor Report action for Oracle Analytics Publisher."""

import json
import logging
import time
from datetime import datetime, timezone

from actions.output import ActionOutput
from exceptions import (
    DataValidationError,
    InconsistentJobIdError,
    PublisherJobFailedError,
    PollTimeoutError,
    UnknownStatusThresholdError,
)
from fields.input import InputFields
from fields.output import OutputFields
from manager import ExtensionManager
from utility.http_client import OracleHttpClient
from utility.output_formatter import (
    print_completion,
    print_job_id_confirmed,
    print_job_preparation,
    print_rerun_detected,
    print_status_transition,
    print_submitting_report,
    print_target,
)
from utility.status_classifier import StatusCategory, classify_status

logger = logging.getLogger("UNV")
extension_manager = ExtensionManager()


def schedule_and_monitor_report(input_data: InputFields) -> ActionOutput:
    """Authenticate, submit a report job, and poll until a terminal state.

    On re-run, if a preserved Job ID is available in the scheduled_job_id
    output field, the submission step is skipped and polling resumes directly.

    Args:
        input_data: Validated input fields from UAC.

    Returns:
        ActionOutput with scheduled_job_id, final_status, status_message,
        elapsed_seconds, and report_path populated on success.

    Raises:
        DataValidationError: When input validation fails (exit code 20).
        OracleAuthenticationError: HTTP 401 from Oracle.
        OracleAuthorizationError: HTTP 403 from Oracle.
        OracleEndpointNotFoundError: HTTP 404 from Oracle.
        OracleConnectionError: Connection-level failure before transmission.
        AmbiguousSubmissionError: Timeout/reset after request may have transmitted.
        OracleSoapFaultError: SOAP Fault in scheduleReport response.
        MissingJobIdError: scheduleReportReturn absent or empty.
        OracleParseError: Malformed XML in any SOAP response.
        OracleSoapFaultStatusError: SOAP Fault during polling.
        OracleTransientError: All poll retries exhausted.
        PublisherJobFailedError: Oracle returned a failure terminal status.
        PollTimeoutError: maximum_wait_seconds exceeded without terminal status.
        UnknownStatusThresholdError: Consecutive unknown statuses exceeded threshold.
        InconsistentJobIdError: jobID in poll response differs from submitted ID.
    """
    logger.info("Starting schedule_and_monitor_report action")

    # -----------------------------------------------------------------------
    # Step 1: Re-run Detection
    # -----------------------------------------------------------------------
    job_id: str = ""

    if input_data.scheduled_job_id is not None and input_data.scheduled_job_id.value:
        job_id = input_data.scheduled_job_id.value
        logger.info("Re-run detected: polling existing Publisher job %s", job_id)
        print_rerun_detected(job_id)
    else:
        logger.debug("No preserved job ID found; proceeding with full submission flow")

    # -----------------------------------------------------------------------
    # Step 2: Input Validation (always runs — including on re-run)
    # -----------------------------------------------------------------------
    logger.info("Validating input fields")

    # URL scheme validation
    url = input_data.schedule_service_url.value if input_data.schedule_service_url else ""
    if not url:
        exc = DataValidationError("schedule_service_url must not be empty")
        extension_manager.add_error(exc, field="schedule_service_url")
    elif not (url.startswith("http://") or url.startswith("https://")):
        exc = DataValidationError(
            "schedule_service_url must begin with 'http://' or 'https://'. Got: %r" % url
        )
        extension_manager.add_error(exc, field="schedule_service_url", value=url)

    # Credential validation
    if input_data.oracle_credential is None:
        exc = DataValidationError("oracle_credential must not be empty")
        extension_manager.add_error(exc, field="oracle_credential")
    else:
        if not input_data.oracle_credential.user:
            exc = DataValidationError(
                "oracle_credential: user (Oracle username) must not be empty"
            )
            extension_manager.add_error(exc, field="oracle_credential")
        if not input_data.oracle_credential.password:
            exc = DataValidationError(
                "oracle_credential: password must not be empty"
            )
            extension_manager.add_error(exc, field="oracle_credential")

    # Report path validation
    report_path_val = (
        input_data.report_absolute_path.value
        if input_data.report_absolute_path
        else ""
    )
    if not report_path_val:
        exc = DataValidationError("report_absolute_path must not be empty")
        extension_manager.add_error(exc, field="report_absolute_path")
    elif not report_path_val.endswith(".xdo"):
        exc = DataValidationError(
            "report_absolute_path must end with '.xdo'. Got: %r" % report_path_val
        )
        extension_manager.add_error(
            exc, field="report_absolute_path", value=report_path_val
        )

    # Report parameters validation
    raw_params = (
        input_data.report_parameters.value if input_data.report_parameters else ""
    )
    parameters: dict = {}
    if raw_params and raw_params.strip():
        try:
            parsed_params = json.loads(raw_params.strip())
        except json.JSONDecodeError as jde:
            exc = DataValidationError(
                "report_parameters is not valid JSON: %s" % jde
            )
            extension_manager.add_error(exc, field="report_parameters")
            parsed_params = None
        else:
            if not isinstance(parsed_params, dict):
                exc = DataValidationError(
                    "report_parameters must be a JSON object ({}), "
                    "not an array, scalar, or null"
                )
                extension_manager.add_error(exc, field="report_parameters")
                parsed_params = None
            else:
                for param_name, param_value in parsed_params.items():
                    if isinstance(param_value, list) and len(param_value) == 0:
                        exc = DataValidationError(
                            "report_parameters: parameter '%s' must not be an empty array []"
                            % param_name
                        )
                        extension_manager.add_error(
                            exc, field="report_parameters", parameter=param_name
                        )
                parameters = parsed_params
    # else: empty string or None — use empty dict (zero parameters)

    # Polling / timeout validation
    poll_interval = (
        input_data.poll_interval_seconds.value
        if input_data.poll_interval_seconds
        else 10
    )
    max_wait = (
        input_data.maximum_wait_seconds.value
        if input_data.maximum_wait_seconds
        else 3600
    )
    unknown_retry = (
        input_data.unknown_status_retry_count.value
        if input_data.unknown_status_retry_count
        else 3
    )
    conn_timeout = (
        input_data.connection_timeout_seconds.value
        if input_data.connection_timeout_seconds
        else 30
    )
    req_timeout = (
        input_data.request_timeout_seconds.value
        if input_data.request_timeout_seconds
        else 60
    )

    if poll_interval < 1:
        exc = DataValidationError(
            "poll_interval_seconds must be >= 1. Got: %d" % poll_interval
        )
        extension_manager.add_error(
            exc, field="poll_interval_seconds", value=poll_interval
        )

    if max_wait < poll_interval:
        exc = DataValidationError(
            "maximum_wait_seconds (%d) must be >= poll_interval_seconds (%d)"
            % (max_wait, poll_interval)
        )
        extension_manager.add_error(
            exc, field="maximum_wait_seconds", value=max_wait
        )

    if conn_timeout < 1:
        exc = DataValidationError(
            "connection_timeout_seconds must be >= 1. Got: %d" % conn_timeout
        )
        extension_manager.add_error(
            exc, field="connection_timeout_seconds", value=conn_timeout
        )

    if req_timeout < 1:
        exc = DataValidationError(
            "request_timeout_seconds must be >= 1. Got: %d" % req_timeout
        )
        extension_manager.add_error(
            exc, field="request_timeout_seconds", value=req_timeout
        )

    if unknown_retry < 0:
        exc = DataValidationError(
            "unknown_status_retry_count must be >= 0. Got: %d" % unknown_retry
        )
        extension_manager.add_error(
            exc, field="unknown_status_retry_count", value=unknown_retry
        )

    if extension_manager.has_errors():
        raise DataValidationError(
            "Validation failed with %d error(s)" % extension_manager.error_count()
        )

    logger.info("Input validation passed")

    # -----------------------------------------------------------------------
    # Initialize OutputFields for real-time UI updates
    # -----------------------------------------------------------------------
    output_fields = OutputFields()

    # Extract typed field values (validated, safe to access .value)
    username: str = input_data.oracle_credential.user
    password: str = input_data.oracle_credential.password
    verify_tls: bool = (
        input_data.verify_tls.value if input_data.verify_tls is not None else True
    )
    bypass_cache: bool = (
        input_data.bypass_cache.value if input_data.bypass_cache is not None else False
    )
    save_data: bool = (
        input_data.save_data.value if input_data.save_data is not None else False
    )
    save_output: bool = (
        input_data.save_output.value if input_data.save_output is not None else False
    )
    bursting: bool = (
        input_data.bursting.value if input_data.bursting is not None else False
    )
    public_schedule: bool = (
        input_data.public_schedule.value
        if input_data.public_schedule is not None
        else False
    )
    output_format: str = (
        input_data.output_format.value
        if input_data.output_format is not None and input_data.output_format.value
        else ""
    )
    report_template: str = (
        input_data.report_template.value
        if input_data.report_template is not None and input_data.report_template.value
        else ""
    )
    report_locale: str = (
        input_data.report_locale.value
        if input_data.report_locale is not None and input_data.report_locale.value
        else ""
    )
    ui_locale: str = (
        input_data.ui_locale.value
        if input_data.ui_locale is not None and input_data.ui_locale.value
        else ""
    )
    report_timezone: str = (
        input_data.report_timezone.value
        if input_data.report_timezone is not None and input_data.report_timezone.value
        else ""
    )
    job_locale: str = (
        input_data.job_locale.value
        if input_data.job_locale is not None and input_data.job_locale.value
        else ""
    )
    job_timezone: str = (
        input_data.job_timezone.value
        if input_data.job_timezone is not None and input_data.job_timezone.value
        else ""
    )

    # -----------------------------------------------------------------------
    # Step 3: Pre-submission Preparation (only on fresh submission)
    # -----------------------------------------------------------------------
    elapsed_start: float = 0.0

    with OracleHttpClient(
        endpoint_url=url,
        username=username,
        password=password,
        verify_tls=verify_tls,
        connection_timeout=conn_timeout,
        request_timeout=req_timeout,
    ) as client:

        if not job_id:
            # Fresh submission path
            print_target(url)
            print_submitting_report(report_path_val)

            # Resolve job_name
            raw_job_name = (
                input_data.job_name.value
                if input_data.job_name is not None and input_data.job_name.value
                else ""
            )
            if raw_job_name:
                job_name = raw_job_name
            else:
                report_basename = report_path_val.rsplit("/", 1)[-1]
                if report_basename.endswith(".xdo"):
                    report_basename = report_basename[:-4]
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                job_name = "UAC-%s-%s" % (report_basename, timestamp)

            # Resolve job_description
            raw_job_desc = (
                input_data.job_description.value
                if input_data.job_description is not None
                and input_data.job_description.value
                else ""
            )
            job_description = raw_job_desc if raw_job_desc else "Submitted by Stonebranch UAC"

            non_null_param_count = sum(
                1 for v in parameters.values() if v is not None
            )
            logger.info(
                "Job name: %s | Parameters: %d", job_name, non_null_param_count
            )
            print_job_preparation(job_name, non_null_param_count)

            # -------------------------------------------------------------------
            # Step 4: Submit Report via scheduleReport
            # -------------------------------------------------------------------
            logger.info("Submitting report via scheduleReport")
            job_id = client.submit_report(
                job_name=job_name,
                report_absolute_path=report_path_val,
                user_id=username,
                password=password,
                bypass_cache=bypass_cache,
                user_job_name=job_name,
                user_job_desc=job_description,
                save_data=save_data,
                save_output=save_output,
                bursting=bursting,
                public_schedule=public_schedule,
                parameters=parameters,
                output_format=output_format,
                report_template=report_template,
                report_locale=report_locale,
                ui_locale=ui_locale,
                report_timezone=report_timezone,
                job_locale=job_locale,
                job_timezone=job_timezone,
            )

            output_fields.update(scheduled_job_id=job_id)
            elapsed_start = time.monotonic()
            print_job_id_confirmed(job_id)
            logger.info("Oracle Publisher scheduled Job ID: %s", job_id)

        else:
            # Re-run path — polling resumes, start elapsed timer now
            elapsed_start = time.monotonic()

        # -------------------------------------------------------------------
        # Step 5: Polling Loop
        # -------------------------------------------------------------------
        logger.info("Starting polling loop for job_id=%s", job_id)
        consecutive_unknown_count: int = 0
        last_known_status: str = None  # type: ignore[assignment]

        while True:
            # Check elapsed time
            elapsed_now = time.monotonic() - elapsed_start
            if elapsed_now >= max_wait:
                logger.error(
                    "Poll timeout: job_id=%s, elapsed=%.1fs, max_wait=%ds, "
                    "last_status=%s",
                    job_id,
                    elapsed_now,
                    max_wait,
                    last_known_status,
                )
                raise PollTimeoutError(
                    "Polling timed out after %ds for job %s (last status: %s)"
                    % (int(elapsed_now), job_id, last_known_status)
                )

            logger.debug(
                "Sleeping %ds before next poll (elapsed=%.1fs)",
                poll_interval,
                elapsed_now,
            )
            time.sleep(poll_interval)

            # Poll Oracle status
            status_result = client.poll_report_status(
                job_id=job_id,
                user_id=username,
                password=password,
            )

            # Validate job ID consistency
            if status_result.job_id != job_id:
                logger.error(
                    "Inconsistent job ID: expected=%s, returned=%s",
                    job_id,
                    status_result.job_id,
                )
                raise InconsistentJobIdError(
                    "Expected job ID %s but Oracle returned %s"
                    % (job_id, status_result.job_id)
                )

            raw_job_status = status_result.job_status
            category, normalized_status = classify_status(raw_job_status)

            # Log status transition only when status changes
            if normalized_status != last_known_status:
                print_status_transition(
                    job_id=job_id,
                    previous_status=last_known_status,
                    current_raw_status=raw_job_status,
                )

            # Classify
            if category == StatusCategory.SUCCESSFUL_TERMINAL:
                logger.info(
                    "Job %s reached successful terminal status: %s",
                    job_id,
                    raw_job_status,
                )
                last_known_status = normalized_status
                break

            elif category == StatusCategory.FAILURE_TERMINAL:
                logger.error(
                    "Job %s reached failure terminal status: %s, message: %s",
                    job_id,
                    raw_job_status,
                    status_result.message,
                )
                raise PublisherJobFailedError(
                    "Oracle job %s failed with status '%s': %s"
                    % (job_id, raw_job_status, status_result.message)
                )

            elif category == StatusCategory.IN_PROGRESS:
                consecutive_unknown_count = 0
                last_known_status = normalized_status
                logger.debug("Job %s in progress: %s", job_id, raw_job_status)

            else:
                # UNKNOWN
                consecutive_unknown_count += 1
                logger.warning(
                    "Unknown Oracle status '%s' for job %s "
                    "(consecutive_unknown_count=%d, threshold=%d)",
                    raw_job_status,
                    job_id,
                    consecutive_unknown_count,
                    unknown_retry,
                )
                if consecutive_unknown_count > unknown_retry:
                    raise UnknownStatusThresholdError(
                        "Consecutive unknown status count (%d) exceeded threshold (%d) "
                        "for job %s; last raw status: '%s'"
                        % (
                            consecutive_unknown_count,
                            unknown_retry,
                            job_id,
                            raw_job_status,
                        )
                    )
                # Unknown but within threshold — treat as in-progress for timing
                last_known_status = normalized_status

    # -----------------------------------------------------------------------
    # Step 6: Completion
    # -----------------------------------------------------------------------
    elapsed_seconds = int(time.monotonic() - elapsed_start)
    final_status = status_result.job_status  # raw value from terminal response  # noqa: F821
    status_message = status_result.message  # noqa: F821

    output_fields.update(
        final_status=final_status,
        status_message=status_message,
        elapsed_seconds=str(elapsed_seconds),
        report_path=report_path_val,
    )

    logger.info(
        "Oracle Publisher job %s completed successfully in %ds",
        job_id,
        elapsed_seconds,
    )
    print_completion(job_id, elapsed_seconds)

    action_output = ActionOutput(
        scheduled_job_id=job_id,
        final_status=final_status,
        status_message=status_message,
        elapsed_seconds=elapsed_seconds,
        report_path=report_path_val,
    )
    action_output.print_output()

    logger.debug(
        "schedule_and_monitor_report completed: job_id=%s, elapsed=%ds",
        job_id,
        elapsed_seconds,
    )
    return action_output
