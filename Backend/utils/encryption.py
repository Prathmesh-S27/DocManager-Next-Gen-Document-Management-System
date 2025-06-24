import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class EncryptionService:
    """Service for encrypting and decrypting files"""
    def __init__(self, master_key=None):
        # Set up master key - either use provided or generate
        if master_key:
            self.master_key = master_key.encode('utf-8')
        else:
            # Use environment variable if available, otherwise use default
            self.master_key = os.environ.get('ENCRYPTION_MASTER_KEY', '<YOUR_ENCRYPTION_MASTER_KEY>').encode('utf-8')
        
        # Key cache to remember encryption keys
        self.key_cache = {}
        
        # Generate a default key for quick operations
        self.default_key_id = 'default'
        self.default_key = self._generate_key(self.default_key_id)
        self.key_cache[self.default_key_id] = self.default_key
    
    def _generate_key(self, key_id):
        """Generate a key for Fernet encryption using our master key and a key ID"""
        # Use the key_id as salt
        salt = key_id.encode('utf-8')
        # If salt is too short, pad it
        if len(salt) < 16:
            salt = salt + b'0' * (16 - len(salt))
        # If salt is too long, truncate it
        if len(salt) > 16:
            salt = salt[:16]
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return key
    
    def encrypt_file(self, file_data, key_id=None):
        """Encrypt file data using Fernet symmetric encryption"""
        if not key_id:
            key_id = self.default_key_id
            key = self.default_key
        elif key_id in self.key_cache:
            key = self.key_cache[key_id]
        else:
            key = self._generate_key(key_id)
            self.key_cache[key_id] = key
            
        cipher = Fernet(key)
        encrypted_data = cipher.encrypt(file_data)
        
        return encrypted_data, key_id
    
    def decrypt_file(self, encrypted_data, key_id=None):
        """Decrypt file data using Fernet symmetric encryption"""
        try:
            if not key_id:
                key_id = self.default_key_id
                
            # Get the key from cache or generate it
            if key_id in self.key_cache:
                key = self.key_cache[key_id]
            else:
                key = self._generate_key(key_id)
                self.key_cache[key_id] = key
                
            cipher = Fernet(key)
            decrypted_data = cipher.decrypt(encrypted_data)
            
            return decrypted_data
        except Exception as e:
            print(f"Decryption error with key_id {key_id}: {str(e)}")
            
            # If specific key failed and it's not default, try with default key
            if key_id != self.default_key_id:
                try:
                    print(f"Trying fallback decryption with default key")
                    cipher = Fernet(self.default_key)
                    decrypted_data = cipher.decrypt(encrypted_data)
                    print(f"Fallback decryption succeeded")
                    return decrypted_data
                except Exception as default_error:
                    print(f"Default key decryption also failed: {str(default_error)}")
            
            # Re-raise the original error if all attempts fail
            raise

# Create a singleton instance
encryption_service = EncryptionService()
