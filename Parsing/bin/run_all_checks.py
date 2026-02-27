import argparse
import os
import shutil
import subprocess
import sys


def run_command(command, cwd, env=None):
    print(f"==> Running: {' '.join(command)}")
    result = subprocess.run(command, cwd=cwd, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(command)}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Parsing tests and generate browser visualization using a local pyenv-backed venv."
    )
    parser.add_argument(
        "--python-version",
        default="3.11.0",
        help="Python version managed by pyenv (default: 3.11.0)",
    )
    parser.add_argument(
        "--venv-dir",
        default=".venv",
        help="Local virtual environment directory under Parsing root (default: .venv)",
    )
    return parser.parse_args()


def get_venv_python(venv_dir):
    if os.name == "nt":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def ensure_local_venv(root_dir, python_version, venv_dir_name):
    venv_dir = os.path.abspath(os.path.join(root_dir, venv_dir_name))
    venv_python = get_venv_python(venv_dir)

    if os.path.isfile(venv_python):
        print(f"==> Reusing existing virtual environment: {venv_dir}")
        return venv_dir, venv_python

    if shutil.which("pyenv") is None:
        raise RuntimeError(
            "pyenv is not available in PATH and no local virtual environment was found. "
            "Install pyenv, then rerun."
        )

    pyenv_env = os.environ.copy()
    pyenv_env["PYENV_VERSION"] = python_version

    print(f"==> Ensuring pyenv Python version is installed: {python_version}")
    run_command(["pyenv", "install", "-s", python_version], cwd=root_dir)

    print(f"==> Creating local virtual environment at: {venv_dir}")
    run_command(["pyenv", "exec", "python", "-m", "venv", venv_dir], cwd=root_dir, env=pyenv_env)

    return venv_dir, venv_python


def main():
    args = parse_args()

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    requirements_file = os.path.join(root_dir, "requirements.txt")
    html_file = os.path.join(root_dir, "Notebooks", "rdf_graph_viewer.html")

    print(f"==> Using Parsing root: {root_dir}")
    print(f"==> Requested pyenv Python version: {args.python_version}")

    _, venv_python = ensure_local_venv(root_dir, args.python_version, args.venv_dir)

    run_command([venv_python, "-m", "pip", "install", "--upgrade", "pip"], cwd=root_dir)
    run_command([venv_python, "-m", "pip", "install", "-r", requirements_file], cwd=root_dir)

    run_command([venv_python, "-m", "pytest", "test", "-q"], cwd=root_dir)
    run_command([venv_python, os.path.join("bin", "create_visualization.py")], cwd=root_dir)

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
