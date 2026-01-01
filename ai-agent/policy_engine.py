# Author: Sourav Chandra
import yaml
import os
from typing import Dict

POLICY_FILE = "policies/default.yaml"

def load_policies(path=POLICY_FILE) -> Dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def evaluate_policies(analyzer_results: dict) -> Dict:
    policies = load_policies()
    violations = {}
    for tool, results in analyzer_results.items():
        tool_policy = policies.get(tool, {})
        for key, rules in tool_policy.items():
            value = results.get(key)
            if value and value > rules.get("threshold", float("inf")):
                violations[f"{tool}.{key}"] = f"Value {value} exceeds threshold {rules.get('threshold')}"
    return violations
