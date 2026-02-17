#!/usr/bin/env python3
"""
IUC02 Demonstrator App Launcher
Cross-platform script to set up and run the Streamlit application on Windows or Linux.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
import venv


def get_os_type():
    """Detect operating system."""
    return platform.system().lower()


def get_venv_path():
    """Get the virtual environment path."""
    return Path(__file__).parent / "venv"


def get_python_executable():
    """Get the Python executable in the virtual environment."""
    venv_path = get_venv_path()
    os_type = get_os_type()
    
    if os_type == "windows":
        return venv_path / "Scripts" / "python.exe"
    else:  # linux, darwin
        return venv_path / "bin" / "python"


def create_venv():
    """Create a virtual environment if it doesn't exist."""
    venv_path = get_venv_path()
    
    if venv_path.exists():
        print(f"✓ Virtual environment already exists at: {venv_path}")
        return True
    
    print(f"Creating virtual environment at: {venv_path}")
    try:
        venv.create(str(venv_path), with_pip=True)
        print("✓ Virtual environment created successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to create virtual environment: {e}")
        return False


def upgrade_pip():
    """Upgrade pip to the latest version."""
    python_exe = get_python_executable()
    
    print("\nUpgrading pip...")
    try:
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✓ pip upgraded successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to upgrade pip: {e.stderr}")
        return False


def install_requirements():
    """Install required packages from requirements.txt."""
    python_exe = get_python_executable()
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"✗ requirements.txt not found at: {requirements_file}")
        return False
    
    print(f"\nInstalling requirements from: {requirements_file}")
    try:
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "-r", str(requirements_file)],
            check=True,
            cwd=str(Path(__file__).parent)
        )
        print("✓ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install requirements: {e}")
        return False


def run_streamlit_app():
    """Launch the Streamlit application."""
    python_exe = get_python_executable()
    app_file = Path(__file__).parent / "IUC02_Demonstrator.py"
    
    if not app_file.exists():
        print(f"✗ IUC02_Demonstrator.py not found at: {app_file}")
        return False
    
    print(f"\n{'='*60}")
    print("Starting IUC02 Demonstrator App...")
    print(f"{'='*60}")
    print("\nStreamlit app is running!")
    print("Open your browser and navigate to: http://localhost:8501")
    print("\nTo stop the app, press Ctrl+C in this terminal.")
    print(f"{'='*60}\n")
    
    try:
        subprocess.run(
            [str(python_exe), "-m", "streamlit", "run", str(app_file)],
            cwd=str(Path(__file__).parent)
        )
        return True
    except KeyboardInterrupt:
        print("\n\nApp stopped by user.")
        return True
    except Exception as e:
        print(f"✗ Failed to run Streamlit app: {e}")
        return False


def main():
    """Main function to orchestrate setup and launch."""
    print(f"IUC02 Demonstrator App Launcher")
    print(f"Operating System: {platform.system()}")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"{'='*60}\n")
    
    # Step 1: Create virtual environment
    if not create_venv():
        sys.exit(1)
    
    # Step 2: Upgrade pip
    if not upgrade_pip():
        sys.exit(1)
    
    # Step 3: Install requirements
    if not install_requirements():
        sys.exit(1)
    
    # Step 4: Run Streamlit app
    print("\n" + "="*60)
    if not run_streamlit_app():
        sys.exit(1)


if __name__ == "__main__":
    main()
