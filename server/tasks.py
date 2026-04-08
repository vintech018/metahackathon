"""Compatibility export for validators that import server.tasks."""

from tasks.task_definitions import TASKS
from tasks.graders import grade

__all__ = ["TASKS", "grade"]
