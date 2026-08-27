"""
Output Formatter for Oracle Analytics Publisher Asynchronous Report Scheduler.

Handles all STDOUT output: progressive execution log lines emitted during
the action flow and the final summary table printed on completion.
"""
import logging
from typing import Optional

from tabulate import tabulate

logger = logging.getLogger("UNV")


def print_target(schedule_service_url: str) -> None:
    """Print the target ScheduleService URL to STDOUT.

    Args:
        schedule_service_url: Full endpoint URL for the Oracle ScheduleService.
    """
    print("Target: %s" % schedule_service_url)
    logger.debug("Printed target URL: %s", schedule_service_url)


def print_submitting_report(report_absolute_path: str) -> None:
    """Print the report submission line to STDOUT.

    Args:
        report_absolute_path: Oracle Publisher catalog path for the report.
    """
    print("Submitting Oracle Publisher report %s" % report_absolute_path)
    logger.debug("Printed report submission line: %s", report_absolute_path)


def print_job_preparation(job_name: str, parameter_count: int) -> None:
    """Print the job preparation summary line to STDOUT.

    Args:
        job_name: The resolved or generated Oracle job name.
        parameter_count: Number of non-null report parameters.
    """
    print("Job name: %s | Parameters: %d" % (job_name, parameter_count))
    logger.debug(
        "Printed job preparation line: job_name=%s, param_count=%d",
        job_name,
        parameter_count,
    )


def print_job_id_confirmed(job_id: str) -> None:
    """Print the Job ID confirmation line to STDOUT after successful submission.

    Args:
        job_id: Oracle scheduled Job ID returned by scheduleReport.
    """
    print("Oracle Publisher scheduled Job ID: %s" % job_id)
    logger.debug("Printed job ID confirmation: %s", job_id)


def print_status_transition(
    job_id: str,
    previous_status: Optional[str],
    current_raw_status: str,
) -> None:
    """Print a status transition line to STDOUT when the status changes.

    This function must only be called when the current normalized status
    differs from the previous normalized status. The caller is responsible
    for change detection.

    Args:
        job_id: Oracle scheduled Job ID being polled.
        previous_status: Previous normalized status string, or None on the
            first transition.
        current_raw_status: Raw status string from the current poll response.
    """
    print(
        "Job %s status changed: %s -> %s"
        % (job_id, previous_status, current_raw_status)
    )
    logger.debug(
        "Status transition printed: job_id=%s, %s -> %s",
        job_id,
        previous_status,
        current_raw_status,
    )


def print_rerun_detected(job_id: str) -> None:
    """Print the re-run detection message to STDOUT.

    Args:
        job_id: The preserved Oracle Job ID from a previous task execution.
    """
    print("Re-run detected: polling existing Publisher job %s" % job_id)
    logger.debug("Printed re-run detection message: job_id=%s", job_id)


def print_completion(job_id: str, elapsed_seconds: int) -> None:
    """Print the task completion summary line to STDOUT.

    Args:
        job_id: Oracle scheduled Job ID.
        elapsed_seconds: Elapsed seconds from Job ID capture to terminal state.
    """
    print(
        "Oracle Publisher job %s completed successfully in %ds"
        % (job_id, elapsed_seconds)
    )
    logger.debug(
        "Printed completion line: job_id=%s, elapsed=%ds", job_id, elapsed_seconds
    )


def print_summary_table(
    scheduled_job_id: str,
    report_path: str,
    final_status: str,
    status_message: str,
    elapsed_seconds: int,
) -> None:
    """Print the final summary table to STDOUT using tabulate rounded_outline style.

    Rows are printed in this fixed order: Scheduled Job ID, Report Path,
    Final Status, Status Message, Elapsed Seconds.

    Args:
        scheduled_job_id: Oracle scheduled Job ID.
        report_path: Oracle Publisher catalog path echoed from the input field.
        final_status: Raw Oracle ``jobStatus`` at terminal state.
        status_message: Oracle ``message`` field at terminal state.
        elapsed_seconds: Integer seconds from Job ID capture to terminal state.
    """
    rows = [
        ["Scheduled Job ID", scheduled_job_id],
        ["Report Path", report_path],
        ["Final Status", final_status],
        ["Status Message", status_message],
        ["Elapsed Seconds", str(elapsed_seconds)],
    ]
    table = tabulate(rows, tablefmt="rounded_outline")
    print(table)
    logger.debug("Printed summary table for job_id=%s", scheduled_job_id)
