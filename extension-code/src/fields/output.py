"""OutputFields dataclass for real-time UI updates."""

from dataclasses import dataclass, asdict
from typing import Optional
from universal_extension import ui
from fields.types import Text


@dataclass
class OutputFields:
    """Real-time output fields for UAC UI updates.

    These fields sync with the UAC UI in real-time during execution and are
    available in subsequent re-runs via InputFields.previous_output.

    Fields:
        scheduled_job_id: Oracle scheduled Job ID returned by scheduleReport.
            Preserved across re-runs (preserveOutputOnRerun: true). A non-empty
            value triggers re-run behavior — polling resumes without resubmitting.
        final_status: Raw jobStatus string returned by Oracle at the terminal state.
        status_message: Oracle JobStatus.message value at the terminal state.
        elapsed_seconds: Seconds from Job ID capture to terminal status or failure,
            formatted as a plain integer string.
        report_path: Submitted Oracle Publisher catalog path, echoed from
            report_absolute_path input.
    """

    scheduled_job_id: Optional[Text] = None
    final_status: Optional[Text] = None
    status_message: Optional[Text] = None
    elapsed_seconds: Optional[Text] = None
    report_path: Optional[Text] = None

    def update(self, **fields):
        """Update fields and sync with UAC UI in real-time.

        Args:
            **fields: Field names and string values to update.
                      String values are automatically wrapped in Text.
        """
        for field_name, field_value in fields.items():
            if hasattr(self, field_name):
                if isinstance(field_value, str):
                    field_value = Text(field_value)
                setattr(self, field_name, field_value)
        ui.update_output_fields(fields)

    def to_dict(self) -> dict:
        """Get current fields as dictionary.

        Returns:
            Dict with non-None field values (Text wrappers unwrapped to strings).
        """
        result = {}
        for k, v in asdict(self).items():
            if v is not None:
                result[k] = v.value if isinstance(v, Text) else v
        return result

    def clear(self):
        """Reset all fields to None."""
        self.scheduled_job_id = None
        self.final_status = None
        self.status_message = None
        self.elapsed_seconds = None
        self.report_path = None
