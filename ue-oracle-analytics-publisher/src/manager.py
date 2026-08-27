from typing import Optional, List, Dict, Any
from exceptions import ExecutionError

class ExtensionManager:
    """
    Singleton for managing extension state: errors, result, and cancellation.

    Provides:
    - Strategic error collection
    - Partial result data storage
    - Cancellation flag for graceful termination

    Usage:
        # In input validation - collect all errors
        exc = DataValidationError("Port invalid")
        extension_manager.add_error(exc, field="port", value=port)

        # In actions - check cancellation
        if extension_manager.is_cancelled():
            raise OperationCancelledError("User cancelled")

        # In actions - fail fast on blocking errors
        exc = ConnectionError("Failed to connect")
        extension_manager.add_error(exc)
        raise exc
    """

    _instance = None
    _errors: List[Dict[str, Any]] = []
    _result: Optional[Dict[str, Any]] = None
    _cancelled: bool = False

    def __new__(cls):
        """Ensure singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._errors = []
            cls._result = None
            cls._cancelled = False
        return cls._instance

    def clear(self):
        """Clear all errors, result, and cancelled flag. Call at extension start."""
        self._errors = []
        self._result = None
        self._cancelled = False

    def add_error(self, exception: ExecutionError, **kwargs):
        """
        Add exception to error collection.

        Args:
            exception: The exception object to add
            **kwargs: Additional context (field, value, etc.)

        Example:
            exc = DataValidationError("Port must be 1-65535")
            error_manager.add_error(exc, field="port", value=99999)
        """
        error_entry = {
            "type": type(exception).__name__,
            "message": str(exception),
            "exit_code": exception.exit_code
        }
        error_entry.update(kwargs)
        self._errors.append(error_entry)

    def set_result(self, result: Dict[str, Any]):
        """
        Set partial result data (for error cases).

        Use this to store what was accomplished before error occurred.

        Args:
            result: Dictionary with partial result data

        Example:
            error_manager.set_result({
                "processed_count": 25,
                "total_count": 100,
                "failed_items": ["item-26"]
            })
        """
        self._result = result

    def has_errors(self) -> bool:
        """Check if any errors collected."""
        return len(self._errors) > 0

    def error_count(self) -> int:
        """Get number of errors collected."""
        return len(self._errors)

    def to_array(self) -> List[Dict[str, Any]]:
        """Get errors as array for unv_output."""
        return self._errors.copy()

    @property
    def result(self) -> Optional[Dict[str, Any]]:
        """Get result data."""
        return self._result

    @property
    def errors(self) -> List[Dict[str, Any]]:
        """Get errors list."""
        return self._errors.copy()

    def set_cancelled(self):
        """Set the cancellation flag. Called by extension_cancel()."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        """Check if extension has been cancelled."""
        return self._cancelled

    @property
    def cancelled(self) -> bool:
        """Get cancellation status."""
        return self._cancelled
