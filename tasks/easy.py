task_data = {
    "report_text": "Users are able to view other users' profiles by modifying the ID parameter in the URL.",
    "logs": ["GET /profile?id=123 200 OK", "GET /profile?id=124 200 OK", "GET /profile?id=1 OR 1=1 500 ISE"],
    "code_snippet": "query = f'SELECT * FROM users WHERE id = {request.GET.get(\"id\")}'\ncursor.execute(query)",
    "ground_truth": {
        "vulnerability_type": "SQL Injection",
        "severity": "High",
        "component": "Profile View / Database",
        "exploit_chain": ["Identify ID parameter", "Inject SQL payload", "Extract unauthorized data"],
        "correct_fix": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', (request.GET.get('id'),))"
    }
}
