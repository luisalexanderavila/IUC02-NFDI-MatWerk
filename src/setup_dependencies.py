def setup_sparse_checkout(repo_path, repo_url, branch, subfolder):
    """Set up a sparse-checkout repository."""
    if not os.path.exists(repo_path):
        print(f"Cloning repository (sparse-checkout) into {repo_path}...")
        # Clone the repository without checking out files
        run_command(["git", "clone", "--no-checkout", "--depth", "1", "--branch", branch, repo_url, repo_path])

    # Set up sparse checkout
    print(f"Configuring sparse checkout for branch '{branch}' and subfolder '{subfolder}'...")
    run_command(["git", "sparse-checkout", "init", "--cone"], cwd=repo_path)
    run_command(["git", "sparse-checkout", "set", subfolder], cwd=repo_path)
    run_command(["git", "checkout"], cwd=repo_path)


def setup_worktrees(config_file):
    """Set up Git worktrees and sparse checkouts based on a YAML configuration."""
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    for dep_name, dep_data in config.get('dependencies', {}).items():
        repo_path = dep_data['repo']
        remotes = dep_data.get('remotes', {})
        sparse_checkout = dep_data.get('sparse_checkout', {})
        worktrees = dep_data.get('worktrees', [])

        # Sparse Checkout
        if sparse_checkout:
            branch = sparse_checkout['branch']
            subfolder = sparse_checkout['subfolder']
            origin_url = remotes.get('origin')
            if not origin_url:
                print(f"Error: No 'origin' remote provided for {dep_name}.")
                continue
            setup_sparse_checkout(repo_path, origin_url, branch, subfolder)
            continue  # Skip worktree setup for sparse checkouts

        # Clone repository if it doesn't exist
        if not os.path.exists(repo_path):
            print(f"Cloning repository for {dep_name}...")
            if "origin" not in remotes:
                print(f"Error: No 'origin' remote provided for {dep_name}.")
                continue
            run_command(["git", "clone", remotes['origin'], repo_path])

        # Set up remotes
        setup_remotes(repo_path, remotes)

        # Add worktrees
        for worktree in worktrees:
            worktree_path = worktree['path']
            branch = worktree['branch']
            description = worktree.get('description', "No description provided.")

            if os.path.exists(worktree_path):
                print(f"Worktree already exists: {worktree_path} ({branch})")
                continue

            print(f"Adding worktree for branch '{branch}': {worktree_path}")
            run_command(["git", "worktree", "add", worktree_path, branch], cwd=repo_path)

