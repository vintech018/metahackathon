from enum import Enum

class Action(str, Enum):
    ANALYZE_REPORT = "analyze_report"
    ANALYZE_LOGS = "analyze_logs"
    INSPECT_CODE = "inspect_code"
    EXTRACT_VULNERABILITY = "extract_vulnerability"
    ESTIMATE_SEVERITY = "estimate_severity"
    IDENTIFY_COMPONENT = "identify_component"
    SIMULATE_ATTACK = "simulate_attack"
    CHAIN_VULNERABILITIES = "chain_vulnerabilities"
    SUGGEST_FIX = "suggest_fix"
    VALIDATE_FIX = "validate_fix"
