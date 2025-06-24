# This script runs all tests with pytest

import pytest
import sys
import os
from pathlib import Path

def run_tests():
    """Run all tests with pytest"""
    # Set environment variables for testing
    os.environ['TESTING'] = 'True'
    
    # Add current directory to path if not already there
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())
    
    # Make sure the .env file exists
    dotenv_path = Path(__file__).parent / '.env'
    if not dotenv_path.exists():
        print("WARNING: .env file does not exist. Tests that require real blockchain may fail.")
        
        # Create minimal .env file for testing if it doesn't exist
        try:
            with open(dotenv_path, 'w') as f:
                f.write("GANACHE_PRIVATE_KEY=56a16e3e237dc5baa288bfe7ba069dc04e8e1a8da96113bc4fccb1e515ee2a6d\n")
                f.write("AWS_ACCESS_KEY=AKIA4DMVQVG7KBEHMPHN\n")
                f.write("AWS_SECRET_KEY=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\n")
                f.write("AWS_REGION=eu-north-1\n")
                f.write("BUCKET_NAME=sihstorage\n")
                f.write("USER_TABLE_NAME=Document_Detail\n")
                f.write("DOCS_TABLE_NAME=Documents\n")
            print("Created minimal .env file for testing")
        except Exception as e:
            print(f"Error creating .env file: {e}")
    
    # Run pytest with appropriate arguments
    args = [
        '-v',                # verbose
        '--no-header',       # no header
        '--no-summary',      # no summary
        '-s',                # allow print statements
        '--disable-warnings', # Disable warning reports
        'tests'              # test directory
    ]
    
    # Add any command line arguments
    args.extend(sys.argv[1:])
    
    return pytest.main(args)

if __name__ == "__main__":
    print("Running DocManager tests...")
    sys.exit(run_tests())
