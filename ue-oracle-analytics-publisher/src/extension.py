"""
Extension module template for UAC Universal Extensions.

This module provides the Extension class with extension_start() method that is called
by UAC when the extension task executes. It orchestrates all components:
- Input validation (InputFields)
- Action dispatch (ACTION_MAPPER)
- Output formatting (ActionOutput)
- Extension state management (ExtensionManager)
"""

import json

from universal_extension import UniversalExtension, ExtensionResult, logger
from fields.input import InputFields
from actions.output import ActionOutput
from actions import ACTION_MAPPER
from exceptions import ExecutionError, UnexpectedSystemError
from manager import ExtensionManager

# Extension metadata - UPDATE THESE FROM YOUR ANALYSIS
EXTENSION_NAME = "ue-oracle-analytics-publisher"
EXTENSION_VERSION = "1.0.0"

extension_manager = ExtensionManager()

# ============================================================================
# Extension Class
# ============================================================================

class Extension(UniversalExtension):
    """
    Universal Extension entry point.

    This class inherits from UniversalExtension as required by the UAC framework.
    """

    def extension_start(self, fields: dict) -> ExtensionResult:
        """
        Main entry point called by UAC when extension task executes.

        Flow:
        1. Preprocess fields via InputFields.preprocess_fields()
        2. Parse and validate input (InputFields)
        3. Dispatch to action (ACTION_MAPPER)
        4. Action executes, prints to STDOUT, returns ActionOutput
        5. Build ExtensionResult via build_result()
        6. Return ExtensionResult

        Args:
            fields: Dictionary containing all input field values from UAC

        Returns:
            ExtensionResult with rc, message, and optional unv_output
        """
        # Initialize extension manager at start
        extension_manager.clear()

        input_data = None
        processed_fields = {}

        try:
            logger.info("%s v%s started", EXTENSION_NAME, EXTENSION_VERSION)

            # Preprocess fields via InputFields static method
            processed_fields = InputFields.preprocess_fields(fields)

            # Parse and validate input (triggers validation in __post_init__)
            input_data = InputFields(**processed_fields)
            logger.info("Action requested: %s", input_data.action.value)

            # Get action function from mapper
            action_func = ACTION_MAPPER.get(input_data.action.value)

            # Execute action - action prints to STDOUT and returns ActionOutput
            logger.info("Executing action: %s", input_data.action.value)
            action_output: ActionOutput = action_func(input_data)

            # Print action output to STDOUT
            action_output.print_output()

            # Build success result
            logger.info("%s completed successfully", EXTENSION_NAME)
            return self.build_result(
                input_fields=input_data,
                result=action_output.to_dict()
            )
        except ExecutionError as e:
            # Custom extension exception (validation, auth, service errors, etc.)
            logger.error("Execution error: %s", e.message)

            # Add error to manager if not already collected
            if not e in extension_manager.errors:
                extension_manager.add_error(e)

            # Create InputFields without validation for error reporting
            if processed_fields:
                input_data = InputFields(**processed_fields, _skip_validation=True)

            return self.build_result(
                input_fields=input_data,
                result=extension_manager.result,
                errors=extension_manager.to_array(),
                exit_code=e.exit_code,
                status_description=e.message
            )
        except Exception as e:
            # Capture exception details for debugging
            error_msg = str(e) if str(e) else f"{type(e).__name__}"
            exc = UnexpectedSystemError(error_msg)
            extension_manager.add_error(exc)

            if processed_fields:
                input_data = InputFields(**processed_fields, _skip_validation=True)

            return self.build_result(
                input_fields=input_data,
                result=extension_manager.result,
                errors=extension_manager.to_array(),
                exit_code=exc.exit_code,
                status_description=exc.message
            )


    def build_result(
        self,
        input_fields: InputFields = None,
        result: dict = None,
        errors: list = None,
        exit_code: int = 0,
        status_description: str = "Successful Execution"
    ) -> ExtensionResult:
        """
        Build ExtensionResult with structured unv_output.

        Args:
            input_fields: Input fields (InputFields instance, optional)
            result: Result dictionary from action or ErrorManager
            errors: Errors array (empty list for success, error list for failures)
            exit_code: Exit code (0 for success, 1+ for errors)
            status_description: Human-readable status message

        Returns:
            ExtensionResult with structured unv_output

        Example (success):
            return self.build_result(
                input_fields=input_data,
                result=action_output.to_dict(),
                errors=[],
                exit_code=0,
                status_description=action_output.message
            )

        Example (error):
            return self.build_result(
                input_fields=input_data,
                result=extension_manager.result,
                errors=extension_manager.to_array(),
                exit_code=1,
                status_description="Execution failed"
            )
        """
        # Set defaults
        if result is None:
            result = {}
        if errors is None:
            errors = []

        # Convert input_fields to dict (if provided)
        # Uses to_dict() to exclude internal fields and empty previous_output
        input_dict = input_fields.to_dict() if input_fields else {}

        # Build unv_output structure
        unv_output = {
            "exit_code": exit_code,
            "status_description": status_description,
            "metadata": {
                "version": EXTENSION_VERSION,
                "extension": EXTENSION_NAME
            },
            "input_fields": input_dict,
            "result": result,
            "errors": errors
        }

        return ExtensionResult(
            rc=exit_code,
            message=status_description,
            unv_output=json.dumps(unv_output, indent=2, default=str)
        )

    def extension_cancel(self):
        """
        Called when extension is cancelled.

        Sets extension_manager.cancelled = True which can be checked in actions:
            if extension_manager.is_cancelled():
                raise OperationCancelledError("User cancelled")

        Override to add custom cleanup:
            def extension_cancel(self):
                super().extension_cancel()  # Set the cancelled flag
                logger.info("Cleaning up resources")
                # Close connections, cleanup files, etc.
        """
        extension_manager.set_cancelled()


    # ============================================================================
    # CUSTOMIZE: Add Dynamic Choice Commands (MUST be methods inside Extension class)
    # ============================================================================

    # Example dynamic choice command:
    #
    # from universal_extension.deco.choice import dynamic_choice_command
    #
    # @dynamic_choice_command("field_name")
    # def get_resources(self, fields: dict) -> ExtensionResult:
    #     """
    #     Dynamic choice function for resource selection.
    #
    #     Called by UAC when user opens the dropdown for 'field_name'.
    #     The field_name in decorator MUST match the field's "name" property in template.json.
    #     The field in template.json MUST have "choiceDynamic": true.
    #
    #     Args:
    #         fields: Current field values (for dependencies)
    #
    #     Returns:
    #         ExtensionResult with values parameter containing list of choices.
    #         Parameters: rc (int), message (str), values (List[str])
    #     """
    #     try:
    #         logger.info("Fetching available resources")
    #
    #         # May depend on other fields (extract as list)
    #         filter_type = fields.get("filter_type", [""])[0] if fields.get("filter_type") else None
    #
    #         # Query resources
    #         resources = ["resource1", "resource2", "resource3"]
    #
    #         logger.info("Found %d resources", len(resources))
    #         return ExtensionResult(
    #             rc=0,
    #             message="Successfully retrieved resources",
    #             values=resources
    #         )
    #
    #     except Exception as e:
    #         logger.error("Failed to fetch resources: %s", str(e))
    #         return ExtensionResult(
    #             rc=1,
    #             message=f"Failed to fetch resources: {str(e)}",
    #             values=[]
    #         )


    # ============================================================================
    # CUSTOMIZE: Add Extension Commands (MUST be methods inside Extension class)
    # ============================================================================

    # Example extension command:
    #
    # from universal_extension.deco.command import dynamic_command
    #
    # @dynamic_command(command_name="validate_configuration")
    # def validate_configuration(self, fields: dict) -> ExtensionResult:
    #     """
    #     Command to validate extension configuration.
    #
    #     Can be called independently from UAC without executing the extension.
    #     The command_name in decorator is used to invoke this command.
    #
    #     Args:
    #         fields: Current field values to validate
    #
    #     Returns:
    #         ExtensionResult indicating validation success/failure
    #     """
    #     try:
    #         logger.info("Validating configuration...")
    #
    #         # Extract and validate fields
    #         timeout = fields.get("timeout", 30)
    #         if timeout < 5:
    #             return ExtensionResult(
    #                 rc=1,
    #                 message="Timeout must be at least 5 seconds",
    #                 output=False,
    #                 output_data=None,
    #                 output_name=None
    #             )
    #
    #         logger.info("Configuration validated successfully")
    #         return ExtensionResult(
    #             rc=0,
    #             message="Configuration is valid",
    #             output=False,
    #             output_data=None,
    #             output_name=None
    #         )
    #
    #     except Exception as e:
    #         logger.error("Validation failed: %s", str(e))
    #         return ExtensionResult(
    #             rc=1,
    #             message=f"Validation error: {str(e)}",
    #             output=False,
    #             output_data=None,
    #             output_name=None
    #         )
    #
    # Example extension command with output data:
    #
    # @dynamic_command(command_name="get_system_info")
    # def get_system_info(self, _fields: dict) -> ExtensionResult:
    #     """Return extension and system information."""
    #     try:
    #         info = {
    #             "extension_name": EXTENSION_NAME,
    #             "extension_version": EXTENSION_VERSION,
    #             "python_version": "3.11"
    #         }
    #         return ExtensionResult(
    #             rc=0,
    #             message="System information retrieved",
    #             output=True,
    #             output_data=json.dumps(info, indent=2),
    #             output_name="system_info"
    #         )
    #     except Exception as e:
    #         return ExtensionResult(
    #             rc=1,
    #             message=f"Error: {str(e)}",
    #             output=False,
    #             output_data=None,
    #             output_name=None
    #         )
