import os, json, subprocess
from analyzers import detect_languages_and_tools, run_analyzers
from llm import call_llm
from github import Github, Auth
from openai import OpenAI

def run_universal_agent(repo_root, llm_provider, run_semgrep):
    detected = detect_languages_and_tools(repo_root)
    analyzer_results = run_analyzers(repo_root, detected, run_semgrep)
    prompt = build_prompt(detected, analyzer_results)
    return call_llm(provider=llm_provider, prompt=prompt), analyzer_results

def build_prompt(detected, analyzer_results):
    return (
        "You are an expert engineering reviewer. Produce:\n"
        "1) A short summary of the repo health.\n"
        "2) A prioritized list of all actionable items.\n"
        "3) Line-level complete suggestions if available.\n"
        f"Repository analysis data:\n{json.dumps(analyzer_results, indent=2)}"
    )

def run_genops_guardian(repo_root, mode):
    api_key = os.getenv("OPENAI_API_KEY")

    client = OpenAI(api_key=api_key)

    if mode == "demo":
        context = "This is a simulated CI/CD pipeline log."
    else:
        git_log = subprocess.getoutput(f"git -C {repo_root} log -n 5 --pretty=oneline")
        git_diff = subprocess.getoutput(f"git -C {repo_root} diff HEAD~5 HEAD")
        context = f"### Commits\n{git_log}\n\n### Diff\n{git_diff}"

    prompt = f"""
    You are GenOps Guardian — an AI DevOps assistant.
    Analyze the following data and output JSON with:
    - risk_score (0-100)
    - risk_level (Low/Medium/High)
    - issues (list)
    - analysis_text (short explanation)
    ---
    {context}
    """

    response = client.responses.create(model="gpt-4.1-mini", input=prompt, temperature=0)
    try:
        return json.loads(response.output_text.strip())
    except Exception:
        return {"risk_score": 50, "risk_level": "Medium", "issues": ["Unstructured output"], "analysis_text": response.output_text}

def post_comment(pr_number, body):
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPOSITORY")

    gh = Github(auth=Auth.Token(token))
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))
    pr.create_issue_comment(body)

def run_agent():
    repo_root = os.getenv("GITHUB_WORKSPACE", os.getcwd())
    llm_provider = os.getenv("INPUT_LLM_PROVIDER", "openai")
    run_semgrep = os.getenv("INPUT_RUN_SEMGREP", "true").lower() == "true"
    mode = "pr" if os.getenv("GITHUB_EVENT_NAME") == "pull_request" else "real"
    pr_number = os.getenv("PR_NUMBER")

    # Universal Agent
    llm_response, analyzer_results = run_universal_agent(repo_root, llm_provider, run_semgrep)
    ua_comment = (
        f"### Repository Health Summary\n{llm_response.get('summary','')}\n\n---\n\n"
        f"### Detailed Report\n{llm_response.get('full', json.dumps(analyzer_results, indent=2))}"
    )

    # GenOps Guardian
    genops_data = run_genops_guardian(repo_root, mode)
    guardian_comment = (
        f"**Risk Score:** {genops_data['risk_score']} ({genops_data['risk_level']})\n\n"
        f"**Detected Issues:**\n" + "\n".join(f"- {i}" for i in genops_data.get("issues", [])) +
        f"\n\n**AI Analysis:**\n{genops_data.get('analysis_text','')}"
    )

    if pr_number:
        # Post comments in PR mode
        post_comment(pr_number, ua_comment)
        post_comment(pr_number, guardian_comment)
    else:
        # Save reports in real mode
        os.makedirs("analysis_results", exist_ok=True)
        with open("analysis_results/universal_agent.txt", "w", encoding="utf-8") as f:
            f.write(ua_comment)
        with open("analysis_results/genops_guardian.json", "w", encoding="utf-8") as f:
            json.dump(genops_data, f, indent=2)
        print(" Reports written to analysis_results/ for inspection.")

if __name__ == "__main__":
    run_agent()
