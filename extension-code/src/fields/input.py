"""InputFields dataclass for input parsing and validation."""

import json
from dataclasses import dataclass, fields as dataclass_fields, asdict
from pathlib import Path
from typing import Optional, Union, get_type_hints, get_origin, get_args
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

extension_manager = ExtensionManager()


@dataclass
class InputFields:
    """Input fields from UAC with validation.

    All user-defined fields are Optional — UAC Controller enforces required
    field validation at the template level. Only validate fields that carry
    a value (check for None and empty string before any validation logic).
    """

    # --- Core action and credential ---
    action: Optional[SingleChoice] = None
    oracle_credential: Optional[Credential] = None

    # --- Connection ---
    schedule_service_url: Optional[Text] = None
    verify_tls: Optional[Boolean] = None
    connection_timeout_seconds: Optional[Integer] = None
    request_timeout_seconds: Optional[Integer] = None

    # --- Report identification ---
    report_absolute_path: Optional[Text] = None
    report_parameters: Optional[Text] = None

    # --- Report rendering options ---
    output_format: Optional[SingleChoice] = None
    report_template: Optional[Text] = None
    report_locale: Optional[Text] = None
    ui_locale: Optional[Text] = None
    report_timezone: Optional[Text] = None
    bypass_cache: Optional[Boolean] = None

    # --- Job metadata ---
    job_name: Optional[Text] = None
    job_description: Optional[Text] = None

    # --- Job options ---
    save_data: Optional[Boolean] = None
    save_output: Optional[Boolean] = None
    bursting: Optional[Boolean] = None
    public_schedule: Optional[Boolean] = None

    # --- Job locale / timezone ---
    job_locale: Optional[Text] = None
    job_timezone: Optional[Text] = None

    # --- Polling configuration ---
    poll_interval_seconds: Optional[Integer] = None
    maximum_wait_seconds: Optional[Integer] = None
    unknown_status_retry_count: Optional[Integer] = None

    # --- Output / re-run trigger field (Output Only, preserveOutputOnRerun) ---
    scheduled_job_id: Optional[Text] = None

    # --- Framework fields ---
    previous_output: Optional[OutputFields] = None
    _skip_validation: bool = False

    @staticmethod
    def preprocess_fields(fields: dict) -> dict:
        """Preprocess raw UAC fields before creating InputFields.

        1. Filters out flattened credential sub-fields (containing dots).
        2. Wraps raw values in appropriate wrapper types based on field type hints.
        3. Extracts previous OutputFields if present (from re-runs).
        """
        processed: dict = {}
        previous_output_data: dict = {}

        output_field_names = {f.name for f in dataclass_fields(OutputFields)}
        type_hints = get_type_hints(InputFields)

        field_wrapper_types: dict = {}
        for field_name, field_type in type_hints.items():
            base_type = field_type
            if get_origin(field_type) is Union:
                args = get_args(field_type)
                non_none_args = [arg for arg in args if arg is not type(None)]
                if non_none_args:
                    base_type = non_none_args[0]
            field_wrapper_types[field_name] = base_type

        for key, value in fields.items():
            # Skip flattened credential sub-fields (e.g. oracle_credential.token)
            if "." in key:
                continue

            # Route output fields to previous_output bucket
            if key in output_field_names:
                previous_output_data[key] = value
                continue

            if value is None:
                processed[key] = value
                continue

            wrapper_type = field_wrapper_types.get(key)

            if wrapper_type == SingleChoice:
                if isinstance(value, list):
                    value = SingleChoice(_values=value)
                else:
                    value = SingleChoice(_values=[value])

            elif wrapper_type == MultiChoice:
                if isinstance(value, list):
                    value = MultiChoice(values=value)
                else:
                    value = MultiChoice(values=[value])

            elif wrapper_type == Script:
                if isinstance(value, str):
                    value = Script(path=Path(value))

            elif wrapper_type == Credential:
                if isinstance(value, dict):
                    value = Credential.from_dict(value)

            elif wrapper_type == Text:
                if isinstance(value, str):
                    value = Text(value=value)

            elif wrapper_type == Integer:
                if isinstance(value, int):
                    value = Integer(value=value)

            elif wrapper_type == Float:
                if isinstance(value, (int, float)):
                    value = Float(value=float(value))

            elif wrapper_type == Boolean:
                if isinstance(value, bool):
                    value = Boolean(value=value)

            elif wrapper_type == Array:
                if isinstance(value, list):
                    value = Array(pairs=value)

            processed[key] = value

        if previous_output_data:
            for key, val in previous_output_data.items():
                if isinstance(val, str):
                    previous_output_data[key] = Text(value=val)
            processed["previous_output"] = OutputFields(**previous_output_data)

        return processed

    def to_dict(self) -> dict:
        """Convert to dict, unwrapping wrapper types and excluding internal fields."""
        data = asdict(self)
        result: dict = {}
        for key, value in data.items():
            if key == "_skip_validation":
                continue
            if key == "previous_output" and value is None:
                continue
            if isinstance(value, dict):
                if "_values" in value:
                    result[key] = value["_values"]
                elif "values" in value and len(value) == 1:
                    result[key] = value["values"]
                elif "value" in value and len(value) == 1:
                    result[key] = value["value"]
                elif "path" in value:
                    result[key] = str(value["path"])
                elif "pairs" in value:
                    result[key] = value["pairs"]
                elif "user" in value:
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

        self._validate_action()
        self._validate_oracle_credential()
        self._validate_schedule_service_url()
        self._validate_report_absolute_path()
        self._validate_report_parameters()
        self._validate_connection_timeout_seconds()
        self._validate_request_timeout_seconds()
        self._validate_poll_interval_seconds()
        self._validate_maximum_wait_seconds()
        self._validate_unknown_status_retry_count()

        if extension_manager.has_errors():
            raise DataValidationError(
                f"Validation failed with {extension_manager.error_count()} error(s)"
            )

    # ------------------------------------------------------------------
    # Validation methods
    # ------------------------------------------------------------------

    def _validate_action(self):
        """Validate action is one of the defined choices."""
        if self.action is not None:
            valid_actions = ["Schedule and Monitor Report"]
            if self.action.value not in valid_actions:
                exc = DataValidationError(
                    f"Invalid action '{self.action.value}'. "
                    f"Valid actions: {', '.join(valid_actions)}"
                )
                extension_manager.add_error(exc, field="action", value=self.action.value)

    def _validate_oracle_credential(self):
        """Validate oracle_credential has non-empty user and password."""
        if self.oracle_credential is not None:
            if not self.oracle_credential.user:
                exc = DataValidationError(
                    "oracle_credential: user (Oracle username) must not be empty"
                )
                extension_manager.add_error(exc, field="oracle_credential")
            if not self.oracle_credential.password:
                exc = DataValidationError(
                    "oracle_credential: password must not be empty"
                )
                extension_manager.add_error(exc, field="oracle_credential")

    def _validate_schedule_service_url(self):
        """Validate schedule_service_url is non-empty and begins with http:// or https://."""
        if self.schedule_service_url is not None and self.schedule_service_url.value:
            url = self.schedule_service_url.value
            if not (url.startswith("http://") or url.startswith("https://")):
                exc = DataValidationError(
                    f"schedule_service_url must begin with 'http://' or 'https://'. "
                    f"Got: {url!r}"
                )
                extension_manager.add_error(
                    exc, field="schedule_service_url", value=url
                )

    def _validate_report_absolute_path(self):
        """Validate report_absolute_path is non-empty and ends with .xdo."""
        if self.report_absolute_path is not None and self.report_absolute_path.value:
            path = self.report_absolute_path.value
            if not path.endswith(".xdo"):
                exc = DataValidationError(
                    f"report_absolute_path must end with '.xdo'. Got: {path!r}"
                )
                extension_manager.add_error(
                    exc, field="report_absolute_path", value=path
                )

    def _validate_report_parameters(self):
        """Validate report_parameters is a valid JSON object when provided and non-empty.

        Rules:
        - Must be valid JSON when provided and non-empty.
        - Must be a JSON object (not array, scalar, or null at the top level).
        - No parameter value may be an empty array [].
        - JSON null values and empty string values are accepted.
        """
        if self.report_parameters is not None and self.report_parameters.value:
            raw = self.report_parameters.value.strip()
            if not raw:
                return

            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as jde:
                exc = DataValidationError(
                    f"report_parameters is not valid JSON: {jde}"
                )
                extension_manager.add_error(exc, field="report_parameters")
                return

            if not isinstance(parsed, dict):
                exc = DataValidationError(
                    "report_parameters must be a JSON object ({}), "
                    "not an array, scalar, or null"
                )
                extension_manager.add_error(exc, field="report_parameters")
                return

            for param_name, param_value in parsed.items():
                if isinstance(param_value, list) and len(param_value) == 0:
                    exc = DataValidationError(
                        f"report_parameters: parameter '{param_name}' "
                        f"must not be an empty array []"
                    )
                    extension_manager.add_error(
                        exc, field="report_parameters", parameter=param_name
                    )

    def _validate_connection_timeout_seconds(self):
        """Validate connection_timeout_seconds is a positive integer (minimum 1)."""
        if self.connection_timeout_seconds is not None:
            if self.connection_timeout_seconds.value < 1:
                exc = DataValidationError(
                    f"connection_timeout_seconds must be >= 1. "
                    f"Got: {self.connection_timeout_seconds.value}"
                )
                extension_manager.add_error(
                    exc,
                    field="connection_timeout_seconds",
                    value=self.connection_timeout_seconds.value,
                )

    def _validate_request_timeout_seconds(self):
        """Validate request_timeout_seconds is a positive integer (minimum 1)."""
        if self.request_timeout_seconds is not None:
            if self.request_timeout_seconds.value < 1:
                exc = DataValidationError(
                    f"request_timeout_seconds must be >= 1. "
                    f"Got: {self.request_timeout_seconds.value}"
                )
                extension_manager.add_error(
                    exc,
                    field="request_timeout_seconds",
                    value=self.request_timeout_seconds.value,
                )

    def _validate_poll_interval_seconds(self):
        """Validate poll_interval_seconds is at least 1."""
        if self.poll_interval_seconds is not None:
            if self.poll_interval_seconds.value < 1:
                exc = DataValidationError(
                    f"poll_interval_seconds must be >= 1. "
                    f"Got: {self.poll_interval_seconds.value}"
                )
                extension_manager.add_error(
                    exc,
                    field="poll_interval_seconds",
                    value=self.poll_interval_seconds.value,
                )

    def _validate_maximum_wait_seconds(self):
        """Validate maximum_wait_seconds is >= poll_interval_seconds."""
        if (
            self.maximum_wait_seconds is not None
            and self.poll_interval_seconds is not None
        ):
            if self.maximum_wait_seconds.value < self.poll_interval_seconds.value:
                exc = DataValidationError(
                    f"maximum_wait_seconds ({self.maximum_wait_seconds.value}) must be >= "
                    f"poll_interval_seconds ({self.poll_interval_seconds.value})"
                )
                extension_manager.add_error(
                    exc,
                    field="maximum_wait_seconds",
                    value=self.maximum_wait_seconds.value,
                )

    def _validate_unknown_status_retry_count(self):
        """Validate unknown_status_retry_count is not negative (minimum 0)."""
        if self.unknown_status_retry_count is not None:
            if self.unknown_status_retry_count.value < 0:
                exc = DataValidationError(
                    f"unknown_status_retry_count must be >= 0. "
                    f"Got: {self.unknown_status_retry_count.value}"
                )
                extension_manager.add_error(
                    exc,
                    field="unknown_status_retry_count",
                    value=self.unknown_status_retry_count.value,
                )
