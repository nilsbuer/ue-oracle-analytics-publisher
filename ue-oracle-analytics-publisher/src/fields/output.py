"""OutputFields dataclass for real-time UI updates."""

from dataclasses import dataclass, asdict
from typing import Optional
from universal_extension import ui
from fields.types import Text


@dataclass
class OutputFields:
    """Real-time output fields for UAC UI updates.

    Define fields for progress tracking during execution.
    These fields sync with the UAC UI in real-time and are available
    in subsequent re-runs via InputFields.previous_output.

    All output fields should use the Text wrapper type.
    """

    # Define your progress tracking fields here using Text wrapper
    # Example fields:
    # status: Optional[Text] = None
    # progress: Optional[Text] = None
    # current_item: Optional[Text] = None
    # items_processed: Optional[Text] = None
    # last_processed_id: Optional[Text] = None

    def update(self, **fields):
        """Update fields and sync with UAC UI in real-time.

        Args:
            **fields: Field names and values to update (strings will be wrapped in Text)
        """
        for field_name, field_value in fields.items():
            if hasattr(self, field_name):
                # Wrap string values in Text type
                if isinstance(field_value, str):
                    field_value = Text(field_value)
                setattr(self, field_name, field_value)
        ui.update_output_fields(fields)

    def to_dict(self) -> dict:
        """Get current fields as dictionary.

        Returns:
            Dict with non-None field values (Text wrappers unwrapped to strings)
        """
        result = {}
        for k, v in asdict(self).items():
            if v is not None:
                # Extract value from Text wrapper
                result[k] = v.value if isinstance(v, Text) else v
        return result

    def clear(self):
        """Reset all fields to None.

        Update this method to match your defined fields.
        """
        # Add your fields here
        # self.status = None
        # self.progress = None
        # self.current_item = None
        # self.items_processed = None
        # self.last_processed_id = None
        pass
