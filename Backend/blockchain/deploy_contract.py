import json
import os
from web3 import Web3
from solcx import compile_source, install_solc
from dotenv import load_dotenv
import sys

# Install specific solc version
install_solc('0.8.17')

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

def deploy_contract():
    """Deploy DocumentLog contract to Ganache and save deployment info"""
    # Connect to Ganache
    w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))
    
    # Check connection
    if not w3.is_connected():
        print("Could not connect to Ganache. Make sure it's running on http://127.0.0.1:7545")
        return False
    
    print("Connected to Ganache!")
    
    # Get deployment account (first account in Ganache)
    accounts = w3.eth.accounts
    if not accounts:
        print("No accounts found in Ganache")
        return False
    
    deployer_account = accounts[0]
    print(f"Using deployer account: {deployer_account}")
    
    # Get private key from .env file
    deployer_private_key = os.getenv('GANACHE_PRIVATE_KEY')
    if not deployer_private_key:
        print("Error: GANACHE_PRIVATE_KEY not found in .env file")
        print("Please add your private key to the .env file as GANACHE_PRIVATE_KEY=your_private_key")
        return False

    # Ensure proper private key format (should be hexadecimal string with or without 0x prefix)
    if deployer_private_key.startswith('0x'):
        deployer_private_key = deployer_private_key[2:]
    
    # Check if it's a valid hex string of the right length
    if not all(c in '0123456789abcdefABCDEF' for c in deployer_private_key) or len(deployer_private_key) != 64:
        print("Error: Private key must be a 64-character hex string (32 bytes)")
        print(f"Current length: {len(deployer_private_key)} characters")
        return False
    
    print(f"Using private key from .env file (valid format)")
    
    # Load contract source
    contract_path = os.path.join(os.path.dirname(__file__), 'contracts', 'DocumentLog.sol')
    if not os.path.exists(contract_path):
        print(f"Error: Contract file not found at {contract_path}")
        return False
        
    with open(contract_path, 'r') as file:
        contract_source = file.read()
    
    # Compile contract
    print("Compiling contract...")
    try:
        compiled_sol = compile_source(
            contract_source,
            output_values=['abi', 'bin'],
            solc_version='0.8.17'
        )
    except Exception as e:
        print(f"Error compiling contract: {str(e)}")
        return False
    
    # Extract contract data
    contract_id, contract_interface = compiled_sol.popitem()
    bytecode = contract_interface['bin']
    abi = contract_interface['abi']
    
    # Create contract instance
    DocumentLog = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Get nonce for deployment account
    nonce = w3.eth.get_transaction_count(deployer_account)
    
    # Build deployment transaction
    print("Building deployment transaction...")
    deploy_tx = DocumentLog.constructor().build_transaction({
        'from': deployer_account,
        'nonce': nonce,
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price
    })
    
    # Sign transaction
    print("Signing transaction...")
    try:
        # Ensure proper key format for signing
        private_key_bytes = bytes.fromhex(deployer_private_key)
        signed_tx = w3.eth.account.sign_transaction(deploy_tx, private_key=private_key_bytes)
        print(f"Transaction signed successfully: {type(signed_tx)}")
        
        # Debug check for raw_transaction
        if not hasattr(signed_tx, 'raw_transaction'):
            print("ERROR: signed_tx doesn't have raw_transaction attribute")
            print(f"signed_tx attributes: {dir(signed_tx)}")
            return False
    except Exception as e:
        print(f"Error signing transaction: {str(e)}")
        return False
    
    # Send transaction and get transaction hash
    print("Deploying contract...")
    try:
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)  # Use raw_transaction (with underscore)
    except Exception as e:
        print(f"Error sending transaction: {str(e)}")
        return False
    
    # Wait for transaction receipt
    print("Waiting for deployment confirmation...")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt.contractAddress
    
    print(f"Contract deployed successfully!")
    print(f"Contract Address: {contract_address}")
    
    # Save deployment info
    deployment_info = {
        "contract_address": contract_address,
        "transaction_hash": tx_hash.hex(),
        "deployer_address": deployer_account,
        "block_number": tx_receipt.blockNumber,
        "abi": abi
    }
    
    # Update config.json
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as file:
        config = json.load(file)
    
    config['contract_address'] = contract_address
    config['account_address'] = deployer_account
    # Store the private key in config (only for development environments)
    # In production, the private key should only be in .env
    if 'simulation_mode' in config and not config['simulation_mode']:
        config['private_key'] = deployer_private_key
    config['simulation_mode'] = False
    
    with open(config_path, 'w') as file:
        json.dump(config, file, indent=2)
    
    # Also save full deployment info as a separate file
    deployment_path = os.path.join(os.path.dirname(__file__), 'deployment_info.json')
    with open(deployment_path, 'w') as file:
        json.dump(deployment_info, file, indent=2)
    
    print(f"Deployment info saved to {deployment_path}")
    print(f"Config updated at {config_path}")
    
    return contract_address

if __name__ == "__main__":
    print("DocumentLog Contract Deployment Script")
    print("=====================================")
    print("This will deploy the contract to your local Ganache instance")
    print("Make sure Ganache is running on http://127.0.0.1:7545")
    
    # Check if python-dotenv is installed
    try:
        import dotenv
    except ImportError:
        print("Error: python-dotenv package is not installed")
        print("Please install it using: pip install python-dotenv")
        sys.exit(1)
        
    deploy_contract()
