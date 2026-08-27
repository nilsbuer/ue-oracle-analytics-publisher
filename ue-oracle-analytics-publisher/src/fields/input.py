"""InputFields dataclass for input parsing and validation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, Dict, List, get_type_hints, Union, get_origin, get_args
from fields.output import OutputFields
from fields.types import (
    Text,
    Integer,
    Float,
    Boolean,
    SingleChoice,
    MultiChoice,
    Credential,
    Script,
    Array,
)
from exceptions import DataValidationError
from manager import ExtensionManager
from dataclasses import fields as dataclass_fields
from dataclasses import asdict

extension_manager = ExtensionManager()


@dataclass
class InputFields:
    """Input fields from UAC with validation.

    Define fields based on your template.json fields using wrapper types.
    All fields should use wrapper types from fields.types for type safety.

    All user-defined fields should be Optional[Type] = None
    - UAC Controller enforces required field validation (template.json)
    - By the time fields reach the extension, they may be None
    - Only validate fields that have values (check for None first)
    """

    # User-defined fields - ALWAYS Optional, even if required in template.json
    action: Optional[SingleChoice] = None

    # Define your extension's fields here using wrapper types
    # Example fields:
    # resource_name: Optional[Text] = None
    # timeout: Optional[Integer] = None
    # api_credential: Optional[Credential] = None
    # tags: Optional[MultiChoice] = None

    # Script fields - use Script wrapper (UAC returns temp file path)
    # sql_query: Optional[Script] = None
    # json_payload: Optional[Script] = None

    # Control fields - use MultiChoice for multi-select options
    # stdout_options: Optional[MultiChoice] = None
    # output_options: Optional[MultiChoice] = None

    # Previous run output (auto-populated for re-runs)
    previous_output: Optional[OutputFields] = None

    # Skip validation flag (internal use only)
    _skip_validation: bool = False

    @staticmethod
    def preprocess_fields(fields: dict) -> dict:
        """Preprocess raw UAC fields before creating InputFields.

        Converts raw UAC values to wrapper type instances:
        1. Filters out flattened credential fields (containing dots)
        2. Wraps values in appropriate wrapper types based on field type hints
        3. Extracts previous OutputFields if present (from re-runs)
        """

        processed = {}
        previous_output_data = {}

        # Get all OutputFields field names for detection
        output_field_names = {f.name for f in dataclass_fields(OutputFields)}

        # Get type hints to detect wrapper types
        type_hints = get_type_hints(InputFields)

        # Map field names to their wrapper types
        field_wrapper_types = {}
        for field_name, field_type in type_hints.items():
            # Get base type (unwrap Optional)
            base_type = field_type
            if get_origin(field_type) is Union:
                args = get_args(field_type)
                # Filter out NoneType to get the actual type
                non_none_args = [arg for arg in args if arg is not type(None)]
                if non_none_args:
                    base_type = non_none_args[0]

            field_wrapper_types[field_name] = base_type

        for key, value in fields.items():
            # Skip flattened credential fields (e.g., "api_credential.token")
            if "." in key:
                continue

            # Check if this field belongs to OutputFields (previous run data)
            if key in output_field_names:
                previous_output_data[key] = value
                continue

            # Skip None values
            if value is None:
                processed[key] = value
                continue

            # Get the wrapper type for this field
            wrapper_type = field_wrapper_types.get(key)

            # Convert to appropriate wrapper type
            if wrapper_type == SingleChoice:
                # UAC sends as list, SingleChoice expects list
                if isinstance(value, list):
                    value = SingleChoice(_values=value)
                else:
                    value = SingleChoice(_values=[value])

            elif wrapper_type == MultiChoice:
                # UAC sends as list, MultiChoice expects list
                if isinstance(value, list):
                    value = MultiChoice(values=value)
                else:
                    value = MultiChoice(values=[value])

            elif wrapper_type == Script:
                # UAC sends as string path, Script expects Path object
                if isinstance(value, str):
                    value = Script(path=Path(value))

            elif wrapper_type == Credential:
                # UAC sends as dict, Credential expects kwargs
                if isinstance(value, dict):
                    value = Credential.from_dict(value)

            elif wrapper_type == Text:
                # Wrap string in Text
                if isinstance(value, str):
                    value = Text(value=value)

            elif wrapper_type == Integer:
                # Wrap int in Integer
                if isinstance(value, int):
                    value = Integer(value=value)

            elif wrapper_type == Float:
                # Wrap float in Float
                if isinstance(value, (int, float)):
                    value = Float(value=float(value))

            elif wrapper_type == Boolean:
                # Wrap bool in Boolean
                if isinstance(value, bool):
                    value = Boolean(value=value)

            elif wrapper_type == Array:
                # UAC sends as list of dicts, Array expects list of dicts
                if isinstance(value, list):
                    value = Array(pairs=value)

            processed[key] = value

        # If we found previous output fields, create OutputFields instance
        if previous_output_data:
            # Wrap Text fields in previous output
            for key, val in previous_output_data.items():
                if isinstance(val, str):
                    previous_output_data[key] = Text(value=val)
            processed["previous_output"] = OutputFields(**previous_output_data)

        return processed

    def to_dict(self) -> dict:
        """Convert to dict, unwrapping wrapper types and excluding internal fields.

        Returns:
            Dict with unwrapped field values, excluding _skip_validation and None previous_output
        """

        data = asdict(self)

        # Unwrap wrapper types to their raw values
        result = {}
        for key, value in data.items():
            # Skip internal fields
            if key == "_skip_validation":
                continue

            # Skip None previous_output
            if key == "previous_output" and value is None:
                continue

            # Unwrap wrapper types
            if isinstance(value, dict):
                # Check if it's a wrapper type dict representation
                if "_values" in value:  # SingleChoice
                    result[key] = value["_values"]
                elif "values" in value and len(value) == 1:  # MultiChoice
                    result[key] = value["values"]
                elif "value" in value and len(value) == 1:  # Text, Integer, Float, Boolean
                    result[key] = value["value"]
                elif "path" in value:  # Script
                    result[key] = str(value["path"])
                elif "pairs" in value:  # Array
                    result[key] = value["pairs"]
                elif "user" in value:  # Credential
                    result[key] = value
                else:
                    result[key] = value
            else:
                result[key] = value

        return result

    def __post_init__(self):
        """Validate fields after initialization."""
        if self._skip_validation:
            return

        # Call validation methods
        self._validate_action()
        # Add your validation methods here
        # self._validate_resource_name()
        # self._validate_timeout()

        # Raise once if errors collected
        if extension_manager.has_errors():
            raise DataValidationError(
                f"Validation failed with {extension_manager.error_count()} error(s)"
            )

    def _validate_action(self):
        """Validate action field (SingleChoice wrapper).

        Only validate fields with values - check for None first.
        """
        # ALWAYS check for None first - only validate if field has a value
        if self.action is not None:
            valid_actions = ["create", "delete", "update", "list"]  # Define your actions
            # Access SingleChoice value via .value property
            if self.action.value not in valid_actions:
                exc = DataValidationError(
                    f"Invalid action '{self.action.value}'. Valid actions: {', '.join(valid_actions)}"
                )
                extension_manager.add_error(exc, field="action", value=self.action.value)

    # Add your validation methods here
    # Always check for None first - only validate fields with values
    #
    # def _validate_resource_name(self):
    #     """Validate resource_name field (Text wrapper)."""
    #     # Always check for None first
    #     if self.resource_name is not None:
    #         # Access Text value via .value property
    #         if len(self.resource_name.value) == 0 or len(self.resource_name.value) > 255:
    #             exc = DataValidationError("resource_name must be 1-255 characters")
    #             extension_manager.add_error(
    #                 exc, field="resource_name", value=self.resource_name.value
    #             )
    #
    # def _validate_timeout(self):
    #     """Validate timeout field (Integer wrapper)."""
    #     # Always check for None first - only validate if field has a value
    #     if self.timeout is not None:
    #         # Access Integer value via .value property
    #         if self.timeout.value < 1:
    #             exc = DataValidationError("timeout must be >= 1")
    #             extension_manager.add_error(exc, field="timeout", value=self.timeout.value)
    #
    # def _validate_sql_query(self):
    #     """Validate sql_query script field (Script wrapper)."""
    #     # Always check for None first - only validate if field has a value
    #     if self.sql_query is not None:
    #         # Validate file exists using Script wrapper method
    #         if not self.sql_query.exists():
    #             exc = DataValidationError("SQL query file not found")
    #             extension_manager.add_error(exc, field="sql_query")
    #             return
    #
    #         # Read content using Script wrapper method
    #         try:
    #             content = self.sql_query.read()
    #             if not content.strip():
    #                 exc = DataValidationError("SQL query cannot be empty")
    #                 extension_manager.add_error(exc, field="sql_query")
    #         except Exception as e:
    #             exc = DataValidationError(f"Failed to read SQL query: {str(e)}")
    #             extension_manager.add_error(exc, field="sql_query")
    #
    # def _validate_headers(self):
    #     """Validate headers array field (Array wrapper).
    #
    #     IMPORTANT: UAC sends arrays in FLATTENED format!
    #     Task definition has: {"name": "X", "value": "Y"}
    #     UAC transforms to: {"X": "Y"}
    #
    #     See Array class documentation in fields/types.py for details.
    #     """
    #     # Always check for None first - only validate if field has a value
    #     if self.headers is not None:
    #         # Access Array pairs (list of flattened dicts)
    #         header_list = self.headers.pairs
    #
    #         for idx, header in enumerate(header_list):
    #             # Check if dictionary is empty
    #             if not header:
    #                 exc = DataValidationError(f"Header at index {idx} is empty")
    #                 extension_manager.add_error(exc, field="headers", index=idx)
    #                 continue
    #
    #             # Extract key from flattened format: {"X": "Y"}
    #             # Do NOT check for "name" property - it doesn't exist!
    #             header_name = next(iter(header.keys()), "")
    #             if not header_name:
    #                 exc = DataValidationError(
    #                     f"Header at index {idx} must have a non-empty name"
    #                 )
    #                 extension_manager.add_error(exc, field="headers", index=idx)
    #                 continue
    #
    #             # Optional: validate header value
    #             header_value = header[header_name]
    #             if header_value is None:
    #                 exc = DataValidationError(
    #                     f"Header '{header_name}' at index {idx} has null value"
    #                 )
    #                 extension_manager.add_error(exc, field="headers", index=idx)
