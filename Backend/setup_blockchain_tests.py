import json
import os
import sys
from pathlib import Path
from web3 import Web3
import subprocess
import shutil
from dotenv import load_dotenv

def setup_blockchain_tests():
    """Configure the test environment to use real blockchain"""
    print("Setting up blockchain for testing...")
    
    # Load environment variables from .env
    dotenv_path = Path(__file__).parent / '.env'
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
        print(f"Loaded environment from {dotenv_path}")
    else:
        print(f"Warning: No .env file found at {dotenv_path}")
    
    # Path to blockchain config file
    config_path = Path(__file__).parent / 'blockchain' / 'config.json'
    
    # Check if the config file exists
    if not config_path.exists():
        print(f"Error: Blockchain config not found at {config_path}")
        return False
    
    try:
        # Read current config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Create a backup of the original config
        backup_path = config_path.with_suffix('.bak')
        shutil.copy(config_path, backup_path)
        print(f"Backed up original config to {backup_path}")
        
        # Update config for real blockchain use
        config['simulation_mode'] = False
        
        # Check Ganache connection
        provider_url = config.get('provider_url', 'http://localhost:7545')
        w3 = Web3(Web3.HTTPProvider(provider_url))
        
        if w3.is_connected():
            print(f"✅ Connected to Ethereum provider at {provider_url}")
            
            # Get contract address from config
            contract_address = config.get('contract_address')
            if not contract_address or contract_address == "0x0000000000000000000000000000000000000000":
                print("❌ Contract address not set in config.json")
                print("   Please deploy the contract first with deploy_contract.py")
                return False
                
            print(f"✅ Using contract at {contract_address}")
            
            # Check if private key is set
            private_key = os.getenv('GANACHE_PRIVATE_KEY')
            if not private_key:
                print("⚠️ GANACHE_PRIVATE_KEY not found in .env file")
                print("   Tests may fail if blockchain writes are needed")
            else:
                print("✅ GANACHE_PRIVATE_KEY found in .env")
                
            # Save the updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
                
            print(f"✅ Successfully updated {config_path}")
            print("   Blockchain tests will now use real Ganache transactions")
            return True
                
        else:
            print(f"❌ Could not connect to Ethereum provider at {provider_url}")
            print("   Please make sure Ganache is running")
            return False
            
    except Exception as e:
        print(f"Error setting up blockchain tests: {e}")
        return False

if __name__ == "__main__":
    success = setup_blockchain_tests()
    if success:
        print("\nBlockchain test setup completed successfully.")
        print("You can now run tests with: python run_tests.py")
    else:
        print("\nBlockchain test setup failed.")
        print("Tests will run in simulation mode.")
