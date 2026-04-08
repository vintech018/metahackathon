from grader.cvss_grader import calculate_final_score


grader = calculate_final_score

task_data = {
    "id": "legacy_hard_xss_csrf_chain",
    "difficulty": "hard",
    "grader": grader,
    "report_text": "A user reported their session was hijacked. They clicked a link in a blog comment.",
    "logs": ["GET /blog/123 200 OK", "POST /admin/delete_user 200 OK"],
    "code_snippet": "return render_template('blog.html', comment=request.args.get('comment'))",
    "ground_truth": {
        "vulnerability_type": "Cross-Site Scripting (XSS) + CSRF",
        "severity": "Critical",
        "component": "Blog Comments / Admin API",
        "exploit_chain": ["Inject malicious script in comment", "Admin views comment", "Script steals session or makes unauthorized API call"],
        "correct_fix": "Escape user input in templates and implement Anti-CSRF tokens for admin endpoints."
    }
}
