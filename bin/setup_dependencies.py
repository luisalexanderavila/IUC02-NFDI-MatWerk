import os
import sys
import shutil
import subprocess
import yaml
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import subprocess
import yaml
import logging

import pdb

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

def setup_sparse_checkout(repo_path, old_url, sparse_checkout):
    """Set up a sparse checkout repository."""
    branch = sparse_checkout['branch']
    subfolder = sparse_checkout['path']

    logger.info(f"Performing sparse checkout from 'old_remote': {old_url}")
    run_command(["git", "clone", "--no-checkout", "--depth", "1", "--branch", branch, old_url, repo_path])
    run_command(["git", "remote", "rename", "origin", "old_remote"], cwd=repo_path)
    run_command(["git", "sparse-checkout", "init", "--cone"], cwd=repo_path)
    run_command(["git", "sparse-checkout", "set", subfolder], cwd=repo_path)
    run_command(["git", "checkout"], cwd=repo_path)

def setup_worktrees(repo_path, worktrees):
    """Set up multiple worktrees for a repository."""
    for worktree_name, worktree in worktrees.items():
        logging.info(f"Setting up worktree: {worktree}")
        if 'path' not in worktree or 'branch' not in worktree:
            logger.error(f"Worktree configuration is missing 'path' or 'branch'. Skipping.")
            continue
        worktree_path = worktree['path']
        branch = worktree['branch']
        description = worktree[ 'description' ]
        if os.path.exists(worktree_path):
            logger.info(f"Worktree already exists: {worktree_path} ({branch})")
            continue
        logger.info(f"Adding worktree for branch '{branch}': {worktree_path} - {description}")
        try:
            run_command(["git", "-C", repo_path,  "worktree", "add", worktree_path, branch])
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create worktree: {worktree_path} ({branch})")
            logger.error(e)

def setup_repository(dep_name, dep_data):
    """Set up the repository, including remotes, sparse checkout, and worktrees."""

    logger.info(f' right now at {os.getcwd()}')

    repo_path = dep_data['target_dir']
    remotes = dep_data.get('remotes', {})
    worktrees = dep_data.get('worktrees', {})


    if 'origin' not in remotes.keys():
        logger.error(f'at least one origin repository must be given for dependency {dep_name}')
        sys.exit(0)

    origin = remotes.pop('origin')

    logger.info(f'cloning repository: {origin['url']} to {repo_path}')
    if os.path.exists(repo_path):
        logger.info(f"Repository already exists at {repo_path}. Skipping clone.")
    else:
        logger.info(f"Repository not cloned yet {repo_path}. cloning.")
        run_command(["git", "clone", origin['url'], repo_path])
        logger.info(f'status: /n {os.listdir(repo_path)}')

    present_remotes = run_command(["git", "-C", repo_path, "remote", "show"]).split('\n')
    logger.info(f"remotes: {present_remotes}")

    for remote_name, remote_data in remotes.items():
        if remote_name not in present_remotes:
            logger.info(f"Adding {remote_name} remote: {remote_data['url']}")
            run_command(["git","-C", repo_path,  "remote", "add", remote_name, remote_data['url']])
        logger.info(f"fetching remote: {remote_name}")
        run_command(["git", "-C", repo_path, "fetch", remote_name])

    if worktrees:
        setup_worktrees(repo_path, worktrees)

def setup_dependencies(config_file):
    """Set up all dependencies based on a YAML configuration."""
    if not os.path.exists(config_file):
        logger.error(f"Configuration file not found: {config_file}")
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    for dep_name, dep_data in config.get('dependencies', {}).items():
        logger.info(f"Setting up dependency: {dep_name}")
        try:
            setup_repository(dep_name, dep_data)
        except Exception as e:
            logger.exception(f"Failed to set up dependency {dep_name}.")

if __name__ == "__main__":
    CONFIG_FILE = "config/dependencies_config.yaml"
    try:
        setup_dependencies(CONFIG_FILE)
    except Exception as e:
        logger.exception("An error occurred during setup.")

