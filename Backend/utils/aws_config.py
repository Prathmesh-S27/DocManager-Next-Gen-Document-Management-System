import os
import boto3
import json
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
dotenv_path = os.path.join(Path(__file__).parent.parent, '.env')
load_dotenv(dotenv_path)

# Configuration
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY') 
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
BUCKET_NAME = os.environ.get('BUCKET_NAME')
USER_TABLE_NAME = os.environ.get('USER_TABLE_NAME')
DOCS_TABLE_NAME = os.environ.get('DOCS_TABLE_NAME')

# Initialize AWS services
s3 = None
dynamodb = None
users_table = None
docs_table = None

# Define the table_exists function that will be imported by other modules
def table_exists(dynamodb_resource, table_name):
    """Check if a table exists in DynamoDB"""
    try:
        table = dynamodb_resource.Table(table_name)
        table.table_status  # This will trigger an exception if the table doesn't exist
        return True
    except Exception as e:
        print(f"Table {table_name} doesn't exist or error occurred: {str(e)}")
        return False

try:
    # Use environment variables or credential provider chain
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        # Use explicit credentials
        s3 = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )
        
        dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )
        
        print(f"Initialized AWS services with explicit credentials in region {AWS_REGION}")
    else:
        # Try default credential provider chain
        s3 = boto3.client('s3')
        dynamodb = boto3.resource('dynamodb')
        print("Initialized AWS services using default credential provider chain")
    
    # Connect to DynamoDB tables
    if DOCS_TABLE_NAME:
        docs_table = dynamodb.Table(DOCS_TABLE_NAME)
    if USER_TABLE_NAME:
        users_table = dynamodb.Table(USER_TABLE_NAME)
        
except NoCredentialsError:
    print("⚠️ WARNING: No AWS credentials found. S3 and DynamoDB services will be unavailable.")
    
except Exception as e:
    print(f"⚠️ WARNING: Error initializing AWS services: {e}")
