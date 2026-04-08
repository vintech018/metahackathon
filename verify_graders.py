"""Sanity check for the Phase 2 task/grader compatibility layer."""

from __future__ import annotations

from app.environment import VulnerabilityTaskEnv
from app.models import Action, VulnerabilityComponent, VulnerabilitySeverity
from tasks.graders import grade
from tasks.task_definitions import TASKS


def make_perfect_action(ground_truth: dict[str, object]) -> Action:
    return Action(
        severity=VulnerabilitySeverity(str(ground_truth["severity"])),
        component=VulnerabilityComponent(str(ground_truth["component"])),
        remediation=" ".join(ground_truth.get("remediation_keywords", [])),
    )


def make_wrong_action() -> Action:
    return Action(
        severity=VulnerabilitySeverity.LOW,
        component=VulnerabilityComponent.API,
        remediation="apply generic best practices",
    )


def main() -> None:
    task_scores: list[float] = []

    for task_id, task in TASKS.items():
        env = VulnerabilityTaskEnv()
        reset_result = env.reset(task_id=task_id)
        assert reset_result.observation.task_id == task_id

        for ticket in task["tickets"]:
            reward = grade(make_perfect_action(ticket["_ground_truth"]), ticket["_ground_truth"], task_id)
            assert 0.0 < reward.total < 1.0

        done = False
        while not done:
            current_ticket = task["tickets"][env.state().current_ticket_index]
            result = env.step(make_perfect_action(current_ticket["_ground_truth"]))
            assert 0.0 < result.reward.total < 1.0
            done = result.done

        final_state = env.state()
        assert 0.0 < final_state.task_score < 1.0
        task_scores.append(final_state.task_score)

        wrong_reward = grade(make_wrong_action(), task["tickets"][0]["_ground_truth"], task_id)
        assert 0.0 < wrong_reward.total < 1.0

    assert len(task_scores) >= 3
    print({"task_count": len(TASKS), "task_scores": task_scores})


if __name__ == "__main__":
    main()
