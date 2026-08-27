"""Actions module - Business logic implementations."""

from actions.output import ActionOutput
from actions.schedule_and_monitor_report import schedule_and_monitor_report
from manager import ExtensionManager

extension_manager = ExtensionManager()

# Map action names to functions
ACTION_MAPPER = {
    "Schedule and Monitor Report": schedule_and_monitor_report,
}
