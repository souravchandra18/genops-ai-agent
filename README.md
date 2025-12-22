# genops-ai-agent

#  Unified AI & GenOps Guardian CI

This repository includes a **GitHub Actions workflow** that runs two AI-powered reviewers on every Pull Request or manual workflow run:

---

##  AI Universal Agent
- Detects languages and tools in the repository
- Runs static analyzers:
  - Python → `ruff`, `pylint`, `bandit`
  - JavaScript → `eslint`
  - Java → `spotbugs`, `pmd`, `checkstyle`
  - Go → `govet`, `staticcheck`
  - Ruby → `rubocop`
  - PHP → `phpcs`, `psalm`
  - .NET → `roslyn`
  - Docker → `trivy`
  - Terraform → `checkov`, `tfsec`
  - Kubernetes → `kube-linter`
  - Semgrep (multi-language)
- Summarizes findings with an LLM (OpenAI)
- Posts a PR comment with both a short summary and a detailed report

---

##  GenOps Guardian
- Collects repository or PR context (configs, diffs, commits)
- Uses OpenAI to calculate a **risk score (0–100)**
- Flags potential pipeline failures, security issues, and optimization opportunities
- Posts a PR comment with risk level and analysis

---

##  Workflow Modes

### Pull Request Mode
- Triggered automatically on PR events (`opened`, `synchronize`, `reopened`)
- Posts **two comments** directly on the PR:
  - Repository Health Summary + Detailed Report
  - Risk Score + Issues + Analysis

### Real Mode
- Triggered manually via `workflow_dispatch`
- Runs both agents but **no PR comments are posted**
- Instead, results are written to `analysis_results/`:
  - `universal_agent.txt` → full summary + detailed analyzer report
  - `genops_guardian.json` → structured risk analysis JSON
- These files are uploaded as a **workflow artifact** named `analysis-results`  
  → Downloadable from the **Actions run summary** in GitHub

---

##  Secrets Required
- `OPENAI_API_KEY` → for AI Universal Agent & for GenOps Guardian
- `GITHUB_TOKEN` → automatically provided by GitHub Actions

---

##  Repository Structure

.github/ workflows/ ai-genops.yml        # Unified workflow
ai-agent/ agent.py               # Unified entrypoint (runs both agents) analyzers.py           # Language/tool detection + analyzers llm.py                 # LLM call wrapper requirements.txt       
ai-agent/ requirements.txt       # Dependencies for AI Agent & GenOps Guardian (aligned)


---

##  Contributor Experience
Every PR will receive **two complementary AI reviews**:
- **Code Quality & Security Analysis** (Universal Agent)
- **Risk Scoring & CI/CD Health Check** (GenOps Guardian)

This ensures contributors get actionable feedback on both **code-level issues** and **pipeline-level risks**.

---

##  Downloading Reports in Real Mode
1. Go to the **Actions tab** in GitHub.
2. Select the workflow run.
3. Scroll to the **Artifacts** section.
4. Download the `analysis-results` archive.
5. Inside you’ll find:
   - `universal_agent.txt`
   - `genops_guardian.json`

---

##  Going to execute
- Ensure secrets are configured in your repository:
  - `OPENAI_API_KEY`
- Open a Pull Request → AI reviews will appear as comments.
- Or trigger manually via **Actions → Run workflow** → choose `real` mode → download artifact for full report.

