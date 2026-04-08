"""Legacy task registry used by the original VulnArena environment."""

from tasks.easy import task_data as easy_task
from tasks.hard import task_data as hard_task
from tasks.medium import task_data as medium_task


ALL_TASKS = [easy_task, medium_task, hard_task]
