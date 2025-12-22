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

    # Python
    if 'python' in detected['languages']:
        results['python'] = run_command(['ruff', '.'], repo_root) or run_command(['pylint', '-f', 'json', '.'], repo_root)
        results['bandit'] = run_command(['bandit', '-r', '.', '-f', 'json'], repo_root)

    # JavaScript
    if 'javascript' in detected['languages']:
        results['javascript'] = run_command(['npx', 'eslint', '.', '-f', 'json'], repo_root)

    # Java
    if 'java' in detected['languages']:
        results['spotbugs'] = run_command(['spotbugs', '-textui', '-xml', 'target/classes'], repo_root)
        results['pmd'] = run_command(['pmd', '-d', 'src', '-R', 'rulesets/java/quickstart.xml', '-f', 'xml'], repo_root)
        results['checkstyle'] = run_command(['checkstyle', '-c', '/google_checks.xml', 'src'], repo_root)

    # Go
    if 'go' in detected['languages']:
        results['govet'] = run_command(['go', 'vet', './...'], repo_root)
        results['staticcheck'] = run_command(['staticcheck', './...'], repo_root)

    # Ruby
    if 'ruby' in detected['languages']:
        results['rubocop'] = run_command(['rubocop', '-f', 'json'], repo_root)

    # PHP
    if 'php' in detected['languages']:
        results['phpcs'] = run_command(['phpcs', '--report=json'], repo_root)
        results['psalm'] = run_command(['psalm', '--output-format=json'], repo_root)

    # .NET / C#
    if 'dotnet' in detected['languages']:
        results['roslyn'] = run_command(['dotnet', 'build', '/warnaserror'], repo_root)

    # Docker
    if 'dockerfile' in detected['tools']:
        results['trivy'] = run_command(['trivy', 'config', '--format', 'json', repo_root], repo_root)

    # Terraform
    if 'terraform' in detected['tools']:
        results['checkov'] = run_command(['checkov', '-d', repo_root, '-o', 'json'], repo_root)
        results['tfsec'] = run_command(['tfsec', '--format', 'json', repo_root], repo_root)

    # Kubernetes YAML
    if 'k8s' in detected['tools']:
        results['kube-linter'] = run_command(['kube-linter', 'lint', repo_root, '--output', 'json'], repo_root)

    # Semgrep (all languages)
    if run_semgrep:
        results['semgrep'] = run_command(['semgrep', '--config', 'auto', '--json', '--quiet'], repo_root)

    return results

def run_command(cmd, cwd):
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        return {'stdout': result.stdout, 'stderr': result.stderr, 'returncode': result.returncode}
    except Exception as e:
        return {'error': str(e)}
