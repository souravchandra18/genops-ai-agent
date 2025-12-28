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

def extract_structured_findings(analyzer_results):
    """Extract and structure key findings instead of truncating"""
    findings = {
        'critical_issues': [],
        'security_issues': [],
        'quality_issues': [],
        'scope_summary': ''
    }
    
    tools_run = []
    total_issues = 0
    
    for tool, data in analyzer_results.items():
        if data.get('returncode') != 0:
            tools_run.append(f"{tool} (ISSUES FOUND)")
        else:
            tools_run.append(f"{tool} (CLEAN)")
            
        stdout = data.get('stdout', '')
        stderr = data.get('stderr', '')
        
        # Parse JSON outputs intelligently
        if stdout.strip():
            try:
                parsed = json.loads(stdout)
                issues = parse_tool_output(tool, parsed)
                
                for issue in issues:
                    if issue['severity'] in ['CRITICAL', 'HIGH', 'ERROR']:
                        findings['critical_issues'].append(f"{tool}: {issue['message']}")
                        
                    if issue['category'] in ['security', 'vulnerability', 'cve']:
                        findings['security_issues'].append(f"{tool}: {issue['message']}")
                        
                    if issue['category'] in ['quality', 'code_smell', 'maintainability']:
                        findings['quality_issues'].append(f"{tool}: {issue['message']}")
                        
                total_issues += len(issues)
                        
            except json.JSONDecodeError:
                # Handle text-based outputs
                if 'error' in stderr.lower() or 'warning' in stderr.lower():
                    findings['quality_issues'].append(f"{tool}: {stderr[:200]}...")
    
    findings['scope_summary'] = f"Analyzed with: {', '.join(tools_run)}. Total issues: {total_issues}"
    
    # Limit to top 10 per category to stay within token limits
    for category in ['critical_issues', 'security_issues', 'quality_issues']:
        findings[category] = findings[category][:10]
        
    return findings

def parse_tool_output(tool_name, data):
    """Parse specific tool outputs intelligently"""
    issues = []
    
    # Semgrep
    if tool_name == 'semgrep' and isinstance(data, dict):
        for result in data.get('results', []):
            issues.append({
                'severity': result.get('extra', {}).get('severity', 'MEDIUM'),
                'message': result.get('extra', {}).get('message', 'Security issue'),
                'category': 'security',
                'file': result.get('path', ''),
                'line': result.get('start', {}).get('line', 0)
            })
    
    # Bandit
    elif tool_name == 'bandit' and isinstance(data, dict):
        for result in data.get('results', []):
            issues.append({
                'severity': result.get('issue_severity', 'MEDIUM'),
                'message': result.get('issue_text', 'Security issue'),
                'category': 'security',
                'file': result.get('filename', ''),
                'line': result.get('line_number', 0)
            })
    
    # PMD (Java)
    elif tool_name == 'pmd' and isinstance(data, dict):
        for file_data in data.get('files', []):
            for violation in file_data.get('violations', []):
                priority = violation.get('priority', 3)
                severity = 'HIGH' if priority <= 2 else 'MEDIUM' if priority <= 3 else 'LOW'
                issues.append({
                    'severity': severity,
                    'message': violation.get('description', 'Code quality issue'),
                    'category': 'quality',
                    'file': file_data.get('filename', ''),
                    'line': violation.get('beginline', 0)
                })
    
    # Generic handler for other tools
    else:
        if isinstance(data, list):
            for item in data[:20]:  # Limit to first 20 items
                issues.append({
                    'severity': 'MEDIUM',
                    'message': str(item)[:100],
                    'category': 'quality',
                    'file': '',
                    'line': 0
                })
    
    return issues

def get_repository_stats(repo_root):
    """Gather repository statistics for better context"""
    stats = {}
    
    try:
        # Count files and estimate LOC
        import os
        total_files = 0
        total_lines = 0
        file_types = {}
        
        for root, dirs, files in os.walk(repo_root):
            # Skip common ignore directories
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', '.venv', 'target', 'build'}]
            
            for file in files:
                if not file.startswith('.'):
                    total_files += 1
                    ext = os.path.splitext(file)[1]
                    file_types[ext] = file_types.get(ext, 0) + 1
                    
                    # Estimate LOC for text files
                    try:
                        file_path = os.path.join(root, file)
                        if ext in {'.py', '.java', '.js', '.ts', '.go', '.rb', '.php', '.cs'}:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                total_lines += len(f.readlines())
                    except:
                        pass
        
        stats['total_files'] = total_files
        stats['lines_of_code'] = total_lines
        stats['file_types'] = file_types
        
        # Get git info
        git_info = subprocess.getoutput(f"git -C {repo_root} log --oneline | wc -l")
        stats['commits'] = git_info.strip() if git_info.isdigit() else 'Unknown'
        
    except Exception:
        stats = {'total_files': 'Unknown', 'lines_of_code': 'Unknown', 'commits': 'Unknown'}
    
    return stats

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
    repo_stats = get_repository_stats(repo_root)
    prompt = build_prompt(detected, analyzer_results, repo_stats)
    llm_response = call_llm(provider=llm_provider, prompt=prompt)
    return llm_response, analyzer_results

def build_prompt(detected, analyzer_results, repo_stats=None):
    # Extract structured findings
    findings_summary = extract_structured_findings(analyzer_results)
    
    return f"""
You are a Principal Software Engineer, Security Architect, and DevOps Lead with 15+ years experience.

CONTEXT:
- Repository: {repo_stats.get('total_files', 'Unknown')} files, {repo_stats.get('lines_of_code', 'Unknown')} LOC
- Languages: {', '.join(detected.get('languages', []))}
- Infrastructure: {', '.join(detected.get('tools', []))}

ANALYSIS SCOPE:
{findings_summary['scope_summary']}

CRITICAL FINDINGS:
{findings_summary['critical_issues']}

SECURITY CONCERNS:
{findings_summary['security_issues']}

CODE QUALITY ISSUES:
{findings_summary['quality_issues']}

MANDATORY JSON OUTPUT FORMAT:
{{
  "overall_health_score": 0-100,
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "executive_summary": "2-3 sentence overview",
  "critical_actions": [
    {{"priority": 1, "category": "Security|Quality|Performance", "issue": "description", "impact": "business impact", "effort": "Low|Medium|High", "remediation": "specific steps"}}
  ],
  "recommendations": [
    {{"category": "Security|Quality|DevOps", "recommendation": "actionable advice", "rationale": "why this matters"}}
  ],
  "technical_debt": {{
    "score": 0-100,
    "hotspots": ["file1.py", "file2.java"],
    "patterns": ["Anti-pattern descriptions"]
  }},
  "security_posture": {{
    "score": 0-100,
    "vulnerabilities": {{"high": 0, "medium": 0, "low": 0}},
    "compliance_gaps": ["specific gaps"]
  }}
}}

RAW ANALYZER DATA:
{json.dumps(analyzer_results, indent=2)}
"""

def generate_enhanced_markdown(structured_data):
    """Generate enhanced markdown from structured LLM response"""
    if not structured_data:
        return "# Analysis Report\n\nNo structured data available."
    
    md = f"""# 🔍 AI & GenOps Analysis Report

## 📊 Overall Assessment
- **Health Score:** {structured_data.get('overall_health_score', 'N/A')}/100
- **Risk Level:** {structured_data.get('risk_level', 'UNKNOWN')}

## 📋 Executive Summary
{structured_data.get('executive_summary', 'No summary available.')}

## 🚨 Critical Actions Required
"""
    
    for action in structured_data.get('critical_actions', []):
        md += f"""
### Priority {action.get('priority', 'N/A')} - {action.get('category', 'General')}
**Issue:** {action.get('issue', 'No description')}  
**Impact:** {action.get('impact', 'Unknown impact')}  
**Effort:** {action.get('effort', 'Unknown effort')}  
**Remediation:** {action.get('remediation', 'No remediation steps provided')}
"""

    md += "\n## 💡 Recommendations\n"
    for rec in structured_data.get('recommendations', []):
        md += f"""
### {rec.get('category', 'General')}
**Recommendation:** {rec.get('recommendation', 'No recommendation')}  
**Rationale:** {rec.get('rationale', 'No rationale provided')}
"""

    # Technical Debt Section
    tech_debt = structured_data.get('technical_debt', {})
    if tech_debt:
        md += f"""
## 🏗️ Technical Debt Analysis
**Score:** {tech_debt.get('score', 'N/A')}/100

### Hotspots
"""
        for hotspot in tech_debt.get('hotspots', []):
            md += f"- `{hotspot}`\n"
            
        md += "\n### Patterns Identified\n"
        for pattern in tech_debt.get('patterns', []):
            md += f"- {pattern}\n"

    # Security Section
    security = structured_data.get('security_posture', {})
    if security:
        md += f"""
## 🔒 Security Posture
**Score:** {security.get('score', 'N/A')}/100

### Vulnerability Breakdown
"""
        vuln = security.get('vulnerabilities', {})
        md += f"- **High:** {vuln.get('high', 0)}\n"
        md += f"- **Medium:** {vuln.get('medium', 0)}\n" 
        md += f"- **Low:** {vuln.get('low', 0)}\n"
        
        md += "\n### Compliance Gaps\n"
        for gap in security.get('compliance_gaps', []):
            md += f"- {gap}\n"

    return md

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
        model="gpt-4o-mini",
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

    # Store structured LLM response
    if llm_response.get('structured'):
        with open("analysis_results/structured_report.json", "w") as f:
            json.dump(llm_response['structured'], f, indent=2)
            
        # Generate enhanced markdown report
        with open("analysis_results/enhanced_report.md", "w") as f:
            f.write(generate_enhanced_markdown(llm_response['structured']))

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


    print("📂 Files inside analysis_results:")
    for f in Path("analysis_results").glob("*"):
        print(" -", f.name)
    

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
