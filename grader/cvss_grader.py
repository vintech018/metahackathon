def calculate_final_score(obs, ground_truth):
    score = 0.0
    weights = {
        "vulnerability": 0.2,
        "severity": 0.2,
        "component": 0.2,
        "exploit_chain": 0.2,
        "fix": 0.2
    }
    
    if obs.identified_vulnerability == ground_truth.get("vulnerability_type"):
        score += weights["vulnerability"]
    if obs.severity == ground_truth.get("severity"):
        score += weights["severity"]
    if obs.component == ground_truth.get("component"):
        score += weights["component"]
    if obs.exploit_chain == ground_truth.get("exploit_chain"):
        score += weights["exploit_chain"]
    if obs.fix_suggestion == ground_truth.get("correct_fix"):
        score += weights["fix"]
        
    return min(1.0, score)
