"""ActionOutput dataclass for action return values."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from utility.output_formatter import print_summary_table

logger = logging.getLogger("UNV")


@dataclass
class ActionOutput:
    """Output from action functions.

    Fields correspond to the five Oracle Analytics Publisher output fields
    that are set on task completion. There are no stdout_options or
    output_options control fields in this extension's template — all fields
    are always included in STDOUT and Extension Output.

    Attrs:
        scheduled_job_id: Oracle scheduled Job ID returned by scheduleReport.
        final_status: Raw Oracle jobStatus string at the terminal state.
        status_message: Oracle JobStatus.message at the terminal state.
        elapsed_seconds: Integer seconds from Job ID capture to terminal state.
        report_path: Submitted Oracle Publisher catalog path echoed from input.
    """

    scheduled_job_id: Optional[str] = None
    final_status: Optional[str] = None
    status_message: Optional[str] = None
    elapsed_seconds: Optional[int] = None
    report_path: Optional[str] = None

    # No stdout_options / output_options in this extension's template.
    # These placeholders are kept so callers may pass empty lists without error.
    stdout_options: List[str] = None
    output_options: List[str] = None

    def __post_init__(self) -> None:
        """Initialize control fields with defaults."""
        if self.stdout_options is None:
            self.stdout_options = []
        if self.output_options is None:
            self.output_options = []

    def print_output(self) -> None:
        """Print the summary table to STDOUT using the output_formatter utility.

        This extension has no stdout_options control — the summary table is
        always printed when the required fields are available.
        """
        if self.scheduled_job_id is None:
            logger.debug("print_output: scheduled_job_id is None, skipping summary table")
            return

        logger.debug(
            "print_output: printing summary table for job_id=%s", self.scheduled_job_id
        )
        print_summary_table(
            scheduled_job_id=self.scheduled_job_id,
            report_path=self.report_path or "",
            final_status=self.final_status or "",
            status_message=self.status_message or "",
            elapsed_seconds=self.elapsed_seconds if self.elapsed_seconds is not None else 0,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for Extension Output (unv_output).

        This extension has no output_options control — all non-None fields are
        always included in the returned dictionary.

        Returns:
            Dict containing all populated output field values.
        """
        output: Dict[str, Any] = {}

        if self.scheduled_job_id is not None:
            output["scheduled_job_id"] = self.scheduled_job_id

        if self.final_status is not None:
            output["final_status"] = self.final_status

        if self.status_message is not None:
            output["status_message"] = self.status_message

        if self.elapsed_seconds is not None:
            output["elapsed_seconds"] = self.elapsed_seconds

        if self.report_path is not None:
            output["report_path"] = self.report_path

        logger.debug("ActionOutput.to_dict: %s", output)
        return output
