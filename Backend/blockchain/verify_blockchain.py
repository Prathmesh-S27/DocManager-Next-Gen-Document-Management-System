import json
import os
import time
import hashlib
from web3 import Web3
from dotenv import load_dotenv

def verify_blockchain_connection():
    """Verify connection to blockchain and contract functionality"""
    # Load environment variables
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path)
    
    # Load config
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as file:
        config = json.load(file)
    
    # Connect to provider
    w3 = Web3(Web3.HTTPProvider(config['provider_url']))
    
    if not w3.is_connected():
        print("❌ Failed to connect to Ethereum provider")
        print(f"   Provider URL: {config['provider_url']}")
        return False
    
    print("✅ Connected to Ethereum provider")
    print(f"   Provider URL: {config['provider_url']}")
    
    # Check contract address
    contract_address = config['contract_address']
    if contract_address == '0x0000000000000000000000000000000000000000':
        print("❌ Contract address is zero address")
        print("   Please deploy the contract first using deploy_contract.py")
        return False
    
    # Check if account and private key are set
    account_address = config['account_address']
    private_key = os.getenv('GANACHE_PRIVATE_KEY')
    if not private_key:
        private_key = config['private_key']
    
    # Ensure proper format for private key
    if private_key.startswith('0x'):
        private_key = private_key[2:]
    
    # Convert private key to bytes
    private_key_bytes = bytes.fromhex(private_key)
    
    if not account_address or account_address == '0x0000000000000000000000000000000000000000':
        print("❌ Account address not set or is zero address")
        return False
    
    if not private_key:
        print("❌ Private key not set")
        return False
    
    # Check account balance
    balance = w3.eth.get_balance(account_address)
    print(f"✅ Account balance: {w3.from_wei(balance, 'ether')} ETH")
    
    # Load ABI and create contract instance
    contract = w3.eth.contract(address=contract_address, abi=config['contract_abi'])
    
    # Check if contract exists by calling a view function
    try:
        total_docs = contract.functions.totalDocuments().call()
        print(f"✅ Contract verified: {total_docs} documents logged")
    except Exception as e:
        print(f"❌ Contract verification failed: {e}")
        return False
    
    # Test contract function
    try:
        print("\nTesting contract functionality with a sample document...")
        
        # Create test data
        document_id = hashlib.sha256(f"test-doc-{time.time()}".encode()).digest()
        user_hash = hashlib.sha256(b"test@example.com").digest()
        doc_hash = hashlib.sha256(b"test document content").digest()
        metadata_hash = hashlib.sha256(b'{"test": true}').digest()
        
        # Build transaction
        nonce = w3.eth.get_transaction_count(account_address)
        tx = contract.functions.logDocumentAction(
            document_id,  # document_id
            0,  # action (0 = UPLOAD)
            user_hash,  # user_hash
            doc_hash,  # document_hash
            metadata_hash  # metadata_hash
        ).build_transaction({
            'from': account_address,
            'nonce': nonce,
            'gas': 500000,  # Increased gas limit from 200000 to 500000
            'gasPrice': w3.eth.gas_price
        })
        
        # Sign transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key_bytes)
        
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)  # Use raw_transaction (with underscore)
        
        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if tx_receipt.status == 1:
            print(f"✅ Test transaction succeeded: {tx_hash.hex()}")
            
            # Verify document exists
            result = contract.functions.documentExists(document_id).call()
            print(f"✅ Document exists check: {result}")
            
            # Get document history
            indices = contract.functions.getDocumentHistory(document_id).call()
            print(f"✅ Document has {len(indices)} log entries")
            
            # Get log entry details
            if indices:
                entry = contract.functions.getLogEntry(indices[0]).call()
                print(f"✅ Log entry verified: Action={entry[1]}, Timestamp={entry[5]}")
        else:
            print(f"❌ Test transaction failed: {tx_receipt}")
            return False
    
    except Exception as e:
        print(f"❌ Contract test failed: {e}")
        # Print more detailed error for debugging
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ Blockchain integration verified successfully!")
    return True

if __name__ == "__main__":
    # Check if python-dotenv is installed
    try:
        import dotenv
    except ImportError:
        print("Warning: python-dotenv package is not installed")
        print("It's recommended to install it using: pip install python-dotenv")
    
    print("DocumentLog Contract Verification Script")
    print("=======================================")
    verify_blockchain_connection()
