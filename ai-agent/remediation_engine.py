# Author: Sourav Chandra
import os
import json
from pathlib import Path
from typing import Dict, Any
from llm import call_llm


class RemediationEngine:
    """
    Tier-1 Enhancement:
    AI-powered remediation suggestions based on analyzer output
    """

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.output_path = Path("analysis_results/remediation_suggestions.json")

    def suggest_fixes(self, analyzer_results: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
You are a Staff+ DevSecOps Engineer.

Given the following analyzer findings, generate remediation guidance.

Rules:
- Suggest FIX snippets only (not full files)
- Group by tool / language
- Prioritize CRITICAL and HIGH issues
- Output STRICT JSON

Analyzer Results:
{json.dumps(analyzer_results, indent=2)}
"""

        llm_response = call_llm(provider="openai", prompt=prompt)

        try:
            remediation = json.loads(llm_response.get("full", "{}"))
        except Exception:
            remediation = {
                "error": "Failed to parse LLM output",
                "raw_output": llm_response.get("full", "")
            }

        self._save(remediation)
        return remediation

    def _save(self, remediation: Dict[str, Any]) -> None:
        os.makedirs(self.output_path.parent, exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(remediation, f, indent=2)


# ---- Backward compatibility (optional) ----
def generate_remediation(analyzer_results: dict) -> dict:
    engine = RemediationEngine(os.getcwd())
    return engine.suggest_fixes(analyzer_results)


def save_remediation(remediation: dict, path="analysis_results/remediation_suggestions.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(remediation, f, indent=2)
