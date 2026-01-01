# Author: Sourav Chandra
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class AIUsageGuard:
    """
    Tier-3 Enhancement:
    AI governance, usage logging & LLM trust evaluation
    """

    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.results_dir = Path("analysis_results")
        self.usage_log = self.results_dir / "ai_usage_log.txt"
        self.trust_report = self.results_dir / "llm_trust_report.json"

        os.makedirs(self.results_dir, exist_ok=True)

    def scan_repo(self) -> None:
        """
        Placeholder for future Copilot / Cursor / CodeWhisperer scanning.
        Currently logs repository scan event.
        """
        self._log("AI usage scan executed")

    def evaluate_llm_trust(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        trust_score = 100
        issues = []

        if "error" in llm_response:
            trust_score -= 50
            issues.append(llm_response["error"])

        if "unstructured" in llm_response.get("full", "").lower():
            trust_score -= 20
            issues.append("Unstructured LLM output detected")

        report = {
            "trust_score": trust_score,
            "issues": issues,
            "evaluated_at": datetime.utcnow().isoformat()
        }

        with open(self.trust_report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report

    def _log(self, action: str, user: str = "system") -> None:
        with open(self.usage_log, "a", encoding="utf-8") as f:
            f.write(f"{datetime.utcnow().isoformat()} - {user} - {action}\n")


# ---- Backward compatibility ----
def log_ai_usage(action: str, user: str = "system"):
    guard = AIUsageGuard(os.getcwd())
    guard._log(action, user)


def evaluate_llm_trust(llm_response: dict):
    guard = AIUsageGuard(os.getcwd())
    return guard.evaluate_llm_trust(llm_response)
