# Author: Sourav Chandra
import os
import json
from datetime import datetime

USAGE_LOG = "analysis_results/ai_usage_log.txt"
TRUST_REPORT = "analysis_results/llm_trust_report.json"

def log_ai_usage(action: str, user: str = "system"):
    os.makedirs(os.path.dirname(USAGE_LOG), exist_ok=True)
    with open(USAGE_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()} - {user} - {action}\n")

def evaluate_llm_trust(llm_response: dict):
    # Simple heuristic: check for presence of "error" or "unstructured"
    trust_score = 100
    issues = []
    if "error" in llm_response:
        trust_score -= 50
        issues.append(llm_response["error"])
    if "unstructured" in llm_response.get("full", "").lower():
        trust_score -= 20
        issues.append("Unstructured output detected")
    report = {"trust_score": trust_score, "issues": issues}
    with open(TRUST_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report
