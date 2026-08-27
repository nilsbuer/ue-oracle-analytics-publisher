"""ActionOutput dataclass for action return values."""

from dataclasses import dataclass
from typing import Optional, Any, Dict, List


@dataclass
class ActionOutput:
    """Output from action functions.

    Define fields based on your extension's output needs.
    Control fields (stdout_options, output_options) are populated from InputFields.
    """

    # Define your output fields here
    # Example fields:
    # resource_id: Optional[str] = None
    # resource_name: Optional[str] = None
    # details: Optional[Dict[str, Any]] = None
    # items: Optional[List[Dict[str, Any]]] = None
    # metadata: Optional[Dict[str, Any]] = None

    # Control fields (from template Choice fields)
    stdout_options: List[str] = None
    output_options: List[str] = None

    def __post_init__(self):
        """Initialize control fields with defaults."""
        if self.stdout_options is None:
            self.stdout_options = []
        if self.output_options is None:
            self.output_options = []

    def print_output(self):
        """Print to STDOUT based on stdout_options.

        Implement printing logic based on user selections.
        Empty list = print everything (if no control fields in template)
        """
        # Implement based on your fields
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for Extension Output (unv_output).

        Returns dict based on output_options selections.
        Empty list = include everything (if no control fields in template)
        """
        include_all = len(self.output_options) == 0
        output = {}

        # Implement based on your fields

        return output
