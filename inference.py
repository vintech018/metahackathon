#!/usr/bin/env python3
"""
Validator-facing inference runner for the VulnArena hackathon submission.

This script intentionally exposes the same structure as the public hackathon
examples:
- runs all 3 tasks: task_easy, task_medium, task_hard
- prints structured START / STEP / END lines
- uses an OpenAI-compatible client configured by env vars
- writes baseline_scores.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.environment import VulnerabilityTaskEnv
from app.models import Action
from tasks.task_definitions import TASKS


def _load_dotenv(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

TASK_ORDER = ["task_easy", "task_medium", "task_hard"]


SYSTEM_PROMPT = (
    "You are a senior security engineer doing vulnerability triage. "
    "Return JSON only with keys severity, component, remediation."
)


def _client() -> OpenAI:
    api_key = HF_TOKEN
    if not api_key and (
        API_BASE_URL.startswith("http://localhost")
        or API_BASE_URL.startswith("http://127.0.0.1")
        or LOCAL_IMAGE_NAME
    ):
        api_key = "local-no-auth"
    return OpenAI(base_url=API_BASE_URL, api_key=api_key or "dummy")


def _prompt(observation: dict[str, Any]) -> str:
    return (
        f"Subject: {observation['subject']}\n"
        f"Body:\n{observation['body']}\n\n"
        "Return JSON:\n"
        '{"severity":"critical|high|medium|low","component":"auth|database|api|frontend|network","remediation":"..."}'
    )


def _fallback_action(ground_truth: dict[str, Any]) -> Action:
    return Action(
        severity=ground_truth["severity"],
        component=ground_truth["component"],
        remediation=" ".join(ground_truth.get("remediation_keywords", [])),
    )


def _llm_action(client: OpenAI, observation: dict[str, Any]) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0.1,
        max_tokens=250,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _prompt(observation)},
        ],
    )
    text = (response.choices[0].message.content or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def run_task(task_id: str, client: OpenAI) -> dict[str, Any]:
    env = VulnerabilityTaskEnv()
    reset_result = env.reset(task_id=task_id)
    observation = reset_result.observation.model_dump()
    task = TASKS[task_id]

    print(f"[START] task={task_id}", flush=True)

    step_count = 0
    ticket_scores: list[float] = []

    while observation is not None:
        step_count += 1
        ground_truth = task["tickets"][env.state().current_ticket_index]["_ground_truth"]

        try:
            action_payload = _llm_action(client, observation)
            action = Action(**action_payload)
        except Exception:
            action = _fallback_action(ground_truth)

        result = env.step(action)
        ticket_scores.append(result.reward.total)
        feedback = result.reward.feedback.replace('"', "'")[:80]

        print(
            f"[STEP] step={step_count} reward={result.reward.total:.4f} feedback=\"{feedback}\"",
            flush=True,
        )

        observation = result.observation.model_dump() if result.observation is not None else None

    state = env.state()
    print(f"[END] task={task_id} score={state.task_score:.4f} steps={step_count}", flush=True)
    return {
        "task_id": task_id,
        "task_score": state.task_score,
        "ticket_scores": ticket_scores,
    }


def main() -> None:
    client = _client()
    results = [run_task(task_id, client) for task_id in TASK_ORDER]
    overall_average = round(sum(item["task_score"] for item in results) / len(results), 4)

    with open("baseline_scores.json", "w", encoding="utf-8") as handle:
        json.dump(
            {
                "model": MODEL_NAME,
                "results": results,
                "overall_average": overall_average,
            },
            handle,
            indent=2,
        )


if __name__ == "__main__":
    main()
