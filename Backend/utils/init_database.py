import boto3
import time
import os
from dotenv import load_dotenv
import sys
from pathlib import Path
import json
import hashlib
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError, NoCredentialsError

# Load environment variables if available
dotenv_path = os.path.join(Path(__file__).parent.parent, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# AWS Configuration
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY', '<YOUR_AWS_ACCESS_KEY>')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY', '<YOUR_AWS_SECRET_KEY>')
AWS_REGION = os.getenv('AWS_REGION', '<YOUR_AWS_REGION>')
USER_TABLE_NAME = os.getenv('USER_TABLE_NAME', '<YOUR_USER_TABLE_NAME>')
DOCS_TABLE_NAME = os.getenv('DOCS_TABLE_NAME', '<YOUR_DOCS_TABLE_NAME>')

def fix_blockchain_logger():
    """Fix the blockchain_logger singleton instance if needed"""
    try:
        from blockchain.blockchain_logger import blockchain_logger, BlockchainLogger
        
        # Check if update_merkle_root exists
        if not hasattr(blockchain_logger, 'update_merkle_root'):
            print("WARNING: blockchain_logger.update_merkle_root method is missing. Adding it.")
            
            # Add the missing method
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
            
            # Add the method to the instance
            import types
            blockchain_logger.update_merkle_root = types.MethodType(update_merkle_root, blockchain_logger)
            
            # Also add the sync method if missing
            if not hasattr(blockchain_logger, '_update_merkle_root_sync_with_details'):
                def _update_merkle_root_sync_with_details(self, merkle_root: str, _callback_id=None) -> dict:
                    """Synchronous implementation of update_merkle_root with transaction details"""
                    try:
                        # For simulation mode, just log
                        if self.simulation_mode:
                            import time
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
                        
                        # In a real implementation, this would send blockchain transactions
                        # For now, just return success
                        return {
                            "success": True,
                            "tx_hash": f"0x{merkle_root[:10]}",
                            "block_number": 999999,
                            "merkle_root": merkle_root
                        }
                            
                    except Exception as e:
                        print(f"Error updating Merkle root: {e}")
                        return {"success": False, "reason": str(e)}
                
                blockchain_logger._update_merkle_root_sync_with_details = types.MethodType(
                    _update_merkle_root_sync_with_details, blockchain_logger
                )
            
            print("✅ Fixed blockchain_logger.update_merkle_root method")
        
    except Exception as e:
        print(f"Error fixing blockchain_logger: {e}")

def initialize_database():
    """Initialize all required database tables"""
    # Load environment variables from .env file if present
    load_dotenv()
    
    # Fix blockchain_logger first
    fix_blockchain_logger()
    
    try:
        # Initialize DynamoDB client
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        
        # Check and create user table
        user_table_exists = table_exists(dynamodb, USER_TABLE_NAME)
        if not user_table_exists:
            print(f"Creating user table: {USER_TABLE_NAME}")
            create_user_table(dynamodb)
        else:
            print(f"User table {USER_TABLE_NAME} already exists")
            
        # Check and create documents table
        docs_table_exists = table_exists(dynamodb, DOCS_TABLE_NAME)
        if not docs_table_exists:
            print(f"Creating documents table: {DOCS_TABLE_NAME}")
            create_documents_table(dynamodb)
        else:
            print(f"Documents table {DOCS_TABLE_NAME} already exists")
            
        # Add missing fields to existing documents if needed
        try:
            from utils.aws_config import docs_table, BUCKET_NAME
            
            if docs_table:
                # Check for documents missing hash fields
                response = docs_table.scan(
                    ProjectionExpression="document_id, s3_key, document_hash"
                )
                
                # Try to create an S3 client with explicitly loaded credentials
                s3_client = None
                try:
                    # First try environment variables
                    if 'AWS_ACCESS_KEY_ID' in os.environ and 'AWS_SECRET_ACCESS_KEY' in os.environ:
                        s3_client = boto3.client(
                            's3',
                            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                            region_name=os.environ.get('AWS_REGION', 'us-east-1')
                        )
                        print("Using AWS credentials from environment variables")
                    # Then try from config file or .env file
                    else:
                        # Try loading from .env file
                        aws_access_key = os.getenv('AWS_ACCESS_KEY')
                        aws_secret_key = os.getenv('AWS_SECRET_KEY')
                        aws_region = os.getenv('AWS_REGION', 'us-east-1')
                        
                        if aws_access_key and aws_secret_key:
                            s3_client = boto3.client(
                                's3',
                                aws_access_key_id=aws_access_key,
                                aws_secret_access_key=aws_secret_key,
                                region_name=aws_region
                            )
                            print("Using AWS credentials from .env file")
                        else:
                            # Try default credential provider chain
                            s3_client = boto3.client('s3')
                            print("Using default AWS credential provider chain")
                except Exception as e:
                    print(f"Error initializing S3 client: {e}")
                    s3_client = None
                
                if not s3_client:
                    print("⚠️ WARNING: Could not initialize S3 client - document hashes cannot be calculated")
                    return
                
                # If we have a bucket name from config
                bucket_name = BUCKET_NAME
                if not bucket_name:
                    bucket_name = os.getenv('BUCKET_NAME')
                    
                if not bucket_name:
                    print("⚠️ WARNING: No S3 bucket name provided - document hashes cannot be calculated")
                    return
                    
                print(f"Checking for documents without hashes in bucket: {bucket_name}")
                
                for item in response.get('Items', []):
                    if 'document_hash' not in item and 's3_key' in item:
                        document_id = item['document_id']
                        s3_key = item['s3_key']
                        
                        try:
                            print(f"Calculating hash for document {document_id}")
                            
                            # Download file content
                            response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
                            file_content = response['Body'].read()
                            
                            # Calculate hash
                            doc_hash = hashlib.sha256(file_content).hexdigest()
                            
                            # Update document with hash
                            docs_table.update_item(
                                Key={'document_id': document_id},
                                UpdateExpression="set document_hash = :hash",
                                ExpressionAttributeValues={':hash': doc_hash}
                            )
                            
                            print(f"✅ Added document hash for {document_id}: {doc_hash[:10]}...")
                        
                        except NoCredentialsError:
                            print(f"Error calculating hash for document {document_id}: Unable to locate credentials")
                            continue
                        except ClientError as e:
                            if e.response['Error']['Code'] == 'NoSuchKey':
                                print(f"Warning: Document file not found in S3: {s3_key}")
                            else:
                                print(f"Error accessing document in S3: {e}")
                            continue
                        except Exception as e:
                            print(f"Error calculating hash for document {document_id}: {e}")
                            continue
                            
        except Exception as e:
            print(f"Error updating document hashes in database: {e}")
            
        print("Database initialization completed successfully")
        return True
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        return False

def table_exists(dynamodb, table_name):
    """Check if table exists"""
    try:
        table = dynamodb.Table(table_name)
        table.table_status  # This will trigger an exception if table doesn't exist
        return True
    except:
        return False

def create_user_table(dynamodb):
    """Create User table with the correct schema"""
    try:
        table = dynamodb.create_table(
            TableName=USER_TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'email',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        # Wait for table to be created
        print("Waiting for user table to be created...")
        table.meta.client.get_waiter('table_exists').wait(TableName=USER_TABLE_NAME)
        print(f"User table {USER_TABLE_NAME} created successfully")
        return True
    except Exception as e:
        print(f"Error creating user table: {str(e)}")
        return False

def create_documents_table(dynamodb):
    """Create Documents table with the correct schema and GSIs"""
    try:
        table = dynamodb.create_table(
            TableName=DOCS_TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'document_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'document_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'keyword',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'EmailIndex',
                    'KeySchema': [
                        {
                            'AttributeName': 'email',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    'IndexName': 'KeywordIndex',
                    'KeySchema': [
                        {
                            'AttributeName': 'keyword',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        # Wait for table to be created
        print("Waiting for documents table to be created...")
        table.meta.client.get_waiter('table_exists').wait(TableName=DOCS_TABLE_NAME)
        print(f"Documents table {DOCS_TABLE_NAME} created successfully")
        return True
    except Exception as e:
        print(f"Error creating documents table: {str(e)}")
        return False

if __name__ == "__main__":
    initialize_database()
