# Author: Sourav Chandra
from convert import convert
from json_to_md import json_to_markdown
from pathlib import Path
import os
import json
import subprocess
from analyzers import detect_languages_and_tools, run_analyzers
from llm import call_llm
from github import Github, Auth
from openai import OpenAI


  # Note: Used only for GenOps Guardian

# ---------- Helpers ----------

def compact_results(analyzer_results, limit=1500):
    compact = {}
    for tool, data in analyzer_results.items():
        compact[tool] = {
            "returncode": data.get("returncode"),
            "stderr": data.get("stderr", "")[:limit],
            "stdout": data.get("stdout", "")[:limit]
        }
    return compact

def post_comment(pr_number, body):
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPOSITORY")
    gh = Github(auth=Auth.Token(token))
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))
    pr.create_issue_comment(body)

# ---------- Universal Agent ----------

def run_universal_agent(repo_root, llm_provider, run_semgrep):
    detected = detect_languages_and_tools(repo_root)
    analyzer_results = run_analyzers(repo_root, detected, run_semgrep)
    prompt = build_prompt(detected, compact_results(analyzer_results))
    llm_response = call_llm(provider=llm_provider, prompt=prompt)
    return llm_response, analyzer_results

def build_prompt(detected, analyzer_results):
    return f"""
You are a senior Staff Engineer, Security Architect, and DevOps reviewer.

MANDATORY OUTPUT FORMAT:

1) Repository Health Summary
2) Prioritized Actionable Items (Critical / High / Medium / Low)
3) Remediation Guidance (snippets, not full files)

Repository context:
Detected languages/tools:
{json.dumps(detected, indent=2)}

Analyzer findings (summarized):
{json.dumps(analyzer_results, indent=2)}
"""

# ---------- GenOps Guardian ----------

def run_genops_guardian(repo_root):
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    git_log = subprocess.getoutput(f"git -C {repo_root} log -n 5 --pretty=oneline")
    git_diff = subprocess.getoutput(f"git -C {repo_root} diff HEAD~5 HEAD")

    prompt = f"""
You are GenOps Guardian — an AI DevOps risk assessor.

Return STRICT JSON:
- risk_score (0-100)
- risk_level (Low/Medium/High)
- issues (list of strings)
- analysis_text (short)

Commits:
{git_log}

Diff:
{git_diff}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        temperature=0
    )

    try:
        return json.loads(response.output_text)
    except Exception:
        return {
            "risk_score": 50,
            "risk_level": "Medium",
            "issues": ["Unstructured LLM output"],
            "analysis_text": response.output_text
        }

# ---------- Entry Point ----------

def run_agent():
    repo_root = os.getenv("GITHUB_WORKSPACE", os.getcwd())
    llm_provider = os.getenv("INPUT_LLM_PROVIDER", "openai")
    run_semgrep = os.getenv("INPUT_RUN_SEMGREP", "true").lower() == "true"
    pr_number = os.getenv("PR_NUMBER")

    llm_response, analyzer_results = run_universal_agent(
        repo_root, llm_provider, run_semgrep
    )
    genops_data = run_genops_guardian(repo_root)

    # --- Always store artifacts ---
    os.makedirs("analysis_results", exist_ok=True)

    with open("analysis_results/analyzer_results.json", "w") as f:
        json.dump(analyzer_results, f, indent=2)

    with open("analysis_results/llm_report.md", "w") as f:
        f.write(llm_response.get("full", ""))

    with open("analysis_results/genops_guardian.json", "w") as f:
        json.dump(genops_data, f, indent=2)

    # --- Convert JSON → Markdown ---
    json_to_markdown(
        Path("analysis_results/analyzer_results.json"),
        Path("analysis_results/analyzer_results.md")
    )

    convert(
        Path("analysis_results/analyzer_results.json"),
        Path("analysis_results/analyzer_results_convert.md")
    )  
    

    # --- Short PR comment ---
    if pr_number:
        critical = genops_data.get("issues", [])[:5]
        comment = f"""
##  AI GenOps Review (Summary)

**Risk Score:** {genops_data['risk_score']} ({genops_data['risk_level']})

###  Top Issues
{chr(10).join(f"- {i}" for i in critical) if critical else "- None"}

 **Full analysis available as workflow artifacts**
--> Actions → AI & GenOps Guardian → Artifacts
"""
        post_comment(pr_number, comment)

if __name__ == "__main__":
    run_agent()
