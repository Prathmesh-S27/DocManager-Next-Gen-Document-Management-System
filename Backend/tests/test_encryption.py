import pytest
import os
from utils.encryption import encryption_service, EncryptionService

class TestEncryption:
    def test_encrypt_decrypt(self):
        """Test encryption and decryption of data"""
        # Test data
        test_data = b"This is a test document for encryption"
        
        # Encrypt the data
        encrypted_data, key_id = encryption_service.encrypt_file(test_data)
        
        # Verify encryption produced different data
        assert encrypted_data != test_data
        
        # Decrypt the data
        decrypted_data = encryption_service.decrypt_file(encrypted_data, key_id)
        
        # Verify decryption returns original data
        assert decrypted_data == test_data
    
    def test_key_persistence(self):
        """Test that encryption keys are correctly persisted"""
        # Create a new encryption service
        custom_service = EncryptionService(master_key="test-master-key-for-unit-testing")
        
        # Test data
        test_data = b"Data for key persistence test"
        
        # Encrypt with a specific key ID
        encrypted_data, key_id = custom_service.encrypt_file(test_data, key_id="test-key-1")
        
        # Verify the key ID was used
        assert key_id == "test-key-1"
        
        # Decrypt the data using the same key ID
        decrypted_data = custom_service.decrypt_file(encrypted_data, key_id="test-key-1")
        
        # Verify decryption was successful
        assert decrypted_data == test_data
    
    def test_default_key_fallback(self):
        """Test fallback to default key when specified key is not available"""
        test_data = b"Fallback test data"
        
        # Encrypt with default key
        encrypted_data, _ = encryption_service.encrypt_file(test_data)
        
        # Try to decrypt with a non-existent key, should fall back to default
        decrypted_data = encryption_service.decrypt_file(encrypted_data, key_id="nonexistent-key")
        
        # Verify fallback decryption worked
        assert decrypted_data == test_data
