import boto3
import os
import sys
import base64
from cryptography.fernet import Fernet
import argparse
from dotenv import load_dotenv

def debug_document_decryption(document_id):
    """Debug tool to diagnose decryption issues"""
    # Load environment variables
    load_dotenv()
    
    # AWS Configuration
    aws_access_key = os.getenv('AWS_ACCESS_KEY', '<YOUR_AWS_ACCESS_KEY>')
    aws_secret_key = os.getenv('AWS_SECRET_KEY', '<YOUR_AWS_SECRET_KEY>')
    aws_region = os.getenv('AWS_REGION', '<YOUR_AWS_REGION>')
    bucket_name = os.getenv('BUCKET_NAME', '<YOUR_BUCKET_NAME>')
    docs_table_name = os.getenv('DOCS_TABLE_NAME', '<YOUR_DOCS_TABLE_NAME>')
    
    # Initialize resources
    print("Initializing AWS resources...")
    s3 = boto3.client(
        's3',
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )
    
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )
    
    docs_table = dynamodb.Table(docs_table_name)
    
    # Get document metadata
    print(f"Retrieving document metadata for ID: {document_id}")
    try:
        response = docs_table.get_item(Key={'document_id': document_id})
        if 'Item' not in response:
            print(f"❌ Document not found with ID: {document_id}")
            return False
            
        document = response['Item']
        print(f"✅ Document found: {document.get('document_name')}")
        print(f"   Type: {document.get('document_type')}")
        print(f"   Size: {document.get('file_size')} bytes")
        
        # Check encryption key ID
        encryption_key_id = document.get('encryption_key_id')
        if encryption_key_id:
            print(f"✅ Encryption Key ID found: {encryption_key_id}")
        else:
            print(f"⚠️ No encryption key ID found, will use default")
        
        # Get S3 object
        s3_key = document.get('s3_key')
        if not s3_key:
            print(f"❌ No S3 key found for document")
            return False
            
        print(f"Getting S3 object: {s3_key}")
        try:
            s3_response = s3.get_object(
                Bucket=bucket_name,
                Key=s3_key
            )
            encrypted_data = s3_response['Body'].read()
            print(f"✅ Retrieved {len(encrypted_data)} bytes from S3")
            
            # Try decryption with both default key and document key
            master_key = os.environ.get('ENCRYPTION_MASTER_KEY', 'docmanager-secure-default-key-1234567890').encode('utf-8')
            
            # Try with document key ID first if available
            if encryption_key_id:
                try:
                    # Generate key from key ID
                    salt = encryption_key_id.encode('utf-8')
                    if len(salt) < 16:
                        salt = salt + b'0' * (16 - len(salt))
                    if len(salt) > 16:
                        salt = salt[:16]
                        
                    from cryptography.hazmat.primitives import hashes
                    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
                    kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt,
                        iterations=100000,
                    )
                    key = base64.urlsafe_b64encode(kdf.derive(master_key))
                    
                    cipher = Fernet(key)
                    decrypted_data = cipher.decrypt(encrypted_data)
                    print(f"✅ Decryption SUCCESS with document key ID")
                    print(f"   Decrypted size: {len(decrypted_data)} bytes")
                    print(f"   First 100 bytes (hex): {decrypted_data[:100].hex()[:100]}...")
                    
                    # Try to determine file type from header bytes
                    file_type = get_file_type(decrypted_data[:8])
                    print(f"   Detected file type: {file_type}")
                    
                    return True
                except Exception as e:
                    print(f"❌ Decryption FAILED with document key ID: {str(e)}")
            
            # Try with default key
            try:
                # Generate default key
                salt = b'default00000000'
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                default_key = base64.urlsafe_b64encode(kdf.derive(master_key))
                
                cipher = Fernet(default_key)
                decrypted_data = cipher.decrypt(encrypted_data)
                print(f"✅ Decryption SUCCESS with default key")
                print(f"   Decrypted size: {len(decrypted_data)} bytes")
                print(f"   First 100 bytes (hex): {decrypted_data[:100].hex()[:100]}...")
                
                # Try to determine file type from header bytes
                file_type = get_file_type(decrypted_data[:8])
                print(f"   Detected file type: {file_type}")
                
                return True
            except Exception as e:
                print(f"❌ Decryption FAILED with default key: {str(e)}")
            
            print("❌ All decryption attempts failed")
            return False
            
        except Exception as e:
            print(f"❌ Error retrieving file from S3: {str(e)}")
            return False
        
    except Exception as e:
        print(f"❌ Error retrieving document: {str(e)}")
        return False

def get_file_type(header_bytes):
    """Try to detect file type from header bytes"""
    # PDF: %PDF
    if header_bytes.startswith(b'%PDF'):
        return "PDF"
    # JPEG: FF D8 FF
    elif header_bytes.startswith(b'\xFF\xD8\xFF'):
        return "JPEG"
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    elif header_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return "PNG"
    # ZIP (including docx, xlsx): PK
    elif header_bytes.startswith(b'PK'):
        return "ZIP/Office"
    # Plain text - check for common ASCII
    elif all(byte < 127 and byte >= 32 for byte in header_bytes[:4]):
        return "Text"
    else:
        return "Unknown"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug document decryption issues")
    parser.add_argument('document_id', help="ID of the document to debug")
    args = parser.parse_args()
    
    if not args.document_id:
        print("Please provide a document ID to debug")
        sys.exit(1)
        
    print("Document Decryption Debugger")
    print("===========================")
    success = debug_document_decryption(args.document_id)
    
    if success:
        print("\n✅ Document decryption debug completed successfully")
    else:
        print("\n❌ Document decryption debug failed")
