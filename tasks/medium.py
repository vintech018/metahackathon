from grader.cvss_grader import calculate_final_score


grader = calculate_final_score

task_data = {
    "id": "legacy_medium_upload_dos",
    "difficulty": "medium",
    "grader": grader,
    "report_text": "The application crashes randomly when uploading a large malformed PDF file.",
    "logs": ["POST /upload 500", "Worker thread paniced"],
    "code_snippet": "def handle_upload(file):\n    pdf_parser.parse(file.read())",
    "ground_truth": {
        "vulnerability_type": "Denial of Service (DoS) / Memory Exhaustion",
        "severity": "Medium",
        "component": "File Upload / PDF Parser",
        "exploit_chain": ["Upload large PDF", "Trigger uncontrolled memory allocation", "Crash worker thread"],
        "correct_fix": "Implement file size limits and stream parsing instead of reading entirely into memory."
    }
}
