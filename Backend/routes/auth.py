from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from boto3.dynamodb.conditions import Key
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from blockchain.blockchain_logger import blockchain_logger, BlockchainLogger
import hashlib
from datetime import datetime

# Import from centralized AWS config - including table_exists function
from utils.aws_config import dynamodb, users_table as user_table, table_exists, s3, BUCKET_NAME

# AWS Configuration - kept for backward compatibility but should use aws_config values
AWS_ACCESS_KEY = '<YOUR_AWS_ACCESS_KEY>'
AWS_SECRET_KEY = '<YOUR_AWS_SECRET_KEY>'
AWS_REGION = '<YOUR_AWS_REGION>'
TABLE_NAME = '<YOUR_TABLE_NAME>'
# Check if the table exists in the AWS config

# Use the existing table if already initialized through aws_config
if not user_table:
    # Initialize AWS resources (fallback if aws_config failed)
    try:
        if not dynamodb:
            dynamodb = boto3.resource(
                'dynamodb',
                region_name=AWS_REGION,
                aws_access_key_id=AWS_ACCESS_KEY,
                aws_secret_access_key=AWS_SECRET_KEY
            )
        
        # Check if table exists, if not create it
        if not table_exists(dynamodb, TABLE_NAME):
            try:
                table = dynamodb.create_table(
                    TableName=TABLE_NAME,
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
                table.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)
                print(f"Table {TABLE_NAME} created successfully.")
            except Exception as create_error:
                print(f"Error creating table: {str(create_error)}")
    except Exception as aws_error:
        print(f"AWS initialization error: {str(aws_error)}")
else:
    # Use the table from aws_config
    table = user_table

# Create Blueprint
auth_bp = Blueprint('auth', __name__)

# Route for login page
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not table_exists(dynamodb, TABLE_NAME):
            flash('Database not available, please try again later', 'error')
            return render_template('login.html')
        
        try:
            # Query DynamoDB to find user with provided email
            response = user_table.query(
                KeyConditionExpression=Key('email').eq(email)
            )
            
            users = response.get('Items', [])
            
            if not users:
                flash('No account found with this email', 'error')
                return redirect(url_for('auth.login'))
            
            user = users[0]
            
            # Verify password
            if check_password_hash(user.get('password_hash', ''), password):
                # Save user info in session
                session['user_email'] = user['email']
                session['user_id'] = user['user_id']
                session['user_name'] = user.get('name', 'User')
                
                # Log successful login to blockchain
                try:
                    blockchain_logger.log_user_action(
                        user_id=user['user_id'],
                        action_type=BlockchainLogger.USER_LOGIN, 
                        user_email=email,
                        metadata={'timestamp': datetime.now().isoformat()}
                    )
                except Exception as log_error:
                    print(f"Error logging to blockchain: {str(log_error)}")
                    # Continue even if blockchain logging fails
                
                flash('Logged in successfully!', 'success')
                return redirect(url_for('user.dashboard'))
            else:
                flash('Incorrect password', 'error')
        except Exception as e:
            flash(f'Error during login: {str(e)}', 'error')
    
    return render_template('login.html')

# Route for signup page
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone', '')
        
        if not table_exists(dynamodb, TABLE_NAME):
            flash('Database not available, please try again later', 'error')
            return render_template('signup.html')
            
        try:
            # Check if user already exists
            response = user_table.query(
                KeyConditionExpression=Key('email').eq(email)
            )
            
            if response.get('Items', []):
                flash('An account with this email already exists', 'error')
                return redirect(url_for('auth.signup'))
            
            # Get the next user_id
            user_id = '1'  # Default to 1
            
            try:
                # Scan for all users to find max ID
                scan_response = user_table.scan(
                    ProjectionExpression="user_id"
                )
                
                # Extract user_ids that are numeric
                user_ids = []
                for item in scan_response.get('Items', []):
                    try:
                        user_ids.append(int(item.get('user_id', '0')))
                    except:
                        pass
                
                # Find max and increment
                if user_ids:
                    user_id = str(max(user_ids) + 1)
            except Exception as scan_error:
                print(f"Error scanning for user IDs: {str(scan_error)}")
                # If scan fails, generate a unique ID
                user_id = str(uuid.uuid4())[:8]
            
            # Hash the password
            password_hash = generate_password_hash(password)
            
            # Create user in DynamoDB
            user_table.put_item(
                Item={
                    'email': email,
                    'user_id': user_id,
                    'name': name,
                    'phone': phone,
                    'password_hash': password_hash
                }
            )
            
            # Log the user in by saving to session
            session['user_email'] = email
            session['user_id'] = user_id
            session['user_name'] = name
            
            flash('Account created successfully!', 'success')
            return redirect(url_for('user.dashboard'))
        except Exception as e:
            flash(f'Error creating account: {str(e)}', 'error')
    
    return render_template('signup.html')

# Route for logout
@auth_bp.route('/logout')
def logout():
    # Log logout to blockchain if user was logged in
    if 'user_email' in session and 'user_id' in session:
        try:
            blockchain_logger.log_user_action(
                user_id=session['user_id'],
                action_type=BlockchainLogger.USER_LOGOUT,
                user_email=session['user_email'],
                metadata={'timestamp': datetime.now().isoformat()}
            )
        except Exception as log_error:
            print(f"Error logging to blockchain: {str(log_error)}")
            # Continue even if blockchain logging fails
    
    # Clear session
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('auth.login'))