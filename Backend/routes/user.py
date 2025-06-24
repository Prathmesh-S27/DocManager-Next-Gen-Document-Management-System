from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime
import uuid
from functools import wraps  # For login_required decorator

# AWS Configuration
AWS_ACCESS_KEY = '<YOUR_AWS_ACCESS_KEY>'
AWS_SECRET_KEY = '<YOUR_AWS_SECRET'
AWS_REGION = '<YOUR_AWS_REGION>'
TABLE_NAME = '<YOUR_TABLE_NAME>'  # User table
DOCS_TABLE_NAME = '<YOUR_DOCS_TABLE_NAME>'  # New documents table

# Initialize AWS resources
try:
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    
    # Initialize user_table (renamed from 'table' to 'user_table' for consistency)
    user_table = dynamodb.Table(TABLE_NAME)
    
    # Initialize docs_table
    docs_table = dynamodb.Table(DOCS_TABLE_NAME)
    
    print("Successfully connected to user and document tables")
except Exception as e:
    print(f"Error connecting to DynamoDB: {str(e)}")
    user_table = None
    docs_table = None

# Create Blueprint for user-specific routes
user_bp = Blueprint('user', __name__)

# Login required decorator (instead of flask_login)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# User dashboard route - COMBINED VERSION
@user_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard showing documents and stats"""
    if not user_table or not docs_table:
        flash('User service is temporarily unavailable', 'error')
        return render_template('dashboard.html', user=None, documents=[], counts={})
    
    # Get user email from session
    email = session.get('user_email')
    
    try:
        # Get user data
        user_response = user_table.query(
            KeyConditionExpression=Key('email').eq(email)
        )
        user = user_response.get('Items', [])[0] if user_response.get('Items') else None
        
        # Get user documents from Documents table using GSI
        docs_response = docs_table.query(
            IndexName='EmailIndex',
            KeyConditionExpression=Key('email').eq(email)
        )
        documents = docs_response.get('Items', [])
        
        # Ensure all documents have the required fields with default values if missing
        for doc in documents:
            if 'upload_date' not in doc:
                doc['upload_date'] = "Unknown"
            if 'document_type' not in doc:
                doc['document_type'] = "unknown"
            if 'document_name' not in doc:
                doc['document_name'] = "Unnamed Document"
            if 'document_url' not in doc:
                doc['document_url'] = "#"
            
            # Convert dates to user-friendly format if needed
            if isinstance(doc.get('upload_date'), str) and 'T' in doc['upload_date']:
                # Keep the format but don't change the original
                doc['formatted_date'] = doc['upload_date'].split('T')[0]
            else:
                doc['formatted_date'] = str(doc.get('upload_date', 'Unknown'))
                
        # Count documents by type
        doc_types = {}
        for doc in documents:
            doc_type = doc.get('document_type', 'unknown').lower()
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
        # Recent documents - sort by upload date if available
        recent_docs = sorted(
            documents, 
            key=lambda x: x.get('upload_date', ''), 
            reverse=True
        )[:5]  # Get 5 most recent
        
        # Extract some stats for the dashboard
        document_count = len(documents)
        recent_uploads = sum(1 for doc in documents 
                            if doc.get('upload_date', '') != ''
                            and isinstance(doc.get('upload_date'), str)
                            and doc.get('upload_date', '').startswith(datetime.now().strftime('%Y-%m')))
        
        return render_template('dashboard.html',
                              user=user,
                              documents=recent_docs,
                              all_documents=documents,
                              counts=doc_types,
                              document_count=document_count,
                              recent_uploads=recent_uploads)
    
    except Exception as e:
        print(f"Error loading dashboard: {str(e)}")
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html', user=None, documents=[], counts={})

# User profile route with enhanced debugging
@user_bp.route('/profile')
@login_required
def profile():
    email = session.get('user_email')
    user_id = session.get('user_id')
    
    print(f"DEBUG - Loading profile for {email}, ID: {user_id}")
    
    try:
        # Use user_table instead of table
        response = user_table.get_item(
            Key={
                'email': email,
                'user_id': user_id
            }
        )
        
        user_info = response.get('Item', {})
        print(f"DEBUG - User data retrieved: {user_info}")
        
        # Convert DynamoDB nested objects to simple Python types
        # This prevents recursion in complex objects
        sanitized_user = {}
        for key, value in user_info.items():
            # Skip complex nested objects that might cause recursion
            if isinstance(value, (str, int, float, bool, list, dict)):
                # For dictionaries, convert to string to avoid recursion
                if isinstance(value, dict):
                    sanitized_user[key] = str(value)
                else:
                    sanitized_user[key] = value
            else:
                # Convert other types to string
                sanitized_user[key] = str(value)
        
        # If no user data is found, create a minimal user object
        if not sanitized_user:
            print(f"DEBUG - No user data found for {email}")
            sanitized_user = {
                'email': email,
                'user_id': user_id,
                'name': 'User',
                'phone': None,
                'created_at': None,
                'last_login': None
            }
            
        return render_template('profile.html', user=sanitized_user)
    except Exception as e:
        print(f"DEBUG - Error retrieving profile: {str(e)}")
        flash(f'Error retrieving profile: {str(e)}', 'error')
        return redirect(url_for('user.dashboard'))
# Update user profile
@user_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    email = session['user_email']
    user_id = session['user_id']
    
    # Get form data
    name = request.form.get('name')
    phone = request.form.get('phone', '')
    
    # Update user info in DynamoDB
    try:
        # Use user_table instead of table
        user_table.update_item(
            Key={
                'email': email,
                'user_id': user_id
            },
            UpdateExpression='SET #name = :name, phone = :phone',
            ExpressionAttributeNames={
                '#name': 'name'
            },
            ExpressionAttributeValues={
                ':name': name,
                ':phone': phone
            }
        )
        flash('Profile updated successfully', 'success')
    except Exception as e:
        flash(f'Error updating profile: {str(e)}', 'error')
    
    return redirect(url_for('user.profile'))

# Route to view a specific document (legacy route)
@user_bp.route('/document/<document_id>')
@login_required
def view_document(document_id):
    # Just redirect to the new view route
    return redirect(url_for('view.view_document', document_id=document_id))

# Route to upload a new document
@user_bp.route('/upload-document', methods=['GET'])
@login_required
def upload_document():
    return render_template('upload_document.html')

# Change Password
@user_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    email = session['user_email']
    user_id = session['user_id']
    
    # Get form data
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Verify passwords match
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('user.profile'))
    
    # Get current user from database
    try:
        # Use user_table instead of table
        response = user_table.get_item(
            Key={
                'email': email,
                'user_id': user_id
            }
        )
        
        user = response.get('Item', None)
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('user.profile'))
            
        # Verify current password
        import bcrypt
        stored_password = user.get('password', '').encode('utf-8')
        
        if not bcrypt.checkpw(current_password.encode('utf-8'), stored_password):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('user.profile'))
            
        # Hash new password
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # Update password in database
        user_table.update_item(
            Key={
                'email': email,
                'user_id': user_id
            },
            UpdateExpression='SET password = :password',
            ExpressionAttributeValues={
                ':password': hashed_password.decode('utf-8')
            }
        )
        
        flash('Password updated successfully', 'success')
        
    except Exception as e:
        flash(f'Error updating password: {str(e)}', 'error')
    
    return redirect(url_for('user.profile'))