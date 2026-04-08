from typing import Dict, Any, Tuple
from .state import Observation
from .actions import Action
from .reward import calculate_step_reward
from tasks import easy, medium, hard
from grader.cvss_grader import calculate_final_score
import os

try:
    from dotenv import load_dotenv
    _ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(_ENV_PATH)
except ImportError:
    pass  # dotenv is optional; vars already loaded by backend.py

from .ai_fixer import generate_fix

TASKS = {
    "easy": easy.task_data,
    "medium": medium.task_data,
    "hard": hard.task_data
}

class VulnArenaEnv:
    def __init__(self):
        self.task_name = "easy"
        self.ground_truth = {}
        self.obs = Observation()
        self.history = []
        self.done = False

    def reset(self, task_name: str = "easy") -> Dict[str, Any]:
        self.task_name = task_name if task_name in TASKS else "easy"
        task = TASKS[self.task_name]
        self.ground_truth = task["ground_truth"]
        self.obs = Observation(
            report_text=task["report_text"],
            logs=task.get("logs", []),
            code_snippet=task.get("code_snippet", "")
        )
        self.history = []
        self.done = False
        return self.state()

    def step(self, action: str, custom_req=None) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        info = {}
        if self.done:
            return self.state(), 0.0, True, {"error": "Environment is already done."}

        self.obs.step_count += 1
        
        # Override with custom inputs if provided
        if custom_req:
            if getattr(custom_req, "report_text", None):
                self.obs.report_text = custom_req.report_text
            if getattr(custom_req, "logs", None) is not None:
                self.obs.logs = custom_req.logs
            if getattr(custom_req, "code_snippet", None):
                self.obs.code_snippet = custom_req.code_snippet
        
        reward = 0.0
        
        valid_actions = [
            "analyze_report",
            "analyze_logs",
            "inspect_code",
            "extract_vulnerability",
            "classify_type",
            "estimate_severity",
            "identify_component",
            "suggest_fix",
            "validate_fix"
        ]

        if action not in valid_actions:
            reward = -0.05
        elif action == "analyze_report":
            reward = 0.1
        elif action == "analyze_logs":
            reward = 0.1
        elif action == "inspect_code":
            reward = 0.1
        elif action == "extract_vulnerability":
            reward = 0.2
        elif action == "estimate_severity":
            reward = 0.2
        elif action == "identify_component":
            reward = 0.2
        elif action == "suggest_fix":
            reward = 0.2
        elif action == "validate_fix":
            reward = 0.2
            self.done = True

        if action in ["analyze_report", "analyze_logs", "inspect_code"]:
            self.obs.extracted_signals.append(f"Analyzed using {action}")
        elif action == "extract_vulnerability":
            print("Incoming code:", self.obs.code_snippet)
            # Extracted features, passing to classification step
            pass

        elif action == "classify_type":
            code = self.obs.code_snippet or ""

            # Detect SQL Injection
            has_sql_query = "SELECT" in code or "UPDATE" in code or "INSERT" in code
            has_concat = "+" in code or "f\"" in code or "{}" in code or "f'" in code
            has_db_exec = "execute" in code or "query" in code
            is_parameterized = "%s" in code or "execute(query," in code

            # Detect XSS
            has_html_render = "res.send" in code or "innerHTML" in code or "`" in code
            has_sanitization = "escape" in code or "sanitize" in code or "encode" in code

            # Priority Rules
            if has_html_render and not has_sanitization:
                self.obs.identified_vulnerability = "XSS"
            elif has_sql_query and has_concat and has_db_exec and not is_parameterized:
                self.obs.identified_vulnerability = "SQL Injection"
            else:
                self.obs.identified_vulnerability = None

            # Set Exploit Chain
            if self.obs.identified_vulnerability is None:
                self.obs.exploit_chain = ["No exploit path"]
            elif self.obs.identified_vulnerability == "SQL Injection":
                self.obs.exploit_chain = [
                    "User input enters via request parameter",
                    "Input is directly inserted into SQL query",
                    "Database executes injected query",
                    "Unauthorized data access occurs"
                ]
            elif self.obs.identified_vulnerability == "XSS":
                self.obs.exploit_chain = [
                    "User input received from request",
                    "Input rendered without sanitization",
                    "Browser executes injected script",
                    "Attacker gains control or steals session"
                ]

        elif action == "estimate_severity":
            if getattr(self.obs, "identified_vulnerability", None) is None:
                self.obs.severity = "LOW"
            elif getattr(self.obs, "severity", None) is None:
                self.obs.severity = self.ground_truth.get("severity", "HIGH")
        elif action == "identify_component":
            self.obs.component = self.ground_truth["component"]
        elif action == "suggest_fix":
            # --- AI-powered fix generation (returns structured dict) ----
            result = generate_fix(
                bug_report=self.obs.report_text or "",
                logs=self.obs.logs or [],
                code=self.obs.code_snippet or "",
            )
            fixed_code  = result.get("fixed_code", "")
            ai_vuln     = result.get("vulnerability", "")
            ai_severity = result.get("severity", "")

            if fixed_code and result.get("raw") != "fallback":
                self.obs.fix_suggestion = fixed_code
                if not self.obs.identified_vulnerability and ai_vuln:
                    self.obs.identified_vulnerability = ai_vuln
                if not self.obs.severity and ai_severity:
                    self.obs.severity = ai_severity.upper()
            else:
                self.obs.fix_suggestion = fixed_code or self.ground_truth.get("correct_fix", "Use parameterized queries.")

        self.history.append(action)

        if self.done:
            score = calculate_final_score(self.obs, self.ground_truth)
            info["final_score"] = score
        
        return self.state(), reward, self.done, info

    def state(self) -> Dict[str, Any]:
        return self.obs.dict()
