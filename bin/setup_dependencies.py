import os
import subprocess
import yaml
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, cwd=None):
    """Run a shell command and log its output."""
    try:
        result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            logger.error(f"Command failed: {' '.join(command)}\n{result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, command, result.stderr)
        logger.debug(f"Command succeeded: {' '.join(command)}\n{result.stdout}")
        return result.stdout.strip()
    except Exception as e:
        logger.exception(f"Error running command: {' '.join(command)}")
        raise e

def setup_repository(repo_path, remotes, sparse_checkout):
    """Set up the repository, either by cloning origin or performing sparse checkout."""
    origin_url = remotes.get("origin")
    old_url = remotes.get("old_dependency")

    if not origin_url:
        logger.error("Error: 'origin' remote is required in the YAML configuration.")
        raise ValueError("'origin' remote is required.")

    # Case 1: Clone from origin if it exists
    if os.path.exists(repo_path):
        logger.info(f"Repository already exists at {repo_path}. Skipping clone.")
    elif origin_url:
        logger.info(f"Cloning repository from 'origin': {origin_url}...")
        run_command(["git", "clone", origin_url, repo_path])

        # Add the old dependency remote
        if old_url:
            logger.info(f"Adding 'old_dependency' remote: {old_url}")
            run_command(["git", "remote", "add", "old_dependency", old_url], cwd=repo_path)
            run_command(["git", "fetch", "old_dependency"], cwd=repo_path)

    # Case 2: Sparse checkout from old_dependency if origin doesn't exist locally
    elif old_url and sparse_checkout:
        branch = sparse_checkout['branch']
        if 'subfolder in sparse_checkout':
            subfolder = sparse_checkout['subfolder']
        else:
            subfolder = './'

        logger.info(f"Performing sparse checkout from 'old_dependency': {old_url}")
        run_command(["git", "clone", "--no-checkout", "--depth", "1", "--branch", branch, old_url, repo_path])
        run_command(["git", "remote", "rename", "origin", "old_dependency"], cwd=repo_path)
        run_command(["git", "sparse-checkout", "init", "--cone"], cwd=repo_path)
        run_command(["git", "sparse-checkout", "set", subfolder], cwd=repo_path)
        run_command(["git", "checkout"], cwd=repo_path)

        # Ensure origin is added after sparse checkout
        logger.info(f"Adding 'origin' remote: {origin_url}")
        run_command(["git", "remote", "add", "origin", origin_url], cwd=repo_path)

    else:
        logger.error("Error: Both 'origin' and 'old_dependency' remotes are missing in the YAML.")
        raise ValueError("Both 'origin' and 'old_dependency' remotes are required.")

    logger.info(f"Repository setup completed for {repo_path}.")

def setup_worktrees(config_file):
    """Set up Git repositories, remotes, and sparse checkouts based on a YAML configuration."""
    if not os.path.exists(config_file):
        logger.error(f"Configuration file not found: {config_file}")
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    for dep_name, dep_data in config.get('dependencies', {}).items():
        logger.info(f"Setting up dependency: {dep_name}")
        repo_path = dep_data['repository']
        remotes = dep_data.get('remotes', {})
        sparse_checkout = dep_data.get('sparse_checkout', {})

        # Set up the repository with sparse checkout or cloning origin
        setup_repository(repo_path, remotes, sparse_checkout)

if __name__ == "__main__":
    CONFIG_FILE = "dependency_config.yaml"
    try:
        setup_worktrees(CONFIG_FILE)
    except Exception as e:
        logger.exception("An error occurred during setup.")

