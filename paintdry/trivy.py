import subprocess
import os


def trivy_scan(repo_path, branch_path):
    """Generate a CycloneDX SBOM for branch_path, saved as <repo_path>/trivy.json"""
    output = os.path.join(repo_path, "trivy.json")
    tmp = output + ".tmp"
    try:
        result = subprocess.run(
            ["trivy", "fs", "--quiet", "--format", "cyclonedx",
             "--output", tmp, branch_path]
        )
    except FileNotFoundError:
        print("Warning: trivy not found - skipping SBOM generation")
        return
    if result.returncode == 0:
        os.rename(tmp, output)
        return

    print(f"Trivy scan failed for {repo_path}")
    try:
        os.remove(tmp)
    except FileNotFoundError:
        pass
