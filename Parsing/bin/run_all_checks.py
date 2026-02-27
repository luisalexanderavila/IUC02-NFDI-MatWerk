import argparse
import os
import subprocess
import sys


def run_command(command, cwd):
    print(f"==> Running: {' '.join(command)}")
    result = subprocess.run(command, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(command)}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Parsing tests and generate browser visualization (cross-platform)."
    )
    parser.add_argument(
        "env_name",
        nargs="?",
        default="IUC02_Demonstator",
        help="micromamba environment name (default: IUC02_Demonstator)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    html_file = os.path.join(root_dir, "Notebooks", "rdf_graph_viewer.html")

    print(f"==> Using Parsing root: {root_dir}")
    print(f"==> Using micromamba env: {args.env_name}")

    run_command(
        ["micromamba", "run", "-n", args.env_name, "pytest", "test", "-q"],
        cwd=root_dir,
    )

    run_command(
        ["micromamba", "run", "-n", args.env_name, "python", os.path.join("bin", "create_visualization.py")],
        cwd=root_dir,
    )

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
