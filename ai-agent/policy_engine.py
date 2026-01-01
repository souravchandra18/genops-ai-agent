# Author: Sourav Chandra
import json
import yaml
from pathlib import Path
from typing import Dict, Any


class PolicyEngine:
    def __init__(self, policy_path: str):
        self.policy_path = Path(policy_path)
        self.policies = self._load_policies()

    def _load_policies(self) -> Dict[str, Any]:
        if not self.policy_path.exists():
            return {}
        with open(self.policy_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _count_issues(self, result: dict) -> int:
        """
        Attempts to count findings from tool output.
        Works across JSON, list, and raw text outputs.
        """
        if not isinstance(result, dict):
            return 0

        stdout = result.get("stdout", "")
        try:
            parsed = json.loads(stdout)

            if isinstance(parsed, list):
                return len(parsed)

            if isinstance(parsed, dict):
                for key in ["results", "issues", "violations", "findings"]:
                    if key in parsed and isinstance(parsed[key], list):
                        return len(parsed[key])

                return len(parsed)

        except Exception:
            pass

        # Fallback: count non-empty lines
        return len([l for l in stdout.splitlines() if l.strip()])

    def evaluate(self, analyzer_results: dict, genops_data: dict) -> Dict[str, Any]:
        compliance = {
            "overall_status": "PASS",
            "violations": [],
            "risk_level": genops_data.get("risk_level", "Medium")
        }

        for language, tools in self.policies.items():
            for tool_name, rule in tools.items():
                result = analyzer_results.get(tool_name)
                if not result:
                    continue

                issues = self._count_issues(result)
                threshold = rule.get("threshold", float("inf"))

                if issues > threshold:
                    compliance["overall_status"] = "FAIL"
                    compliance["violations"].append({
                        "tool": tool_name,
                        "issues": issues,
                        "threshold": threshold
                    })

        return compliance
