# Author: Sourav Chandra
import os
import json
from llm import call_llm

def generate_remediation(analyzer_results: dict) -> dict:
    prompt = f"""
You are an expert DevOps & Security AI.
Based on the following analyzer results, suggest remediation steps (fix snippets, not full files):

{json.dumps(analyzer_results, indent=2)}
"""
    llm_response = call_llm(provider='openai', prompt=prompt)
    try:
        remediation = json.loads(llm_response.get("full", "{}"))
    except Exception:
        remediation = {"suggestions": ["Could not parse AI output."]}
    return remediation

def save_remediation(remediation: dict, path="analysis_results/remediation_suggestions.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(remediation, f, indent=2)
