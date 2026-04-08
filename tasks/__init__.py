"""Legacy task registry used by the original VulnArena environment."""

from tasks.easy import task_data as easy_task
from tasks.hard import task_data as hard_task
from tasks.medium import task_data as medium_task
from tasks.task_definitions import TASKS


ALL_TASKS = [easy_task, medium_task, hard_task]

__all__ = ["ALL_TASKS", "TASKS"]
