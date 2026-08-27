"""
Exceptions module template for UAC Universal Extensions.

This module provides:
- Base ExecutionError class
- Standard exception types (DataValidationError, ConnectionError, etc.)
- ErrorManager singleton for error collection
- Exit code conventions

CUSTOMIZE:
- Add custom exception types for your extension
- Modify ErrorManager methods if needed
"""
from typing import Optional

class ExecutionError(Exception):
    """
    The default error raised by an extension.

    All extension errors must inherit from it.

    Attrs:
        exit_code: The exit code of the extension (for UAC)
        message: The error message for status description
    """

    exit_code: int = 1
    message: str = "Execution Failed"

    def __init__(self, message: Optional[str] = None):
        """
        Initialize exception.

        Args:
            message: Optional message that will be appended to the default message.

        Note:
            To return result data with errors, use error_manager.set_result()
            before raising the exception.
        """
        if message:
            self.message = f"{self.message}: {message}"

        super().__init__(self.message)

class DataValidationError(ExecutionError):
    """Raised when an input field is invalid."""
    exit_code = 20
    message = "Data Validation Error"

class UnexpectedSystemError(ExecutionError):
    """Raised for unexpected system errors."""
    exit_code = 1
    message = "System Error"
