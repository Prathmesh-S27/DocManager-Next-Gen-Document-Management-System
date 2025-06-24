import os
import sys
import subprocess
import platform

def setup_test_env():
    """Set up a dedicated testing environment"""
    print("Setting up DocManager test environment...")
    
    # Determine the venv directory
    venv_dir = os.path.join(os.path.dirname(__file__), 'test_venv')
    
    # Check if venv already exists
    if os.path.exists(venv_dir):
        print(f"Test environment already exists at {venv_dir}")
        activate_script = "activate.bat" if platform.system() == "Windows" else "bin/activate"
        print(f"\nTo activate the environment, run:")
        print(f"    {os.path.join(venv_dir, activate_script)}")
        return
    
    # Create virtual environment
    print(f"Creating virtual environment at {venv_dir}...")
    subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
    
    # Determine pip command
    if platform.system() == "Windows":
        pip_cmd = os.path.join(venv_dir, "Scripts", "pip")
    else:
        pip_cmd = os.path.join(venv_dir, "bin", "pip")
    
    # Install required packages
    print("Installing required packages...")
    # Install all required packages for testing with real blockchain
    subprocess.check_call([pip_cmd, "install", 
        "pytest", 
        "pytest-cov", 
        "moto==4.1.12", 
        "web3>=6.0.0", 
        "python-dotenv",
        "flask",
        "boto3",
        "werkzeug",
        "flask-cors",
        "cryptography",
        "py-solc-x"
    ])
    
    # Create tests directory if it doesn't exist
    tests_dir = os.path.join(os.path.dirname(__file__), 'tests')
    if not os.path.exists(tests_dir):
        os.makedirs(tests_dir)
        # Create __init__.py
        with open(os.path.join(tests_dir, '__init__.py'), 'w') as f:
            f.write("# Tests package\n")
    
    print("\nTest environment setup complete!")
    activate_script = "activate.bat" if platform.system() == "Windows" else "bin/activate"
    print(f"\nTo activate the environment, run:")
    print(f"    {os.path.join(venv_dir, activate_script)}")
    print("\nThen run tests with:")
    print("    python run_tests.py")

if __name__ == "__main__":
    setup_test_env()
