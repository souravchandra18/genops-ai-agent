# Author: Sourav Chandra
import os
import json
from github import Github, Auth
from ai-agent.remediation_engine import generate_remediation, save_remediation

def create_remediation_pr(repo_root, pr_title="AI Remediation PR", branch="genops-remediation"):
    # Load analyzer results
    with open(os.path.join("analysis_results", "analyzer_results.json"), "r") as f:
        analyzer_results = json.load(f)

    remediation = generate_remediation(analyzer_results)
    save_remediation(remediation)

    # GitHub PR creation
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPOSITORY")
    gh = Github(auth=Auth.Token(token))
    repo = gh.get_repo(repo_name)

    # Create branch
    default_branch = repo.default_branch
    source = repo.get_branch(default_branch)
    try:
        repo.create_git_ref(ref=f"refs/heads/{branch}", sha=source.commit.sha)
    except Exception:
        pass  # branch may exist

    # Commit remediation file
    repo.create_file(
        path="analysis_results/remediation_suggestions.json",
        message="AI remediation suggestions",
        content=json.dumps(remediation, indent=2),
        branch=branch
    )

    # Create PR
    pr = repo.create_pull(title=pr_title, body="AI-generated remediation PR", head=branch, base=default_branch)
    return pr.html_url
