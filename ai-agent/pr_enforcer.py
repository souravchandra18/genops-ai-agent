# Author: Sourav Chandra
import os
from typing import Dict, Any
from github import Github, Auth


class PREnforcer:
    """
    Tier-1 Enhancement:
    Automated PR enforcement based on GenOps risk & policy compliance
    """

    def __init__(self, pr_number: str | None):
        self.pr_number = pr_number
        self.token = os.getenv("GITHUB_TOKEN")
        self.repo_name = os.getenv("GITHUB_REPOSITORY")

        if self.token and self.repo_name:
            self.gh = Github(auth=Auth.Token(self.token))
            self.repo = self.gh.get_repo(self.repo_name)
        else:
            self.gh = None
            self.repo = None

    def evaluate(self, compliance_status: Dict[str, Any], genops_data: Dict[str, Any]) -> str:
        """
        Enforcement rules:
        - Block PR if GenOps risk is HIGH
        - Block PR if policy compliance failed
        """

        if not self.pr_number or not self.repo:
            return "No PR context available"

        pr = self.repo.get_pull(int(self.pr_number))

        reasons = []

        risk = genops_data.get("risk_level", "Medium").upper()
        if risk == "HIGH":
            reasons.append("HIGH GenOps risk detected")

        if compliance_status and compliance_status.get("status") == "FAIL":
            reasons.append("Policy compliance failure")

        if reasons:
            message = (
                "🚫 **PR Blocked by AI GenOps Guardian**\n\n"
                + "\n".join(f"- {r}" for r in reasons)
            )
            pr.create_issue_comment(message)
            pr.edit(state="closed")
            return f"PR {self.pr_number} blocked: {', '.join(reasons)}"

        pr.create_issue_comment(
            "✅ **AI GenOps Guardian**: PR passed automated risk & policy checks"
        )
        return f"PR {self.pr_number} allowed"


# ---- Backward compatibility ----
def enforce_pr_block(genops_data: dict, pr_number=None):
    enforcer = PREnforcer(pr_number)
    return enforcer.evaluate({}, genops_data)
