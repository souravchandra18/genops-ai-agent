import os
import subprocess

def detect_languages_and_tools(repo_root):
    detected = {'languages': [], 'tools': []}
    files = os.listdir(repo_root)

    # Python
    if os.path.exists(os.path.join(repo_root, 'requirements.txt')) or os.path.exists(os.path.join(repo_root, 'pyproject.toml')):
        detected['languages'].append('python')

    # JavaScript / Node
    if os.path.exists(os.path.join(repo_root, 'package.json')):
        detected['languages'].append('javascript')
        detected['tools'].append('npm')

    # Java
    if os.path.exists(os.path.join(repo_root, 'pom.xml')) or os.path.exists(os.path.join(repo_root, 'build.gradle')):
        detected['languages'].append('java')

    # Go
    if os.path.exists(os.path.join(repo_root, 'go.mod')):
        detected['languages'].append('go')

    # Ruby
    if os.path.exists(os.path.join(repo_root, 'Gemfile')):
        detected['languages'].append('ruby')

    # PHP
    if os.path.exists(os.path.join(repo_root, 'composer.json')):
        detected['languages'].append('php')

    # .NET / C#
    if any(f.endswith('.csproj') for f in files):
        detected['languages'].append('dotnet')

    # Docker
    if os.path.exists(os.path.join(repo_root, 'Dockerfile')):
        detected['tools'].append('dockerfile')

    # Terraform / Kubernetes
    if any(f.endswith('.tf') for f in files):
        detected['tools'].append('terraform')

    if any(f.endswith(('.yaml', '.yml')) for f in files):
        detected['tools'].append('k8s')

    return detected

def run_analyzers(repo_root, detected, run_semgrep):
    results = {}

    def wrap(tool, language, has_lines, cmd):
        return {
            "tool": tool,
            "language": language,
            "has_line_numbers": has_lines,
            "result": run_command(cmd, repo_root)
        }

    # Python
    if 'python' in detected['languages']:
        results['ruff'] = wrap("Ruff", "Python", True, ['ruff', '.'])
        results['bandit'] = wrap("Bandit", "Python", True, ['bandit', '-r', '.', '-f', 'json'])

    # JavaScript
    if 'javascript' in detected['languages']:
        results['eslint'] = wrap("ESLint", "JavaScript", True, ['npx', 'eslint', '.', '-f', 'json'])

    # Java
    if 'java' in detected['languages']:
        results['spotbugs'] = wrap("SpotBugs", "Java", False, ['spotbugs', '-textui', '-xml', 'target/classes'])
        results['pmd'] = wrap("PMD", "Java", True, ['pmd', 'check', '-d', 'src', '-R', 'rulesets/java/quickstart.xml', '-f', 'json'])
        results['checkstyle'] = wrap("Checkstyle", "Java", True, ['java', '-jar', '/opt/checkstyle/checkstyle.jar', '-c', '/opt/checkstyle/google_checks.xml', 'src'])

    # Go
    if 'go' in detected['languages']:
        results['govet'] = wrap("GoVet", "Go", False, ['go', 'vet', './...'])
        results['staticcheck'] = wrap("StaticCheck", "Go", True, ['staticcheck', './...'])

    # Ruby
    if 'ruby' in detected['languages']:
        results['rubocop'] = wrap("RuboCop", "Ruby", True, ['rubocop', '-f', 'json'])

    # PHP
    if 'php' in detected['languages']:
        results['phpcs'] = wrap("PHPCS", "PHP", True, ['phpcs', '--report=json'])
        results['psalm'] = wrap("Psalm", "PHP", True, ['psalm', '--output-format=json'])

    # .NET / C#
    if 'dotnet' in detected['languages']:
        results['roslyn'] = wrap("Roslyn", ".NET", False, ['dotnet', 'build', '/warnaserror'])

    # Dockerfile
    if 'dockerfile' in detected['tools']:
        results['trivy'] = wrap("Trivy", "Container/IaC", False, ['trivy', 'config', '--format', 'json', repo_root])

    # Terraform
    if 'terraform' in detected['tools']:
        results['checkov'] = wrap("Checkov", "Terraform", False, ['checkov', '-d', repo_root, '-o', 'json'])
        results['tfsec'] = wrap("tfsec", "Terraform", False, ['tfsec', '--format', 'json', repo_root])

    # Kubernetes YAML
    if 'k8s' in detected['tools']:
        results['kube-linter'] = wrap("kube-linter", "Kubernetes", False, ['kube-linter', 'lint', repo_root, '--output', 'json'])

    # Semgrep (All languages)
    if run_semgrep:
        results['semgrep'] = wrap("Semgrep", "Multi", True, ['semgrep', '--config', 'auto', '--json', '--quiet'])

    return results

def run_command(cmd, cwd):
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        return {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except Exception as e:
        return {'error': str(e)}
