"""
Multi-step LLM Reasoning Engine for vulnerability triage.

Implements a chain-of-thought pipeline:
    Step 1 — Identify vulnerability type(s)
    Step 2 — Assess impact and blast radius
    Step 3 — Assign severity with justification
    Step 4 — Suggest detailed remediation

Each step builds on the previous, enabling rich explainability.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from agent.config import LLMConfig

# ── System prompts for each reasoning step ────────────────────────────────────

SYSTEM_PROMPT_BASE = """\
You are an expert cybersecurity analyst specializing in vulnerability triage \
for bug bounty programs. You have deep knowledge of OWASP Top 10, CVSS scoring, \
CWE classifications, and industry-standard remediation practices.

You analyze vulnerability reports with precision, even when reports are \
poorly written, incomplete, or contain misleading severity claims."""

STEP1_PROMPT = """\
STEP 1 — VULNERABILITY IDENTIFICATION

Analyze the following vulnerability report and identify:
1. The primary vulnerability type (e.g., SQL Injection, XSS, SSRF, IDOR, etc.)
2. Any secondary vulnerabilities mentioned
3. Whether this is a chained/multi-step attack
4. Key technical indicators that support your classification

Report:
{report}

{context}

Respond in JSON format:
{{
    "primary_vulnerability": "string",
    "secondary_vulnerabilities": ["string"],
    "is_chained": true/false,
    "technical_indicators": ["string"],
    "confidence": 0.0-1.0,
    "reasoning": "string"
}}"""

STEP2_PROMPT = """\
STEP 2 — IMPACT ASSESSMENT

Given your vulnerability identification from Step 1, assess the impact:
1. What is the blast radius? (single user, all users, infrastructure)
2. What data is at risk? (PII, credentials, financial, system)
3. Is authentication required to exploit?
4. Is user interaction required?
5. What is the attack complexity?

Step 1 Analysis:
{step1_result}

Original Report:
{report}

{context}

Respond in JSON format:
{{
    "blast_radius": "single_user|all_users|infrastructure",
    "data_at_risk": ["string"],
    "auth_required": true/false,
    "user_interaction_required": true/false,
    "attack_complexity": "low|medium|high",
    "exploitability": "trivial|moderate|difficult",
    "business_impact": "string",
    "reasoning": "string"
}}"""

STEP3_PROMPT = """\
STEP 3 — SEVERITY ASSIGNMENT & COMPONENT IDENTIFICATION

Based on your analysis from Steps 1 and 2, determine:
1. Severity: critical, high, medium, or low
2. Primary affected component: auth, database, api, frontend, or network

Use this rubric:
- CRITICAL: RCE, full auth bypass, mass data breach, infrastructure compromise
- HIGH: Significant data exposure, privilege escalation, stored XSS with impact
- MEDIUM: Limited data exposure, CSRF, less impactful vulns
- LOW: Information disclosure, minor issues, theoretical attacks

Component mapping:
- auth: Authentication/authorization, session management, JWT, OAuth
- database: SQL injection, data storage, query manipulation
- api: REST/GraphQL endpoints, server-side logic, file upload
- frontend: XSS, CSRF, client-side issues, UI rendering
- network: SSRF, DNS, infrastructure, cloud metadata

Step 1 Analysis:
{step1_result}

Step 2 Analysis:
{step2_result}

Original Report:
{report}

{context}

Respond in JSON format:
{{
    "severity": "critical|high|medium|low",
    "component": "auth|database|api|frontend|network",
    "severity_justification": "string",
    "component_justification": "string",
    "cvss_estimate": 0.0-10.0,
    "confidence": 0.0-1.0
}}"""

STEP4_PROMPT = """\
STEP 4 — REMEDIATION RECOMMENDATION

Provide detailed, actionable remediation for the identified vulnerabilities.

Requirements:
- Be specific and technical (not generic advice)
- Address ALL vulnerabilities identified (primary and secondary)
- If it's a chained attack, address each link in the chain
- Include both immediate fixes and long-term hardening
- Reference relevant security standards (OWASP, CWE) when applicable

Step 1 (Vulnerability):
{step1_result}

Step 2 (Impact):
{step2_result}

Step 3 (Severity & Component):
{step3_result}

Original Report:
{report}

{context}

Respond in JSON format:
{{
    "remediation": "detailed remediation text covering all identified vulnerabilities",
    "immediate_actions": ["string"],
    "long_term_hardening": ["string"],
    "relevant_standards": ["CWE-xxx", "OWASP xxx"],
    "testing_recommendations": ["string"]
}}"""


@dataclass
class ReasoningTrace:
    """Complete record of the multi-step reasoning process."""
    report: str = ""
    step1_vuln_identification: dict[str, Any] = field(default_factory=dict)
    step2_impact_assessment: dict[str, Any] = field(default_factory=dict)
    step3_severity_component: dict[str, Any] = field(default_factory=dict)
    step4_remediation: dict[str, Any] = field(default_factory=dict)
    final_action: dict[str, str] = field(default_factory=dict)
    total_tokens_used: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step1_vuln_identification": self.step1_vuln_identification,
            "step2_impact_assessment": self.step2_impact_assessment,
            "step3_severity_component": self.step3_severity_component,
            "step4_remediation": self.step4_remediation,
            "final_action": self.final_action,
            "total_tokens_used": self.total_tokens_used,
            "error": self.error,
        }

    def summary(self) -> str:
        """Human-readable summary of the reasoning chain."""
        parts = []
        if self.step1_vuln_identification:
            parts.append(
                f"[Step 1] Vuln: {self.step1_vuln_identification.get('primary_vulnerability', '?')}"
            )
        if self.step2_impact_assessment:
            parts.append(
                f"[Step 2] Blast: {self.step2_impact_assessment.get('blast_radius', '?')}, "
                f"Exploit: {self.step2_impact_assessment.get('exploitability', '?')}"
            )
        if self.step3_severity_component:
            parts.append(
                f"[Step 3] {self.step3_severity_component.get('severity', '?').upper()} → "
                f"{self.step3_severity_component.get('component', '?')}"
            )
        if self.final_action:
            parts.append(
                f"[Final] severity={self.final_action.get('severity')}, "
                f"component={self.final_action.get('component')}"
            )
        return " | ".join(parts) if parts else "No reasoning steps completed."


def _extract_json(text: str) -> dict[str, Any]:
    """Extract JSON object from LLM response, handling markdown fences."""
    # Try to find JSON in code fences first
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return json.loads(fence_match.group(1))

    # Try to find raw JSON
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return json.loads(brace_match.group(0))

    raise ValueError(f"No JSON found in response: {text[:200]}...")


class LLMReasoningEngine:
    """
    Multi-step reasoning engine that uses an LLM to analyze vulnerability
    reports through a structured chain-of-thought pipeline.
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self._config = config or LLMConfig()
        self._client: OpenAI | None = None
        self._total_tokens = 0

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._config.validate()
            self._client = OpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
            )
        return self._client

    def _call_llm(self, system: str, user: str) -> tuple[str, int]:
        """Make a single LLM call. Returns (content, tokens_used)."""
        client = self._get_client()
        response = client.chat.completions.create(
            model=self._config.model,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0
        self._total_tokens += tokens
        return content, tokens

    def _safe_parse(self, response: str, step_name: str) -> dict[str, Any]:
        """Parse JSON from LLM response with fallback."""
        try:
            return _extract_json(response)
        except (json.JSONDecodeError, ValueError) as e:
            return {"parse_error": str(e), "raw_response": response[:500]}

    def analyze(
        self,
        report: str,
        reflection_context: str = "",
    ) -> ReasoningTrace:
        """
        Run the full 4-step reasoning pipeline on a vulnerability report.

        Parameters
        ----------
        report : str
            Raw vulnerability report text.
        reflection_context : str
            Optional context from past reflections to improve analysis.

        Returns
        -------
        ReasoningTrace
            Complete reasoning trace with all intermediate results.
        """
        trace = ReasoningTrace(report=report)
        context = f"\nIMPORTANT CONTEXT FROM PAST ANALYSIS:\n{reflection_context}" if reflection_context else ""

        try:
            # ── Step 1: Vulnerability Identification ──────────────────────
            prompt1 = STEP1_PROMPT.format(report=report, context=context)
            resp1, tok1 = self._call_llm(SYSTEM_PROMPT_BASE, prompt1)
            trace.step1_vuln_identification = self._safe_parse(resp1, "Step 1")
            trace.total_tokens_used += tok1

            # ── Step 2: Impact Assessment ─────────────────────────────────
            prompt2 = STEP2_PROMPT.format(
                step1_result=json.dumps(trace.step1_vuln_identification, indent=2),
                report=report,
                context=context,
            )
            resp2, tok2 = self._call_llm(SYSTEM_PROMPT_BASE, prompt2)
            trace.step2_impact_assessment = self._safe_parse(resp2, "Step 2")
            trace.total_tokens_used += tok2

            # ── Step 3: Severity & Component ──────────────────────────────
            prompt3 = STEP3_PROMPT.format(
                step1_result=json.dumps(trace.step1_vuln_identification, indent=2),
                step2_result=json.dumps(trace.step2_impact_assessment, indent=2),
                report=report,
                context=context,
            )
            resp3, tok3 = self._call_llm(SYSTEM_PROMPT_BASE, prompt3)
            trace.step3_severity_component = self._safe_parse(resp3, "Step 3")
            trace.total_tokens_used += tok3

            # ── Step 4: Remediation ───────────────────────────────────────
            prompt4 = STEP4_PROMPT.format(
                step1_result=json.dumps(trace.step1_vuln_identification, indent=2),
                step2_result=json.dumps(trace.step2_impact_assessment, indent=2),
                step3_result=json.dumps(trace.step3_severity_component, indent=2),
                report=report,
                context=context,
            )
            resp4, tok4 = self._call_llm(SYSTEM_PROMPT_BASE, prompt4)
            trace.step4_remediation = self._safe_parse(resp4, "Step 4")
            trace.total_tokens_used += tok4

            # ── Build final action ────────────────────────────────────────
            trace.final_action = {
                "severity": trace.step3_severity_component.get("severity", "medium"),
                "component": trace.step3_severity_component.get("component", "api"),
                "remediation": trace.step4_remediation.get(
                    "remediation",
                    "Apply security best practices and conduct thorough review."
                ),
            }

        except Exception as e:
            trace.error = f"{type(e).__name__}: {e}"
            # Provide safe fallback
            if not trace.final_action:
                trace.final_action = {
                    "severity": "medium",
                    "component": "api",
                    "remediation": "Unable to fully analyze. Apply defense-in-depth.",
                }

        return trace

    def analyze_quick(self, report: str, reflection_context: str = "") -> dict[str, str]:
        """
        Single-shot analysis (no multi-step). Faster but less explainable.
        Used as fallback or for simple cases.
        """
        context = f"\nContext from past analysis:\n{reflection_context}" if reflection_context else ""

        prompt = f"""\
Analyze this vulnerability report and provide a triage decision.

Report:
{report}

{context}

Respond in JSON:
{{
    "severity": "critical|high|medium|low",
    "component": "auth|database|api|frontend|network",
    "remediation": "detailed remediation steps"
}}"""

        try:
            resp, _ = self._call_llm(SYSTEM_PROMPT_BASE, prompt)
            result = _extract_json(resp)
            return {
                "severity": result.get("severity", "medium"),
                "component": result.get("component", "api"),
                "remediation": result.get("remediation", "Apply security best practices."),
            }
        except Exception:
            return {
                "severity": "medium",
                "component": "api",
                "remediation": "Apply defense-in-depth security measures.",
            }

    @property
    def total_tokens(self) -> int:
        return self._total_tokens
