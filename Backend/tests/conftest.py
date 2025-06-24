import os
import sys
import pytest
from flask import Flask
import boto3
from moto.dynamodb import mock_dynamodb
from moto.s3 import mock_s3
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app as flask_app
from utils.encryption import encryption_service
from blockchain.blockchain_logger import blockchain_logger, BlockchainLogger
from utils.merkle_tree import document_merkle_tree

@pytest.fixture
def app():
    """Create a Flask test client"""
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
      # Configure for testing
    flask_app.secret_key = "<TEST_SECRET_KEY>"
    
    # Use app context
    with flask_app.app_context():
        yield flask_app

@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()

@pytest.fixture
def mock_aws():
    """Set up mock AWS services"""
    with mock_dynamodb():
        with mock_s3():            # Set environment variables for AWS credentials
            os.environ['AWS_ACCESS_KEY_ID'] = '<TEST_AWS_ACCESS_KEY_ID>'
            os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
            os.environ['AWS_DEFAULT_REGION'] = 'eu-north-1'
            
            # Create mock DynamoDB tables
            dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')
            
            # Create user table
            dynamodb.create_table(
                TableName='Document_Detail',
                KeySchema=[
                    {'AttributeName': 'email', 'KeyType': 'HASH'},
                    {'AttributeName': 'user_id', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'email', 'AttributeType': 'S'},
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
            
            # Create document table
            dynamodb.create_table(
                TableName='Documents',
                KeySchema=[
                    {'AttributeName': 'document_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'document_id', 'AttributeType': 'S'},
                    {'AttributeName': 'email', 'AttributeType': 'S'},
                    {'AttributeName': 'keyword', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'EmailIndex',
                        'KeySchema': [
                            {'AttributeName': 'email', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    },
                    {
                        'IndexName': 'KeywordIndex',
                        'KeySchema': [
                            {'AttributeName': 'keyword', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    }
                ],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            )
            
            # Create S3 bucket
            s3 = boto3.client('s3', region_name='eu-north-1')
            try:
                s3.create_bucket(
                    Bucket='sihstorage',
                    CreateBucketConfiguration={'LocationConstraint': 'eu-north-1'}
                )
            except Exception as e:
                print(f"Error creating bucket: {e}")
            
            yield

@pytest.fixture
def blockchain_config():
    """Load the blockchain configuration"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'blockchain', 'config.json')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        pytest.skip(f"Could not load blockchain config: {e}")

@pytest.fixture
def real_blockchain(blockchain_config):
    """Get the blockchain logger based on configuration"""
    from blockchain.blockchain_logger import BlockchainLogger
    
    try:
        # Use the global blockchain_logger instance if already initialized
        from blockchain.blockchain_logger import blockchain_logger
        
        # Force connection to real blockchain if config says so
        if not blockchain_config.get('simulation_mode', True) and blockchain_logger.simulation_mode:
            print("Re-initializing blockchain logger with real connection")
            blockchain_logger = BlockchainLogger(config=blockchain_config)
            
        if not blockchain_logger.connected:
            pytest.skip("Blockchain logger not connected - skipping test")
            
        return blockchain_logger
    except Exception as e:
        pytest.skip(f"Error setting up blockchain logger: {e}")

@pytest.fixture
def authenticated_client(client):
    """Create a client with an authenticated session"""
    with client.session_transaction() as session:
        session['user_email'] = 'test@example.com'
        session['user_id'] = 'test_user_id'
        session['name'] = 'Test User'
    
    return client
