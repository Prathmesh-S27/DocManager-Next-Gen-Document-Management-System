import json
import hashlib
import os
from typing import Dict, Any, List, Optional
from web3 import Web3
from web3.exceptions import ContractLogicError
import threading
import queue
import time

class BlockchainLogger:
    """Interface for logging document operations to a blockchain"""
    
    # Action type constants - must match the contract enum
    ACTION_UPLOAD = 0
    ACTION_UPDATE = 1
    ACTION_DOWNLOAD = 2
    ACTION_DELETE = 3
    ACTION_VERSION = 4
    ACTION_SHARE = 5
    ACTION_RESTORE = 6
    
    # User action types (stored separately since they don't match the contract enum)
    USER_LOGIN = "LOGIN"
    USER_LOGOUT = "LOGOUT"
    USER_REGISTER = "REGISTER"
    USER_UPDATE = "UPDATE"
    USER_PASSWORD_CHANGE = "PASSWORD_CHANGE"
    
    def __init__(self, config_path=None, simulation_mode=None):
        """Initialize the blockchain logger"""
        # Default config path
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'config.json')
        
        # Load configuration
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading blockchain config: {e}")
            # Default config for local development
            self.config = {
                'provider_url': 'http://localhost:7545',  # Ganache default
                'contract_address': None,
                'contract_abi': None,
                'account_address': None,
                'private_key': None,
                'simulation_mode': False
            }
        
        # Set simulation mode - parameter overrides config
        if simulation_mode is not None:
            self.simulation_mode = simulation_mode
        else:
            self.simulation_mode = self.config.get('simulation_mode', False)
        
        # Check if we need to force simulation mode due to missing config
        if not self.simulation_mode:
            # Check if contract address is valid
            if not self.config.get('contract_address') or self.config.get('contract_address') == '0x0000000000000000000000000000000000000000':
                print("WARNING: Contract address is zero address or not provided. Running in simulation mode.")
                self.simulation_mode = True
            
            # Check if account address is valid
            if not self.config.get('account_address') or self.config.get('account_address') == '0x0000000000000000000000000000000000000000':
                print("WARNING: Account address is zero address or not provided. Running in simulation mode.")
                self.simulation_mode = True
            
            # Check if private key is provided
            if not self.config.get('private_key'):
                print("WARNING: No private key provided. Running in simulation mode.")
                self.simulation_mode = True
        
        if self.simulation_mode:
            print("Blockchain logger running in SIMULATION mode - no real transactions will be sent.")
            print("To use real blockchain transactions:")
            print("1. Deploy the contract using deploy_contract.py")
            print("2. Update config.json with contract_address, account_address, and private_key")
            print("3. Set simulation_mode to false in config.json")
        
        # Initialize Web3 connection
        self.web3 = None
        self.contract = None
        self.connected = False
        self.connect()
        
        # Setup async operation queue
        self.operation_queue = queue.Queue()
        self.worker_thread = None
        self.stop_worker = False
        
        # In-memory log for simulation mode
        self.simulation_logs = []
    
    def connect(self) -> bool:
        """Connect to the blockchain network"""
        if self.simulation_mode:
            print("Running in simulation mode - no real connection established")
            self.connected = True
            return True
            
        try:
            # Connect to provider
            self.web3 = Web3(Web3.HTTPProvider(self.config['provider_url']))
            
            if not self.web3.is_connected():
                print(f"Failed to connect to Ethereum provider at {self.config['provider_url']}")
                print("Switching to simulation mode")
                self.simulation_mode = True
                self.connected = True
                return True
            
            print(f"Connected to Ethereum provider at {self.config['provider_url']}")
            
            # Load contract if ABI and address available
            contract_address = self.config['contract_address']
            contract_abi = self.config['contract_abi']
            
            if contract_address and contract_abi:
                # Convert address to checksum address if needed
                if not self.web3.is_checksum_address(contract_address):
                    contract_address = self.web3.to_checksum_address(contract_address)
                
                self.contract = self.web3.eth.contract(
                    address=contract_address,
                    abi=contract_abi
                )
                
                # Verify contract by calling a view function
                try:
                    total_docs = self.contract.functions.totalDocuments().call()
                    total_operations = self.contract.functions.totalOperations().call()
                    print(f"Connected to DocumentLog contract at {contract_address}")
                    print(f"Contract status: {total_docs} documents, {total_operations} operations")
                    self.connected = True
                    return True
                except Exception as e:
                    print(f"Error verifying contract: {e}")
                    print("Contract might not be deployed correctly. Switching to simulation mode.")
                    self.simulation_mode = True
                    self.connected = True
                    return True
            else:
                print("Contract address or ABI not configured")
                self.simulation_mode = True
                self.connected = True
                return True
                
        except Exception as e:
            print(f"Error connecting to blockchain: {e}")
            self.simulation_mode = True
            self.connected = True
            return True
    
    def start_worker(self):
        """Start the asynchronous worker thread"""
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
        
        self.stop_worker = False
        self.worker_thread = threading.Thread(target=self._process_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()
    
    def stop_worker(self):
        """Stop the asynchronous worker thread"""
        if self.worker_thread is None:
            return
            
        self.stop_worker = True
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)
    
    def _process_queue(self):
        """Process operations in the queue"""
        while not self.stop_worker:
            try:
                # Get operation with timeout to allow checking stop condition
                operation, args, kwargs = self.operation_queue.get(timeout=1.0)
                
                try:
                    # Execute the operation
                    operation(*args, **kwargs)
                except Exception as e:
                    print(f"Error processing blockchain operation: {e}")
                
                self.operation_queue.task_done()
                
            except queue.Empty:
                continue
    
    def _hash_string(self, input_str: str) -> bytes:
        """Create SHA-256 hash of a string"""
        return hashlib.sha256(input_str.encode('utf-8')).digest()
    
    def _hash_dict(self, input_dict: Dict[str, Any]) -> bytes:
        """Create SHA-256 hash of a dictionary"""
        # Convert dict to canonical JSON string and hash it
        json_str = json.dumps(input_dict, sort_keys=True)
        return self._hash_string(json_str)
    
    def _bytes32_from_str(self, input_str: str) -> bytes:
        """Convert string to bytes32"""
        # Get SHA-256 hash if string is too long
        if len(input_str.encode('utf-8')) > 32:
            return self._hash_string(input_str)
        
        # Otherwise pad with zeros
        return input_str.encode('utf-8').ljust(32, b'\0')
    
    def log_document_action(self, 
                           document_id: str, 
                           action_type: int, 
                           user_email: str,
                           document_data: Optional[bytes] = None,
                           metadata: Optional[Dict[str, Any]] = None,
                           async_mode: bool = True) -> bool:
        """
        Log a document action to the blockchain
        
        Args:
            document_id: Document identifier
            action_type: Type of action (use ACTION_* constants)
            user_email: User's email address
            document_data: Document content bytes (optional)
            metadata: Document metadata (optional)
            async_mode: Whether to process asynchronously
        
        Returns:
            Success status (always True for async_mode=True)
        """
        if not self.connected:
            print("Not connected to blockchain")
            return False
        
        # Queue the operation if in async mode
        if async_mode:
            self.operation_queue.put((
                self._log_document_action_sync,
                [document_id, action_type, user_email, document_data, metadata],
                {}
            ))
            
            # Ensure worker is running
            self.start_worker()
            return True
        
        # Otherwise process synchronously
        return self._log_document_action_sync(
            document_id, action_type, user_email, document_data, metadata
        )
    
    def _log_document_action_sync(self,
                               document_id: str,
                               action_type: int,
                               user_email: str,
                               document_data: Optional[bytes] = None,
                               metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Synchronous implementation of log_document_action"""
        try:
            # For simulation mode, just store in memory
            if self.simulation_mode:
                # Calculate document hash for verification purposes
                doc_hash = None
                if document_data:
                    doc_hash = hashlib.sha256(document_data).hexdigest()
                    
                log_entry = {
                    'timestamp': time.time(),
                    'document_id': document_id,
                    'action_type': action_type,
                    'user_email': user_email,
                    'document_hash': doc_hash,  # Store the full hex hash for verification
                    'has_document_data': document_data is not None,
                    'metadata': metadata or {}
                }
                self.simulation_logs.append(log_entry)
                print(f"[SIMULATION] Document action logged: {document_id}, Action: {action_type}")
                return True
            
            # Convert inputs to bytes32
            doc_id_bytes = self._bytes32_from_str(document_id)
            user_hash = self._hash_string(user_email)
            
            # Hash document data if provided (always calculate for UPLOAD and VERSION actions)
            full_doc_hash_hex = None
            if document_data:
                doc_hash = hashlib.sha256(document_data).digest()
                full_doc_hash_hex = doc_hash.hex()  # Save the full hex hash for verification
                
                # Add the document hash to metadata for document upload actions
                if action_type in [self.ACTION_UPLOAD, self.ACTION_VERSION]:
                    if metadata is None:
                        metadata = {}
                    metadata['document_hash'] = full_doc_hash_hex
                    print(f"Storing document hash in blockchain: {full_doc_hash_hex}")
            else:
                doc_hash = b'\0' * 32  # Empty hash
            
            # Convert metadata to hash
            if metadata:
                metadata_hash = self._hash_dict(metadata)
            else:
                metadata_hash = b'\0' * 32  # Empty hash
            
            # Build transaction
            tx = self.contract.functions.logDocumentAction(
                doc_id_bytes,
                action_type,
                user_hash,
                doc_hash,
                metadata_hash
            ).build_transaction({
                'from': self.config['account_address'],
                'nonce': self.web3.eth.get_transaction_count(self.config['account_address']),
                'gas': 1000000,  # Increased gas limit from 500000 to 1000000
                'gasPrice': self.web3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(
                tx, private_key=self.config['private_key']
            )
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)  # Use raw_transaction (with underscore)
            
            # Wait for receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:  # Success
                print(f"Document action logged to blockchain: {document_id}, Action: {action_type}")
                return True
            else:
                print(f"Transaction failed: {receipt}")
                return False
                
        except Exception as e:
            print(f"Error logging to blockchain: {e}")
            # Fall back to simulation mode if something fails
            if not self.simulation_mode:
                print(f"Falling back to simulation mode for this transaction")
                log_entry = {
                    'timestamp': time.time(),
                    'document_id': document_id,
                    'action_type': action_type,
                    'user_email': user_email,
                    'has_document_data': document_data is not None,
                    'metadata': metadata or {},
                    'error': str(e)
                }
                self.simulation_logs.append(log_entry)
                return True
            return False
    
    def get_document_hash_from_blockchain(self, document_id: str) -> Optional[str]:
        """
        Retrieve the document hash stored in blockchain at the time of upload
        
        Args:
            document_id: Document identifier
            
        Returns:
            Document hash as string or None if not found
        """
        print(f"🔍 Looking for document hash in blockchain for document: {document_id}")
        
        if self.simulation_mode:
            # Check simulation logs for document actions
            for log in self.simulation_logs:
                if log.get('document_id') == document_id and log.get('action_type') == self.ACTION_UPLOAD:
                    doc_hash = log.get('document_hash')
                    if doc_hash:
                        print(f"📄 Found document hash in simulation logs: {doc_hash}")
                        return doc_hash
                    # Also check metadata for newer format logs
                    metadata = log.get('metadata', {})
                    if metadata and 'document_hash' in metadata:
                        doc_hash = metadata['document_hash']
                        print(f"📄 Found document hash in simulation logs metadata: {doc_hash}")
                        return doc_hash
            return None
        
        try:
            if not self.connected or not self.contract:
                return None
                
            # Get document history
            history = self.get_document_history(document_id)
            
            # Look for upload actions with document hash
            for action in history:
                if action.get('action_type') == self.ACTION_UPLOAD:
                    # Check if document hash is stored directly
                    if action.get('document_hash') and action.get('document_hash') != '0x' + ('0' * 64):
                        doc_hash = action['document_hash']
                        print(f"📄 Found document hash directly in blockchain: {doc_hash}")
                        return doc_hash
                    
                    # Also check if we can retrieve and parse metadata
                    try:
                        metadata_hash = action.get('metadata_hash')
                        if metadata_hash and metadata_hash != '0x' + ('0' * 64):
                            # Try to retrieve the actual metadata
                            # This would require additional contract functions to store and retrieve metadata
                            # For now, we only have the hash, but in a more advanced implementation
                            # we could store and retrieve the actual metadata
                            pass
                    except:
                        pass
            
            print("❌ No document hash found in blockchain records")
            return None
        except Exception as e:
            print(f"Error retrieving document hash from blockchain: {e}")
            return None

    def update_merkle_root(self, merkle_root: str, async_mode: bool = True) -> dict:
        """
        Update the document Merkle root hash and return transaction details
        
        Args:
            merkle_root: Hex string of Merkle root hash
            async_mode: Whether to process asynchronously
        
        Returns:
            Dictionary with transaction details (tx_hash, block_number) or success status
        """
        if not self.connected:
            print("Not connected to blockchain")
            return {"success": False, "reason": "Not connected to blockchain"}
        
        # Queue the operation if in async mode
        if async_mode:
            future_result = {"pending": True, "async_requested": True}
            self.operation_queue.put((
                self._update_merkle_root_sync_with_details, 
                [merkle_root], 
                {"_callback_id": id(future_result)}
            ))
            self.start_worker()
            return future_result
        
        # Otherwise process synchronously
        return self._update_merkle_root_sync_with_details(merkle_root)

    def _update_merkle_root_sync_with_details(self, merkle_root: str, _callback_id=None) -> dict:
        """Synchronous implementation of update_merkle_root with transaction details"""
        try:
            # For simulation mode, just log
            if self.simulation_mode:
                log_entry = {
                    'timestamp': time.time(),
                    'action': 'UPDATE_MERKLE_ROOT',
                    'merkle_root': merkle_root
                }
                self.simulation_logs.append(log_entry)
                print(f"[SIMULATION] Merkle root updated: {merkle_root}")
                return {
                    "success": True, 
                    "simulated": True, 
                    "merkle_root": merkle_root,
                    "timestamp": time.time()
                }
                    
            # Convert merkle root to bytes32
            if merkle_root.startswith('0x'):
                root_bytes = bytes.fromhex(merkle_root[2:])
            else:
                root_bytes = bytes.fromhex(merkle_root)
            
            # Ensure it's bytes32
            if len(root_bytes) != 32:
                root_bytes = root_bytes.ljust(32, b'\0')
            
            # Build transaction
            tx = self.contract.functions.updateMerkleRoot(root_bytes).build_transaction({
                'from': self.config['account_address'],
                'nonce': self.web3.eth.get_transaction_count(self.config['account_address']),
                'gas': 500000,
                'gasPrice': self.web3.eth.gas_price
            })
            
            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(
                tx, private_key=self.config['private_key']
            )
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash_hex = self.web3.to_hex(tx_hash)
            
            # Wait for receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:  # Success
                block_number = receipt.blockNumber
                print(f"Merkle root updated in blockchain: {merkle_root}")
                print(f"Transaction hash: {tx_hash_hex}")
                print(f"Block number: {block_number}")
                
                # Return transaction details
                return {
                    "success": True,
                    "tx_hash": tx_hash_hex,
                    "block_number": block_number,
                    "merkle_root": merkle_root
                }
            else:
                print(f"Transaction failed: {receipt}")
                return {
                    "success": False, 
                    "reason": "Transaction failed", 
                    "receipt": str(receipt)
                }
                    
        except Exception as e:
            print(f"Error updating Merkle root: {e}")
            return {"success": False, "reason": str(e)}

    def verify_root_in_blockchain(self, merkle_root: str) -> dict:
        """
        Verify if a Merkle root exists in the blockchain
        
        Args:
            merkle_root: Hex string of Merkle root to verify
            
        Returns:
            Dictionary with verification status and details
        """
        print(f"🔍 Verifying Merkle root in blockchain: {merkle_root}")
        
        if self.simulation_mode:
            print("Running in simulation mode - checking simulated logs")
            # Look through simulation logs for the merkle root
            for log in self.simulation_logs:
                if log.get('action') == 'UPDATE_MERKLE_ROOT' and log.get('merkle_root') == merkle_root:
                    print(f"✅ Found exact match in simulation logs: {merkle_root}")
                    return {
                        'verified': True,
                        'simulated': True,
                        'match_type': 'exact',
                        'timestamp': log.get('timestamp', 0),
                        'matched_root': merkle_root
                    }
            
            # Try normalized comparison (without 0x prefix and case-insensitive)
            normalized_root = merkle_root.lower()
            if normalized_root.startswith('0x'):
                normalized_root = normalized_root[2:]
                
            for log in self.simulation_logs:
                if log.get('action') == 'UPDATE_MERKLE_ROOT':
                    log_root = log.get('merkle_root', '').lower()
                    if log_root.startswith('0x'):
                        log_root = log_root[2:]
                        
                    if log_root == normalized_root:
                        print(f"✅ Found normalized match in simulation logs: {merkle_root}")
                        return {
                            'verified': True,
                            'simulated': True,
                            'match_type': 'normalized',
                            'timestamp': log.get('timestamp', 0),
                            'matched_root': log.get('merkle_root')
                        }
            
            return {'verified': False, 'simulated': True}
        
        try:
            if not self.connected or not self.contract:
                return {'verified': False, 'error': 'Not connected to blockchain'}
            
            # Get all historical merkle roots
            all_roots = self.get_all_historical_merkle_roots()
            
            # Check for exact match
            for root_data in all_roots:
                if root_data.get('root') == merkle_root:
                    print(f"✅ Found exact match in blockchain: {merkle_root}")
                    return {
                        'verified': True,
                        'match_type': 'exact',
                        'block_number': root_data.get('block_number', 'Unknown'),
                        'timestamp': root_data.get('timestamp', 0),
                        'matched_root': merkle_root
                    }
            
            # Try normalized comparison
            normalized_root = merkle_root.lower()
            if normalized_root.startswith('0x'):
                normalized_root = normalized_root[2:]
                
            for root_data in all_roots:
                blockchain_root = root_data.get('root', '').lower()
                if blockchain_root.startswith('0x'):
                    blockchain_root = blockchain_root[2:]
                    
                if blockchain_root == normalized_root:
                    print(f"✅ Found normalized match in blockchain: {root_data.get('root')}")
                    return {
                        'verified': True,
                        'match_type': 'normalized',
                        'block_number': root_data.get('block_number', 'Unknown'),
                        'timestamp': root_data.get('timestamp', 0),
                        'matched_root': root_data.get('root')
                    }
            
            print("❌ Merkle root not found in blockchain records")
            return {'verified': False}
            
        except Exception as e:
            print(f"Error verifying Merkle root in blockchain: {e}")
            return {'verified': False, 'error': str(e)}

    def get_all_historical_merkle_roots(self) -> list:
        """
        Get all historical Merkle roots stored in the blockchain
        
        Returns:
            List of dicts containing root hash and timestamp
        """
        if self.simulation_mode:
            # Return simulated logs for merkle root updates
            roots = []
            for log in self.simulation_logs:
                if log.get('action') == 'UPDATE_MERKLE_ROOT' and 'merkle_root' in log:
                    roots.append({
                        'root': log['merkle_root'],
                        'timestamp': log.get('timestamp', 0),
                        'simulated': True
                    })
            return sorted(roots, key=lambda x: x.get('timestamp', 0), reverse=True)
        
        try:
            if not self.connected or not self.contract:
                return []
                
            # Get all merkle root update events
            filter_from_block = 0  # Start from genesis/first block
            current_block = self.web3.eth.block_number
            
            # Create filter for MerkleRootUpdated events
            event_filter = self.contract.events.MerkleRootUpdated.create_filter(
                fromBlock=filter_from_block,
                toBlock=current_block
            )
            
            # Get all events
            events = event_filter.get_all_entries()
            
            # Process events
            roots = []
            for event in events:
                block_number = event['blockNumber']
                try:
                    # Get block timestamp
                    block = self.web3.eth.get_block(block_number)
                    timestamp = block.timestamp
                    
                    # Extract merkle root from event
                    merkle_root = '0x' + event['args']['newRoot'].hex()
                    
                    roots.append({
                        'root': merkle_root,
                        'block_number': block_number,
                        'timestamp': timestamp
                    })
                except Exception as e:
                    print(f"Error processing event at block {block_number}: {e}")
            
            return sorted(roots, key=lambda x: x.get('timestamp', 0), reverse=True)
            
        except Exception as e:
            print(f"Error getting historical Merkle roots: {e}")
            return []

    def get_blockchain_status(self) -> dict:
        """
        Get the current status of the blockchain connection
        
        Returns:
            Dictionary with blockchain connection status
        """
        status = {
            'connected': self.connected,
            'simulation_mode': self.simulation_mode,
            'provider_url': self.config['provider_url'],
        }
        
        # Add contract information if available
        if self.contract:
            status['contract_address'] = self.config['contract_address']
        
        # Add historical stats if available in simulation mode
        if self.simulation_mode:
            operations_count = len(self.simulation_logs)
            upload_count = len([log for log in self.simulation_logs 
                              if log.get('action_type') == self.ACTION_UPLOAD])
            
            status['operations_count'] = operations_count
            status['upload_count'] = upload_count
            
        return status

# Singleton instance for application use
blockchain_logger = BlockchainLogger()
