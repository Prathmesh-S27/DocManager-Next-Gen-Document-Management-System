import pytest
from blockchain.blockchain_logger import BlockchainLogger
import os
import time
import json
import hashlib

class TestBlockchainLogger:
    def test_blockchain_connection(self, real_blockchain, blockchain_config):
        """Test blockchain connection based on configuration"""
        # If using simulation mode, skip real connection test
        if blockchain_config.get('simulation_mode', True):
            pytest.skip("Test requires real blockchain but running in simulation mode")
            
        # Verify we're connected
        assert real_blockchain.connected
        
        # If explicitly set to non-simulation mode, verify that
        if not blockchain_config.get('simulation_mode', True):
            assert not real_blockchain.simulation_mode
        
        # Get status and check basic fields
        status = real_blockchain.get_blockchain_status()
        assert 'connected' in status
        assert status['connected'] == True
    
    def test_merkle_root_update(self, real_blockchain, blockchain_config):
        """Test updating the Merkle root"""
        # If using simulation mode, make that explicit
        if blockchain_config.get('simulation_mode', True):
            assert real_blockchain.simulation_mode
        
        # Generate a test root hash
        test_root = hashlib.sha256(f"test_merkle_root_{time.time()}".encode()).hexdigest()
        
        # Update the Merkle root
        success = real_blockchain.update_merkle_root(test_root)
        
        # Verify update was successful
        assert success == True
    
    def test_document_logging(self, real_blockchain):
        """Test logging document actions"""
        # Create test document data
        document_id = f"test-doc-{time.time()}"
        document_data = b"Test content for document logging"
        
        # Log document action
        success = real_blockchain.log_document_action(
            document_id=document_id,
            action_type=0,  # Upload action
            user_email="test@example.com",
            document_data=document_data
        )
        
        # Verify logging was successful
        assert success == True
        
        # Verify document history can be retrieved
        history = real_blockchain.get_document_history(document_id)
        
        # In simulation mode we'll get entries, in real mode we might not get them yet
        if real_blockchain.simulation_mode:
            assert len(history) > 0

    def test_simulation_mode(self):
        """Test blockchain logger in simulation mode"""
        # Create logger in simulation mode
        logger = BlockchainLogger(simulation_mode=True)
        
        # Check initial state
        assert logger.simulation_mode == True
        assert logger.connected == True  # Always connected in simulation mode
        
        # Log a document action
        document_id = "test-doc-3"
        action_type = BlockchainLogger.ACTION_UPLOAD
        user_email = "test@example.com"
        document_data = b"Test document content"
        metadata = {"test_key": "test_value"}
        
        success = logger.log_document_action(
            document_id=document_id,
            action_type=action_type,
            user_email=user_email,
            document_data=document_data,
            metadata=metadata
        )
        
        # Verify logging was successful
        assert success == True
        
        # Get document history
        history = logger.get_document_history(document_id)
        
        # Verify history contains our entry
        assert len(history) == 1
        assert history[0].get('action_type') == action_type
