import os
import time
import subprocess
import sys

def run_command(command):
    """Run a command and print output in real-time"""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        shell=False  # Changed to False for better argument handling
    )
    
    # Print output in real-time
    for line in process.stdout:
        print(line, end='')
        
    # Wait for process to complete
    process.wait()
    return process.returncode

def main():
    print("Starting full blockchain document verification demo...")
    
    # Step 1: Check prerequisites and debug environment
    print("\n🔍 Checking prerequisites and environment...")
    
    # Check if Flask app is reachable
    print("Checking if Flask application is accessible...")
    import requests
    try:
        response = requests.get("http://127.0.0.1:5000/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Flask application is running and accessible")
        else:
            print(f"⚠️ Flask application returned status code {response.status_code}")
            proceed = input("Continue anyway? (y/n): ")
            if proceed.lower() != 'y':
                sys.exit(1)
    except requests.exceptions.RequestException:
        print("⚠️ Could not connect to Flask application")
        proceed = input("Continue anyway? (y/n): ")
        if proceed.lower() != 'y':
            sys.exit(1)
    
    # Check if Ganache is running
    ganache_check = input("Is Ganache running at http://localhost:7545? (y/n): ")
    if ganache_check.lower() != 'y':
        print("Please start Ganache before running the demo.")
        sys.exit(1)
    
    # Create screenshots directory
    screenshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    
    # Step 2: Run the document upload and verification demo
    print("\n🚀 Running document upload and verification demo...")
    
    # Set env var to help debug the form issue
    os.environ["PYTHONUNBUFFERED"] = "1"  # Ensure output is not buffered
    # Set env var to click "View" button instead of "Open"
    os.environ["CLICK_VIEW_BUTTON"] = "1"
    
    # Use list arguments instead of string to handle paths with spaces
    upload_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'automated_demo.py')
    upload_command = [sys.executable, upload_script]
    print(f"Running command: {' '.join(upload_command)}")
    upload_result = run_command(upload_command)
    
    if upload_result != 0:
        print("❌ Upload demo encountered issues.")
        continue_demo = input("Would you like to continue with the demo? (y/n): ")
        if continue_demo.lower() != 'y':
            sys.exit(1)
    
    # Wait for user confirmation to continue
    input("\n✅ Upload and verification phase completed. Press Enter to continue to Ganache exploration...")
    
    # Step 3: Run the Ganache exploration demo
    print("\n🔍 Running Ganache blockchain exploration...")
    ganache_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ganache_explorer.py')
    ganache_command = [sys.executable, ganache_script]
    print(f"Running command: {' '.join(ganache_command)}")
    ganache_result = run_command(ganache_command)
    
    if ganache_result != 0:
        print("⚠️ Ganache exploration had issues but continuing with demo.")
    
    # Extract the document ID from user input or screenshots
    document_id = input("\n🔑 Enter a Document ID for tamper detection (or press Enter to skip this step): ")
    
    # Step 4: Run the tamper detection demo if a document ID was provided
    if document_id.strip():
        print("\n🛡️ Running tamper detection demo...")
        tamper_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tamper_demo.py')
        tamper_command = [sys.executable, tamper_script]
        print(f"Running command: {' '.join(tamper_command)}")
        
        # Pass the document ID to the tamper demo through stdin
        process = subprocess.Popen(
            tamper_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            shell=False  # Changed to False for better argument handling
        )
        
        # Write the document ID to stdin
        process.stdin.write(f"{document_id}\n")
        process.stdin.flush()
        
        # Print output in real-time
        for line in process.stdout:
            print(line, end='')
            
        # Wait for process to complete
        process.wait()
    else:
        print("\n⏭️ Skipping tamper detection demo.")
    
    # Done!
    print("\n✅ Blockchain document verification demo completed!")
    print(f"Screenshots saved in: {screenshots_dir}")

if __name__ == "__main__":
    main()
