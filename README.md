# VulnArena AI - Autonomous Security Triage & Exploitation Simulator

A fully compliant OpenEnv environment designed to simulate real-world bug bounty and security triage workflows. The environment allows for evaluating AI agents' ability to inspect code, analyze logs, verify vulnerabilities, estimate severity, and formulate exploits.

## Features
- **3 Challenge Tasks**: Easy (SQL Injection), Medium (Memory DoS), Hard (XSS to Privilege Escalation).
- **Extensive Typed Observations**: Accurate and fully typed observation models strictly aligning with OpenEnv spec.
- **RESTful Endpoints**: Full API integration for `/reset`, `/step`, and `/state` state retrieval.
- **Deterministic Evaluation Grader**: Implements standard correctness and completion criteria via penalizations and robust rewards mechanics.

## Setup & Run locally

### Via Docker
Build the environment container:
```bash
docker build -t vulnarena .
```

Run the container:
```bash
docker run -p 8000:8000 vulnarena
```

### Validate OpenEnv Requirements
To evaluate the tasks by running an AI test loop with strict compliance:
```bash
export API_BASE_URL="http://localhost:8000"
export MODEL_NAME="gpt-4"
python inference.py
```
