# Author: Sourav Chandra
import os
from github import Github, Auth

def enforce_pr_block(genops_data: dict, pr_number=None):
    if not pr_number:
        return "No PR context found"
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPOSITORY")
    gh = Github(auth=Auth.Token(token))
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))

    # Block if risk_level is high
    risk = genops_data.get("risk_level", "Medium")
    if risk.upper() == "HIGH":
        pr.create_issue_comment("🚫 PR blocked by GenOps Guardian: High risk detected")
        pr.edit(state="closed")
        return f"PR {pr_number} blocked due to HIGH risk"
    return f"PR {pr_number} allowed (risk: {risk})"
