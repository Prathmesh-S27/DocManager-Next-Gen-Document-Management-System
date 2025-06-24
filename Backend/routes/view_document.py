from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort, send_file
import boto3
from boto3.dynamodb.conditions import Key, Attr
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import threading
from functools import wraps
from utils.encryption import encryption_service
import io
from blockchain.blockchain_logger import blockchain_logger, BlockchainLogger
from utils.merkle_tree import document_merkle_tree
from utils.aws_config import s3, docs_table, BUCKET_NAME  # Use centralized AWS config

# AWS Configuration
AWS_ACCESS_KEY = '<YOUR_AWS_ACCESS_KEY>'
AWS_SECRET_KEY = '<YOUR_AWS_SECRET_KEY>'
AWS_REGION = '<YOUR_AWS_REGION>'
BUCKET_NAME = '<YOUR_BUCKET_NAME>'
DOCS_TABLE_NAME = '<YOUR_DOCS_TABLE_NAME>'

# Initialize AWS resources with error handling
try:
    s3 = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
except Exception as e:
    print(f"Error initializing S3: {str(e)}")
    s3 = None

# Initialize DynamoDB client
try:
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    
    # Get or create documents table
    try:
        docs_table = dynamodb.Table(DOCS_TABLE_NAME)
        docs_table.table_status
        print(f"Successfully connected to DynamoDB table: {DOCS_TABLE_NAME}")
    except Exception as e:
        print(f"Error accessing documents table: {str(e)}")
        docs_table = None
        
except Exception as e:
    print(f"DynamoDB error: {str(e)}")
    docs_table = None

# Create Blueprint
view_bp = Blueprint('view', __name__)

# Helper function to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Create blueprint
view_bp = Blueprint('view', __name__)
# Helper function to format document for display
# Update the format_document helper function
def format_document(doc):
    """Format document data for templates with better error handling"""
    if not doc:
        return {
            'document_id': '',
            'document_name': 'Unknown Document',
            'document_url': '#',
            'document_type': 'unknown',
            'upload_date': 'Unknown',
            'formatted_date': 'Unknown',
            'file_size': 0,
            'file_size_formatted': '0 KB'
        }
    
    # Ensure all required fields exist with defaults
    formatted = {
        'document_id': doc.get('document_id', ''),
        'document_name': doc.get('document_name', 'Unnamed Document'),
        'document_description': doc.get('document_description', ''),
        'document_url': doc.get('document_url', '#'),
        'document_type': doc.get('document_type', 'unknown'),
        'upload_date': doc.get('upload_date', 'Unknown'),
        'category': doc.get('category', 'Uncategorized'),
        'tags': doc.get('tags', ''),
        'user_id': doc.get('user_id', ''),
        'email': doc.get('email', ''),
        's3_key': doc.get('s3_key', ''),
        'ai_summary': doc.get('ai_summary', ''),
        'ai_topics': doc.get('ai_topics', []),
        'keyword_list': doc.get('keyword_list', []),
        'text_content': doc.get('text_content', '')
    }
    
    # Format date if available
    if isinstance(formatted['upload_date'], str) and 'T' in formatted['upload_date']:
        formatted['formatted_date'] = formatted['upload_date'].split('T')[0]
    else:
        formatted['formatted_date'] = str(formatted['upload_date'])
    
    # Format file size if available
    try:
        file_size = int(doc.get('file_size', 0))
        if file_size > 1048576:  # 1MB
            formatted['file_size_formatted'] = f"{file_size/1048576:.1f} MB"
        else:
            formatted['file_size_formatted'] = f"{file_size/1024:.1f} KB"
        formatted['file_size'] = file_size
    except (ValueError, TypeError):
        formatted['file_size'] = 0
        formatted['file_size_formatted'] = 'Unknown size'
    
    return formatted 

# View all documents
# Update the all_documents view to format documents
@view_bp.route('/documents')
@login_required
def all_documents():
    """View all user documents with filters and search"""
    if docs_table is None:
        flash('Document service is temporarily unavailable', 'error')
        return render_template('all_documents.html', documents=[], categories=[], doc_types=[])
    
    # Get user email from session
    email = session.get('user_email')
    
    try:
        # Get documents for this user using the GSI
        response = docs_table.query(
            IndexName='EmailIndex',
            KeyConditionExpression=Key('email').eq(email)
        )
        
        # Get search/filter parameters
        search_query = request.args.get('q', '')
        category_filter = request.args.get('category', '')
        type_filter = request.args.get('type', '')
        keyword_filter = request.args.get('keyword', '')
        sort_by = request.args.get('sort_by', 'upload_date')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Get all unique document categories and types for filtering
        categories = set()
        doc_types = set()
        
        # Initialize documents list
        all_documents = []
        
        # Filter out keyword entries that might be in results
        for doc in response.get('Items', []):
            if 'original_document_id' in doc:
                continue
                
            # Add to category and type sets for filter dropdowns
            if 'category' in doc and doc['category']:
                categories.add(doc['category'])
            
            if 'document_type' in doc and doc['document_type']:
                doc_types.add(doc['document_type'])
            
            # Format document and add to list
            formatted_doc = format_document(doc)
            all_documents.append(formatted_doc)
        
        # If keyword filter is active, use the keyword index
        if keyword_filter:
            # Get documents with this keyword
            documents = []
            for doc in all_documents:
        # Check if document has keyword_list and the keyword is in it
               if 'keyword_list' in doc and keyword_filter.lower() in [k.lower() for k in doc.get('keyword_list', [])]:
                   documents.append(doc)
            # Get the original document IDs
            
            # Filter the documents to only those with matching IDs
        else:
            documents = all_documents
            
        # Apply category filter if specified
        if category_filter:
            documents = [doc for doc in documents if doc.get('category') == category_filter]
            
        # Apply document type filter if specified
        if type_filter:
            documents = [doc for doc in documents if doc.get('document_type') == type_filter]
            
        # Apply text search if specified
        if search_query:
            search_terms = search_query.lower().split()
            filtered_docs = []
            
            for doc in documents:
                doc_text = (
                    (doc.get('document_name', '') or '').lower() + ' ' +
                    (doc.get('document_description', '') or '').lower() + ' ' +
                    (doc.get('text_content', '') or '').lower()
                )
                
                # Check if all search terms are in the document text
                if all(term in doc_text for term in search_terms):
                    filtered_docs.append(doc)
                    
            documents = filtered_docs
            
        # Sort documents
        reverse_sort = sort_order.lower() == 'desc'
        
        if sort_by == 'document_name':
            documents = sorted(documents, key=lambda x: x.get('document_name', '').lower(), reverse=reverse_sort)
        elif sort_by == 'document_type':
            documents = sorted(documents, key=lambda x: x.get('document_type', '').lower(), reverse=reverse_sort)
        else:  # Default to upload_date
            documents = sorted(documents, key=lambda x: x.get('upload_date', ''), reverse=reverse_sort)
        
        return render_template('all_documents.html', 
                              documents=documents,
                              categories=sorted(list(categories)),
                              doc_types=sorted(list(doc_types)),
                              search_query=search_query,
                              category_filter=category_filter,
                              type_filter=type_filter,
                              keyword_filter=keyword_filter,
                              sort_by=sort_by,
                              sort_order=sort_order,
                              doc_count=len(documents))
        
    except Exception as e:
        print(f"Error loading documents: {str(e)}")
        flash(f'Error loading documents: {str(e)}', 'error')
        return render_template('all_documents.html', documents=[], categories=[], doc_types=[])

# View a single document
@view_bp.route('/document/<document_id>')
@login_required
def view_document(document_id):
    """Show details for a specific document"""
    if docs_table is None:
        flash('Document service is temporarily unavailable', 'error')
        return redirect(url_for('user.dashboard'))
    
    try:
        # Get document by ID
        response = docs_table.get_item(
            Key={
                'document_id': document_id
            }
        )
        
        if 'Item' not in response:
            flash('Document not found', 'error')
            return redirect(url_for('view.all_documents'))
            
        document = response['Item']
        
        # Verify ownership
        if document.get('email') != session['user_email']:
            flash('Access denied', 'error')
            return redirect(url_for('view.all_documents'))
            
        # Format document for display
        formatted_document = format_document(document)
        
        # Create direct content URL for viewing
        content_url = url_for('view.view_document_content', document_id=document_id)
        formatted_document['content_url'] = content_url
        
        # Get related documents (same category or type)
        related_documents = []
        try:
            category = document.get('category')
            doc_type = document.get('document_type')
            
            if category or doc_type:
                # Query using the GSI
                response = docs_table.query(
                    IndexName='EmailIndex',
                    KeyConditionExpression=Key('email').eq(session['user_email'])
                )
                
                all_user_docs = response.get('Items', [])
                
                # Filter for related documents
                for doc in all_user_docs:
                    if doc['document_id'] != document_id:  # Skip current document
                        if (category and doc.get('category') == category) or \
                           (doc_type and doc.get('document_type') == doc_type):
                            related_documents.append(format_document(doc))
                            if len(related_documents) >= 4:  # Limit to 4 related docs
                                break
                                
        except Exception as e:
            print(f"Error getting related documents: {str(e)}")
        
        return render_template('view_document.html', 
                               document=formatted_document, 
                               related_documents=related_documents)
    
    except Exception as e:
        flash(f'Error retrieving document: {str(e)}', 'error')
        return redirect(url_for('view.all_documents'))

@view_bp.route('/document/<document_id>/content')
@login_required
def view_document_content(document_id):
    """View the actual document content"""
    if docs_table is None:
        flash('Document service is temporarily unavailable', 'error')
        return redirect(url_for('user.dashboard'))
    
    try:
        # Get document by ID
        response = docs_table.get_item(
            Key={
                'document_id': document_id
            }
        )
        
        if 'Item' not in response:
            flash('Document not found', 'error')
            return redirect(url_for('view.all_documents'))
            
        document = response['Item']
        
        # Verify ownership
        if document.get('email') != session['user_email']:
            flash('Access denied', 'error')
            return redirect(url_for('view.all_documents'))
        
        # Log document view/download to blockchain (non-blocking)
        try:
            # Store needed values from session before starting thread
            user_email = session.get('user_email')
            
            # Use a thread to prevent blocking
            def log_to_blockchain(doc_id, user_email):
                try:
                    blockchain_logger.log_document_action(
                        document_id=doc_id,
                        action_type=BlockchainLogger.ACTION_DOWNLOAD,
                        user_email=user_email,
                        metadata={'timestamp': datetime.now().isoformat()}
                    )
                except Exception as e:
                    print(f"Background blockchain logging error: {str(e)}")
                    
            # Pass the values as parameters instead of accessing session in the thread
            log_thread = threading.Thread(
                target=log_to_blockchain,
                args=(document_id, user_email)
            )
            log_thread.daemon = True
            log_thread.start()
        except Exception as e:
            print(f"Error setting up blockchain logging thread: {str(e)}")
        
        try:
            # Get encrypted content from S3
            s3_key = document.get('s3_key')
            if not s3_key:
                flash('Document content not available', 'error')
                return redirect(url_for('view.view_document', document_id=document_id))
            
            s3_response = s3.get_object(
                Bucket=BUCKET_NAME,
                Key=s3_key
            )
            encrypted_data = s3_response['Body'].read()
            
            # Improved decryption with detailed error handling
            try:
                encryption_key_id = document.get('encryption_key_id')
                if not encryption_key_id:
                    print(f"Warning: No encryption_key_id found for document {document_id}, attempting default decryption")
                
                # Try to decrypt with encryption_key_id if available
                decrypted_data = encryption_service.decrypt_file(
                    encrypted_data, 
                    key_id=encryption_key_id if encryption_key_id else None
                )
            except Exception as decrypt_error:
                print(f"Decryption error: {str(decrypt_error)}")
                print(f"Document: {document_id}, Key ID: {document.get('encryption_key_id', 'None')}")
                
                # Fallback approach: try without specific key ID
                try:
                    decrypted_data = encryption_service.decrypt_file(encrypted_data, key_id=None)
                    print("Fallback decryption succeeded using default key")
                except Exception as fallback_error:
                    print(f"Fallback decryption also failed: {str(fallback_error)}")
                    # Last resort: return encrypted data with warning
                    flash("Warning: Document could not be decrypted. Displaying raw content.", 'warning')
                    decrypted_data = encrypted_data
            
            # Create file-like object from decrypted data
            file_stream = io.BytesIO(decrypted_data)
            file_stream.seek(0)  # Important: Reset pointer to beginning of file
            
            # Get content type
            content_type = document.get('content_type')
            if not content_type:
                # Try to infer content type from file extension
                document_type = document.get('document_type', '').lower()
                if document_type == 'pdf':
                    content_type = 'application/pdf'
                elif document_type in ['doc', 'docx']:
                    content_type = 'application/msword'
                elif document_type in ['xls', 'xlsx']:
                    content_type = 'application/vnd.ms-excel'
                elif document_type in ['ppt', 'pptx']:
                    content_type = 'application/vnd.ms-powerpoint'
                elif document_type in ['jpg', 'jpeg']:
                    content_type = 'image/jpeg'
                elif document_type == 'png':
                    content_type = 'image/png'
                elif document_type == 'txt':
                    content_type = 'text/plain'
                else:
                    content_type = 'application/octet-stream'
            
            # Set download or inline disposition
            disposition = 'attachment' if request.args.get('download', 'false').lower() == 'true' else 'inline'
            
            # Return decrypted content with proper headers
            response = send_file(
                file_stream,
                mimetype=content_type,
                download_name=document.get('filename', document.get('document_name', 'document')),
                as_attachment=request.args.get('download', 'false').lower() == 'true',
                max_age=300,  # Cache for 5 minutes
                conditional=True
            )
            
            # Add additional headers for better browser handling
            response.headers['Content-Disposition'] = f'{disposition}; filename="{document.get("filename", document.get("document_name", "document"))}"'
            response.headers['Content-Type'] = content_type
            response.headers['X-Content-Type-Options'] = 'nosniff'
            
            return response
        except Exception as e:
            print(f"Error sending document: {str(e)}")
            flash(f'Error viewing document: {str(e)}', 'error')
            return redirect(url_for('view.view_document', document_id=document_id))
    
    except Exception as e:
        flash(f'Error retrieving document: {str(e)}', 'error')
        return redirect(url_for('view.all_documents'))

# Edit document
@view_bp.route('/document/<document_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_document(document_id):
    """Edit document metadata"""
    if docs_table is None:
        flash('Document service is temporarily unavailable', 'error')
        return redirect(url_for('view.all_documents'))
    
    # Handle GET request - show the edit form
    if request.method == 'GET':
        try:
            # Get document by ID
            response = docs_table.get_item(
                Key={
                    'document_id': document_id
                }
            )
            
            if 'Item' not in response:
                flash('Document not found', 'error')
                return redirect(url_for('view.all_documents'))
                
            document = response['Item']
            
            # Verify ownership
            if document.get('email') != session['user_email']:
                flash('Access denied', 'error')
                return redirect(url_for('view.all_documents'))
            
            return render_template('edit_document.html', document=document)
        
        except Exception as e:
            flash(f'Error retrieving document: {str(e)}', 'error')
            return redirect(url_for('view.all_documents'))
    
    # Handle POST request - update the document
    else:
        try:
            # First verify document exists and belongs to user
            response = docs_table.get_item(
                Key={
                    'document_id': document_id
                }
            )
            
            if 'Item' not in response:
                flash('Document not found', 'error')
                return redirect(url_for('view.all_documents'))
                
            document = response['Item']
            
            # Verify ownership
            if document.get('email') != session['user_email']:
                flash('Access denied', 'error')
                return redirect(url_for('view.all_documents'))
            
            # Get form data
            document_name = request.form.get('document_name')
            document_description = request.form.get('document_description', '')
            category = request.form.get('category', '')
            tags = request.form.get('tags', '')
            
            # Update DynamoDB record
            update_expression = "SET document_name = :name, document_description = :desc"
            expression_values = {
                ':name': document_name,
                ':desc': document_description
            }
            
            if category:
                update_expression += ", category = :cat"
                expression_values[':cat'] = category
                
            if tags:
                update_expression += ", tags = :tags"
                expression_values[':tags'] = tags
            
            docs_table.update_item(
                Key={
                    'document_id': document_id
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            flash('Document updated successfully', 'success')
            return redirect(url_for('view.view_document', document_id=document_id))
            
        except Exception as e:
            flash(f'Error updating document: {str(e)}', 'error')
            return redirect(url_for('view.edit_document', document_id=document_id))

# API endpoints for AJAX operations
@view_bp.route('/api/documents')
def get_documents_json():
    """Get documents as JSON for AJAX requests"""
    if 'user_email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if docs_table is None:
        return jsonify({'error': 'Service unavailable'}), 503
    
    try:
        # Query using the GSI
        response = docs_table.query(
            IndexName='EmailIndex',
            KeyConditionExpression=Key('email').eq(session['user_email'])
        )
        
        documents = response.get('Items', [])
        
        # Convert to JSON-serializable format
        documents = json.loads(json.dumps(documents, default=str))
        
        return jsonify({
            'success': True,
            'count': len(documents),
            'documents': documents
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add a new route for keyword searching
@view_bp.route('/search')
@login_required
def search_documents():
    """Search documents by keyword"""
    if docs_table is None:
        flash('Document service is temporarily unavailable', 'error')
        return render_template('all_documents.html', documents=[], categories=[])
    
    # Get search parameters
    keyword = request.args.get('keyword', '').lower().strip()
    
    # If no keyword provided, redirect to all documents
    if not keyword:
        return redirect(url_for('view.all_documents'))
    
    try:
        matching_documents = []
        
        # First, try to find documents by keyword using the KeywordIndex
        try:
            keyword_response = docs_table.query(
                IndexName='KeywordIndex',
                KeyConditionExpression=Key('keyword').eq(keyword)
            )
            
            # Get the original document IDs from the keyword items
            original_doc_ids = set()
            for item in keyword_response.get('Items', []):
                if item.get('original_document_id'):
                    original_doc_ids.add(item.get('original_document_id'))
                    
            # Get full document details for each original document ID
            for doc_id in original_doc_ids:
                doc_response = docs_table.get_item(
                    Key={'document_id': doc_id}
                )
                
                if 'Item' in doc_response:
                    # Only add if it belongs to the current user
                    if doc_response['Item'].get('email') == session['user_email']:
                        matching_documents.append(doc_response['Item'])
        except Exception as e:
            print(f"Error searching by keyword index: {str(e)}")
        
        # If no documents found by keyword index, try searching through all user documents
        if not matching_documents:
            # Get all user documents
            response = docs_table.query(
                IndexName='EmailIndex',
                KeyConditionExpression=Key('email').eq(session['user_email'])
            )
            
            all_docs = response.get('Items', [])
            
            # Search through document content, names, descriptions, etc.
            for doc in all_docs:
                # Check document name
                if keyword in doc.get('document_name', '').lower():
                    matching_documents.append(doc)
                    continue
                    
                # Check document description
                if keyword in doc.get('document_description', '').lower():
                    matching_documents.append(doc)
                    continue
                    
                # Check keywords list
                if 'keyword_list' in doc:
                    keywords = [k.lower() for k in doc.get('keyword_list', [])]
                    if keyword in keywords:
                        matching_documents.append(doc)
                        continue
                        
                # Check tags
                if keyword in doc.get('tags', '').lower():
                    matching_documents.append(doc)
                    continue
                    
                # Check text content (limited)
                if 'text_content' in doc and keyword in doc.get('text_content', '').lower():
                    matching_documents.append(doc)
                    continue
        
        # Format documents for display
        formatted_documents = [format_document(doc) for doc in matching_documents]
        
        # Return search results (reusing all_documents template with search context)
        return render_template('all_documents.html', 
                              documents=formatted_documents,
                              categories=[],
                              doc_types=[],
                              search_term=keyword,
                              is_keyword_search=True)
        
    except Exception as e:
        flash(f'Error searching documents: {str(e)}', 'error')
        return render_template('all_documents.html', documents=[], categories=[])

# Add at the bottom of the file
# Add this route (or update if it exists)
@view_bp.route('/document/<document_id>/versions')
@login_required
def document_versions(document_id):
    """Show version history for a document"""
    if docs_table is None:
        flash('Document service is temporarily unavailable', 'error')
        return redirect(url_for('user.dashboard'))
    
    try:
        # Get document by ID
        response = docs_table.get_item(
            Key={
                'document_id': document_id
            }
        )
        
        if 'Item' not in response:
            flash('Document not found', 'error')
            return redirect(url_for('view.all_documents'))
            
        document = response['Item']
        
        # Verify ownership
        if document.get('email') != session['user_email']:
            flash('Access denied', 'error')
            return redirect(url_for('view.all_documents'))
        
        # Format document for display
        formatted_document = format_document(document)
        
        # Get version history
        versions = document.get('versions', [])
        
        # Add current version to the list
        current_version = {
            'version_id': 'current',
            'upload_date': document.get('upload_date'),
            'file_size': document.get('file_size'),
            'filename': document.get('filename'),
            's3_key': document.get('s3_key'),
            'document_url': document.get('document_url'),
            'is_current': True
        }
        
        # Format dates for all versions
        for version in versions:
            if isinstance(version.get('upload_date'), str) and 'T' in version['upload_date']:
                version['formatted_date'] = version['upload_date'].split('T')[0]
                version['formatted_time'] = version['upload_date'].split('T')[1][:8]
            else:
                version['formatted_date'] = str(version.get('upload_date', 'Unknown'))
                version['formatted_time'] = ''
            
            # Format file size
            try:
                file_size = int(version.get('file_size', 0))
                if file_size > 1048576:  # 1MB
                    version['formatted_size'] = f"{file_size/1048576:.1f} MB"
                else:
                    version['formatted_size'] = f"{file_size/1024:.1f} KB"
            except (ValueError, TypeError):
                version['formatted_size'] = 'Unknown size'
        
        # Sort versions by date (newest first)
        versions = sorted(versions, key=lambda x: x.get('upload_date', ''), reverse=True)
        
        # Add the current version at the top
        all_versions = [current_version] + versions
        
        return render_template('document_versions.html', 
                              document=formatted_document, 
                              versions=all_versions)
    
    except Exception as e:
        flash(f'Error retrieving document versions: {str(e)}', 'error')
        return redirect(url_for('view.view_document', document_id=document_id))

@view_bp.route('/api/document/<document_id>')
def get_document_json(document_id):
    """Get a specific document as JSON"""
    if 'user_email' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if docs_table is None:
        return jsonify({'error': 'Service unavailable'}), 503
    
    try:
        response = docs_table.get_item(
            Key={
                'document_id': document_id
            }
        )
        
        if 'Item' not in response:
            return jsonify({'error': 'Document not found'}), 404
            
        document = response['Item']
        
        # Verify ownership
        if document.get('email') != session['user_email']:
            return jsonify({'error': 'Access denied'}), 403
            
        # Convert to JSON-serializable format
        document = json.loads(json.dumps(document, default=str))
        
        return jsonify({
            'success': True,
            'document': document
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500