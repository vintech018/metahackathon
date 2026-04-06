from env.triage_env import TriageEnv

# Create environment
env = TriageEnv(debug=True)

# Reset environment
obs = env.reset()
print("\n--- OBSERVATION ---")
print(obs)

# Example correct action (for SQL injection case)
action = {
    "severity": "critical",
    "component": "database",
    "remediation": "use parameterized queries"
}

# Step
obs, reward, done, info = env.step(action)

print("\n--- RESULT ---")
print("Reward:", reward)
print("Done:", done)

print("\n--- INFO ---")
for key, value in info.items():
    print(f"{key}: {value}")