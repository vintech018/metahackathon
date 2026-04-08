"""Phase 2 task registry exposed in the structure used by public hackathon examples."""

from __future__ import annotations

from typing import Any

from env.tasks import (
    TASK_EASY_INFO_DISCLOSURE,
    TASK_EASY_RCE,
    TASK_EASY_SQL_INJECTION,
    TASK_EASY_XSS,
    TASK_HARD_BROKEN_AUTH_CHAIN,
    TASK_HARD_SSRF_CHAIN,
    TASK_HARD_STORED_XSS_CHAIN,
    TASK_MEDIUM_CSRF,
    TASK_MEDIUM_IDOR,
    TASK_MEDIUM_TOKEN_REUSE,
)


def _extract_subject(report: str) -> str:
    first_line = report.splitlines()[0].strip() if report.strip() else "Untitled report"
    return first_line.removeprefix("Title: ").strip()


def _extract_body(report: str) -> str:
    lines = report.splitlines()
    if len(lines) <= 1:
        return report.strip()
    return "\n".join(line.rstrip() for line in lines[1:]).strip()


def _ticket(task: dict[str, Any], index: int, task_id: str) -> dict[str, Any]:
    subject = _extract_subject(task["report"])
    body = _extract_body(task["report"])
    return {
        "id": f"{task_id.upper()}-{index:03d}",
        "subject": subject,
        "body": body,
        "sender_email": f"researcher{index}@example.com",
        "created_at": f"2026-04-08T0{index}:00:00Z",
        "attachments": [],
        "_ground_truth": task["expected"],
    }


def _task_group(
    task_id: str,
    name: str,
    difficulty: str,
    description: str,
    source_tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "name": name,
        "difficulty": difficulty,
        "description": description,
        "tickets": [
            _ticket(source_task, index + 1, task_id)
            for index, source_task in enumerate(source_tasks)
        ],
    }


TASKS: dict[str, dict[str, Any]] = {
    "task_easy": _task_group(
        "task_easy",
        "Basic Vulnerability Triage",
        "easy",
        "Classify clear vulnerability reports with obvious severity and affected component.",
        [
            TASK_EASY_SQL_INJECTION,
            TASK_EASY_XSS,
            TASK_EASY_RCE,
            TASK_EASY_INFO_DISCLOSURE,
        ],
    ),
    "task_medium": _task_group(
        "task_medium",
        "Moderate Vulnerability Triage",
        "medium",
        "Handle authorization and session-management issues with less direct signals.",
        [
            TASK_MEDIUM_TOKEN_REUSE,
            TASK_MEDIUM_IDOR,
            TASK_MEDIUM_CSRF,
        ],
    ),
    "task_hard": _task_group(
        "task_hard",
        "Chained Attack Triage",
        "hard",
        "Reason about chained exploitation paths and broader remediation requirements.",
        [
            TASK_HARD_STORED_XSS_CHAIN,
            TASK_HARD_SSRF_CHAIN,
            TASK_HARD_BROKEN_AUTH_CHAIN,
        ],
    ),
}
