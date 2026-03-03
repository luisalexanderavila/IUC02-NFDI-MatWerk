import argparse
import os
import subprocess
import sys


def run_command(command, cwd, env=None):
    print(f"==> Running: {' '.join(command)}")
    result = subprocess.run(command, cwd=cwd, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(command)}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Parsing tests and generate browser visualization with the current Python interpreter."
    )
    return parser.parse_args()


def main():
    parse_args()

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    requirements_file = os.path.join(root_dir, "requirements.txt")
    html_file = os.path.join(root_dir, "Notebooks", "rdf_graph_viewer.html")
    active_python = sys.executable

    print(f"==> Using Parsing root: {root_dir}")
    print(f"==> Active Python interpreter: {active_python}")

    run_command([active_python, "-m", "pip", "install", "--upgrade", "pip"], cwd=root_dir)
    run_command([active_python, "-m", "pip", "install", "-r", requirements_file], cwd=root_dir)

    run_command([active_python, "-m", "pytest", "test", "-q"], cwd=root_dir)
    run_command([active_python, os.path.join("bin", "create_visualization.py")], cwd=root_dir)

    if not os.path.isfile(html_file):
        raise FileNotFoundError(f"Visualization file was not generated: {html_file}")

    print(f"==> Visualization ready: {html_file}")
    print("==> All checks passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
