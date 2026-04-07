from typing import Dict, Any

def calculate_step_reward(action_obj, ground_truth: Dict[str, Any], obs: Any, history: list) -> float:
    reward = 0.0
    if action_obj.value in history:
        return -0.02 # Penalize repeated action
        
    from .actions import Action
    if action_obj == Action.EXTRACT_VULNERABILITY:
        reward = 0.2
    elif action_obj == Action.ESTIMATE_SEVERITY:
        reward = 0.2
    elif action_obj == Action.IDENTIFY_COMPONENT:
        reward = 0.2
    elif action_obj == Action.CHAIN_VULNERABILITIES:
        reward = 0.2
    elif action_obj == Action.SUGGEST_FIX:
        reward = 0.2
    return reward
