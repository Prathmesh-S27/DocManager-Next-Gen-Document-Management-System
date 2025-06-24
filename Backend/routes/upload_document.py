from flask import Blueprint, request, jsonify, session, redirect, url_for, flash
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from functools import wraps
from utils.document_processor import process_document
import io
import hashlib

# Import our new security modules
from utils.encryption import encryption_service
from utils.bloom_filter import keyword_filter
from utils.keyword_matching import keyword_matcher
from utils.merkle_tree import document_merkle_tree
from blockchain.blockchain_logger import blockchain_logger, BlockchainLogger
from utils.aws_config import s3, docs_table, BUCKET_NAME  # Use centralized AWS config
from utils.text_processing import extract_keywords, clean_text

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Create Blueprint
upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'csv', 'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def update_document_with_blockchain_data(document_id, file_data, blockchain_result, root_hash):
    """Helper function to consistently update documents with blockchain data"""
    update_values = {}
    update_expression_parts = []
    
    # Always store the document hash
    document_hash = hashlib.sha256(file_data).hexdigest()
    update_values[':dh'] = document_hash
    update_expression_parts.append("document_hash = :dh")
    
    # Add Merkle root
    update_values[':mr'] = root_hash
    update_expression_parts.append("merkle_root_at_upload = :mr")
    
    # Add blockchain verification flag
    if blockchain_result and blockchain_result.get('success'):
        update_values[':tx'] = blockchain_result.get('tx_hash')
        update_values[':bn'] = blockchain_result.get('block_number')
        update_values[':bv'] = True
        
        update_expression_parts.extend([
            "blockchain_tx_hash = :tx",
            "blockchain_block_number = :bn",
            "blockchain_verification = :bv"
        ])
    else:
        update_values[':bv'] = False
        update_expression_parts.append("blockchain_verification = :bv")
    
    # Construct the final update expression
    update_expression = "set " + ", ".join(update_expression_parts)
    
    # Update the document
    docs_table.update_item(
        Key={'document_id': document_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=update_values
    )
    
    print(f"Updated document {document_id} with blockchain data")
    return document_hash

@upload_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if s3 is None or docs_table is None:
        flash('Document upload service is temporarily unavailable', 'error')
        return redirect(url_for('user.upload_document'))

    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('user.upload_document'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('user.upload_document'))
    
    document_name = request.form.get('document_name', 'Untitled Document')
    document_description = request.form.get('document_description', '')
    tags = request.form.get('tags', '')
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        document_id = str(uuid.uuid4())
        s3_key = f"documents/{session['user_email']}/{document_id}/{filename}"
        
        try:
            file_data = file.read()
            file_size = len(file_data)
            
            encrypted_data, encryption_key_id = encryption_service.encrypt_file(file_data)
            s3_file = io.BytesIO(encrypted_data)
            
            s3.upload_fileobj(
                s3_file,
                BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'ContentType': file.content_type,
                    'ACL': 'public-read'
                }
            )
            
            s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            
            process_file = io.BytesIO(file_data)
            ai_result = None
            try:
                ai_result = process_document(process_file, file_extension)
                print(f"AI processing completed for {filename}")
            except Exception as e:
                print(f"Error processing document with AI: {str(e)}")
                ai_result = {
                    "summary": f"Error processing document: {str(e)}",
                    "keywords": [],
                    "topics": [],
                    "text_content": ""
                }
            
            extracted_text = ai_result.get('text_content', '') if ai_result else ''
            extracted_text = clean_text(extracted_text)
            
            keywords = extract_keywords(extracted_text)
            
            if keywords:
                try:
                    keyword_matcher.add_keywords(keywords)
                except Exception as e:
                    print(f"Error adding keywords to matcher: {str(e)}")
            
            summary = ai_result.get('summary', '') if ai_result else ''
            topics = ai_result.get('topics', []) if ai_result else []
            
            keyword_filter.add_document_keywords(document_id, keywords)
            
            timestamp = datetime.now().isoformat()
            
            item = {
                'document_id': document_id,
                'email': session['user_email'],
                'user_id': session['user_id'],
                'document_name': document_name,
                'document_description': document_description,
                'document_type': file_extension,
                'upload_date': timestamp,
                'document_url': s3_url,
                's3_key': s3_key,
                'file_size': file_size,
                'filename': filename,
                'ai_summary': summary,
                'ai_topics': topics,
                'text_content': extracted_text,
                'keyword_list': keywords,
                'encryption_key_id': encryption_key_id
            }
            
            if tags:
                item['tags'] = tags
            
            try:
                document_merkle_tree.add_document(document_id, {
                    'document_id': document_id, 
                    'document_name': document_name,
                    'document_type': file_extension,
                    'file_size': file_size,
                    'upload_date': timestamp
                })

                document_merkle_tree.rebuild_tree()
                root_hash = document_merkle_tree.get_root_hash()
                
                # Update the Merkle root in the blockchain and get transaction details
                blockchain_result = blockchain_logger.update_merkle_root(root_hash, async_mode=False)
                
                # Store blockchain transaction details with document
                document_hash = update_document_with_blockchain_data(document_id, file_data, blockchain_result, root_hash)
                
                # Add hash to the document metadata
                item['document_hash'] = document_hash
                
                docs_table.put_item(Item=item)
                print(f"Document metadata saved to DynamoDB: {document_id}")
                
                try:
                    # Add the hash to metadata too for redundancy
                    metadata = item.copy()
                    metadata['document_hash'] = document_hash
                    
                    blockchain_logger.log_document_action(
                        document_id=document_id,
                        action_type=BlockchainLogger.ACTION_UPLOAD,
                        user_email=session['user_email'],
                        document_data=file_data,  # Pass the raw file data for hashing
                        metadata=metadata
                    )
                    print(f"Document action logged to blockchain: {document_id}")
                except Exception as blockchain_error:
                    print(f"Blockchain logging error: {str(blockchain_error)}")
                    # Continue even if blockchain logging fails
                
                flash('Document uploaded successfully', 'success')
                return redirect(url_for('user.dashboard'))
                
            except Exception as db_error:
                print(f"Error saving document to DynamoDB: {str(db_error)}")
                flash(f'Error saving document metadata: {str(db_error)}', 'error')
                return redirect(url_for('user.upload_document'))
            
        except Exception as e:
            print(f"Error in upload: {str(e)}")
            flash(f'Error uploading document: {str(e)}', 'error')
            return redirect(url_for('user.upload_document'))
    
    flash('Invalid file type. Allowed types: pdf, doc, docx, txt, jpg, jpeg, png, csv, xls, xlsx', 'error')
    return redirect(url_for('user.upload_document'))

@upload_bp.route('/upload/multiple', methods=['POST'])
@login_required
def upload_multiple_files():
    if s3 is None or docs_table is None:
        flash('Document upload service is temporarily unavailable', 'error')
        return redirect(url_for('user.upload_document'))
    
    if 'files[]' not in request.files:
        flash('No files selected', 'error')
        return redirect(url_for('user.upload_document'))
    
    files = request.files.getlist('files[]')
    
    if not files or all(f.filename == '' for f in files):
        flash('No files selected', 'error')
        return redirect(url_for('user.upload_document'))
    
    document_category = request.form.get('document_category', 'Uncategorized')
    tags = request.form.get('tags', '')
    
    uploaded_files = []
    errors = []
    
    for file in files:
        if file.filename == '':
            continue
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_extension = filename.rsplit('.', 1)[1].lower()
            document_id = str(uuid.uuid4())
            s3_key = f"documents/{session['user_email']}/{document_id}/{filename}"
            
            try:
                file_data = file.read()
                file_size = len(file_data)
                encrypted_data, encryption_key_id = encryption_service.encrypt_file(file_data)
                s3_file = io.BytesIO(encrypted_data)
                
                s3.upload_fileobj(
                    s3_file,
                    BUCKET_NAME,
                    s3_key,
                    ExtraArgs={
                        'ContentType': file.content_type,
                        'ACL': 'public-read'
                    }
                )
                
                s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
                
                process_file = io.BytesIO(file_data)
                ai_result = process_document(process_file, file_extension)
                
                keywords = ai_result.get('keywords', [])
                summary = ai_result.get('summary', '')
                topics = ai_result.get('topics', [])
                text_content = ai_result.get('text_content', '')
                
                keyword_filter.add_document_keywords(document_id, keywords)
                keyword_matcher.add_document_keywords(document_id, keywords)
                
                timestamp = datetime.now().isoformat()
                
                item = {
                    'document_id': document_id,
                    'email': session['user_email'],
                    'user_id': session['user_id'],
                    'document_name': filename,
                    'document_description': f"Uploaded as part of {document_category} batch",
                    'document_type': file_extension,
                    'upload_date': timestamp,
                    'document_url': s3_url,
                    's3_key': s3_key,
                    'category': document_category,
                    'file_size': file_size,
                    'filename': filename,
                    'ai_summary': summary,
                    'ai_topics': topics,
                    'text_content': text_content,
                    'keyword_list': keywords,
                    'encryption_key_id': encryption_key_id
                }
                
                if tags:
                    item['tags'] = tags
                
                document_merkle_tree.add_document(document_id, {
                    'document_id': document_id, 
                    'document_name': filename,
                    'document_type': file_extension,
                    'file_size': file_size,
                    'upload_date': timestamp
                })

                document_merkle_tree.rebuild_tree()
                root_hash = document_merkle_tree.get_root_hash()
                
                # Update the Merkle root in the blockchain and get transaction details
                blockchain_result = blockchain_logger.update_merkle_root(root_hash, async_mode=False)
                
                # Store blockchain transaction details with document
                document_hash = update_document_with_blockchain_data(document_id, file_data, blockchain_result, root_hash)
                
                # Add hash to the document metadata
                item['document_hash'] = document_hash
                
                docs_table.put_item(Item=item)
                
                blockchain_logger.log_document_action(
                    document_id=document_id,
                    action_type=BlockchainLogger.ACTION_UPLOAD,
                    user_email=session['user_email'],
                    document_data=file_data,
                    metadata={'document_hash': document_hash}  # Include the hash in metadata
                )
                
                uploaded_files.append({
                    'filename': filename,
                    'document_id': document_id,
                    'url': s3_url
                })
                
            except Exception as e:
                print(f"Error uploading {filename}: {str(e)}")
                errors.append({
                    'filename': filename,
                    'error': str(e)
                })
        else:
            errors.append({
                'filename': file.filename,
                'error': 'Invalid file type'
            })
    
    if not errors:
        flash(f'Successfully uploaded {len(uploaded_files)} documents', 'success')
    else:
        if uploaded_files:
            flash(f'Uploaded {len(uploaded_files)} documents with {len(errors)} errors', 'warning')
        else:
            flash('Failed to upload documents', 'error')
    
    return redirect(url_for('user.dashboard'))

@upload_bp.route('/version/<document_id>', methods=['POST'])
@login_required
def upload_new_version(document_id):
    if s3 is None or docs_table is None:
        flash('Document upload service is temporarily unavailable', 'error')
        return redirect(url_for('view.view_document', document_id=document_id))
    
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('view.view_document', document_id=document_id))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('view.view_document', document_id=document_id))
    
    try:
        response = docs_table.get_item(Key={'document_id': document_id})
        if 'Item' not in response:
            flash('Document not found', 'error')
            return redirect(url_for('view.all_documents'))
            
        document = response['Item']
        
        if document.get('email') != session.get('user_email'):
            flash('You do not have permission to update this document', 'error')
            return redirect(url_for('view.all_documents'))
        
        if file and allowed_file(file.filename):
            try:
                version_id = datetime.now().strftime("%Y%m%d%H%M%S")
                version_history = document.get('versions', [])
                
                current_s3_key = document.get('s3_key')
                if current_s3_key:
                    try:
                        version_s3_key = current_s3_key.replace('documents/', f'versions/{version_id}/')
                        
                        try:
                            s3.head_object(Bucket=BUCKET_NAME, Key=current_s3_key)
                            
                            s3.copy_object(
                                Bucket=BUCKET_NAME,
                                CopySource={'Bucket': BUCKET_NAME, 'Key': current_s3_key},
                                Key=version_s3_key
                            )
                            
                            previous_version = {
                                'version_id': version_id,
                                'upload_date': document.get('upload_date'),
                                'file_size': document.get('file_size'),
                                'filename': document.get('filename'),
                                's3_key': version_s3_key,
                                'document_url': f"https://{BUCKET_NAME}.s3.amazonaws.com/{version_s3_key}"
                            }
                            
                            version_history.append(previous_version)
                            print(f"Successfully copied existing version to version history: {version_s3_key}")
                            
                        except s3.exceptions.ClientError as e:
                            if e.response['Error']['Code'] == '404' or e.response['Error']['Code'] == 'NoSuchKey':
                                print(f"Warning: Original file {current_s3_key} not found in S3, skipping version history")
                            else:
                                raise e
                                
                    except Exception as copy_err:
                        print(f"Warning: Could not copy original file to version history: {str(copy_err)}")
                
                filename = secure_filename(file.filename)
                file_extension = filename.rsplit('.', 1)[1].lower()
                s3_key = f"documents/{session['user_email']}/{document_id}/{filename}"
                
                file_data = file.read()
                file_size = len(file_data)
                encrypted_data, encryption_key_id = encryption_service.encrypt_file(file_data)
                s3_file = io.BytesIO(encrypted_data)
                
                s3.upload_fileobj(
                    s3_file,
                    BUCKET_NAME,
                    s3_key,
                    ExtraArgs={
                        'ContentType': file.content_type,
                        'ACL': 'public-read'
                    }
                )
                
                s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
                
                process_file = io.BytesIO(file_data)
                ai_result = process_document(process_file, file_extension)
                
                timestamp = datetime.now().isoformat()
                
                document_merkle_tree.add_document(document_id, {
                    'document_id': document_id, 
                    'document_name': filename,
                    'document_type': file_extension,
                    'file_size': file_size,
                    'upload_date': timestamp
                })

                document_merkle_tree.rebuild_tree()
                root_hash = document_merkle_tree.get_root_hash()
                
                # Update the Merkle root in the blockchain and get transaction details
                blockchain_result = blockchain_logger.update_merkle_root(root_hash, async_mode=False)
                
                # Store blockchain transaction details with document
                update_expression = "set document_url = :url, s3_key = :key, file_size = :size, " + \
                                    "filename = :name, upload_date = :date, versions = :ver, " + \
                                    "ai_summary = :sum, keyword_list = :kw, ai_topics = :top, " + \
                                    "text_content = :txt, version_count = :vc, encryption_key_id = :eki"
                
                expression_values = {
                    ':url': s3_url,
                    ':key': s3_key,
                    ':size': file_size,
                    ':name': filename,
                    ':date': timestamp,
                    ':ver': version_history,
                    ':sum': ai_result.get('summary', ''),
                    ':kw': ai_result.get('keywords', []),
                    ':top': ai_result.get('topics', []),
                    ':txt': ai_result.get('text_content', ''),
                    ':vc': len(version_history),
                    ':eki': encryption_key_id
                }
                
                if blockchain_result and blockchain_result.get('success'):
                    update_expression += ", blockchain_tx_hash = :tx, blockchain_block_number = :bn, " + \
                                        "merkle_root_at_upload = :mr, blockchain_verification = :bv"
                    expression_values.update({
                        ':tx': blockchain_result.get('tx_hash'),
                        ':bn': blockchain_result.get('block_number'),
                        ':mr': root_hash,
                        ':bv': True
                    })
                    print(f"Storing blockchain transaction details with version: {blockchain_result.get('tx_hash')}")
                else:
                    update_expression += ", merkle_root_at_upload = :mr, blockchain_verification = :bv"
                    expression_values.update({
                        ':mr': root_hash,
                        ':bv': False
                    })
                
                # Update document with new values including blockchain data
                docs_table.update_item(
                    Key={'document_id': document_id},
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_values
                )
                
                blockchain_logger.log_document_action(
                    document_id=document_id,
                    action_type=BlockchainLogger.ACTION_VERSION,
                    user_email=session['user_email'],
                    document_data=file_data,
                    metadata={'version_id': timestamp, 'filename': filename}
                )
                
                flash('New version uploaded successfully', 'success')
                return redirect(url_for('view.view_document', document_id=document_id))
                
            except Exception as e:
                flash(f'Error updating document: {str(e)}', 'error')
                return redirect(url_for('view.view_document', document_id=document_id))
        else:
            flash('Invalid file type', 'error')
            return redirect(url_for('view.view_document', document_id=document_id))
    except Exception as e:
        flash(f'Error accessing document: {str(e)}', 'error')
        return redirect(url_for('view.all_documents'))

@upload_bp.route('/version/restore/<document_id>', methods=['POST'])
@login_required
def restore_version(document_id):
    if s3 is None or docs_table is None:
        flash('Document service is temporarily unavailable', 'error')
        return redirect(url_for('view.document_versions', document_id=document_id))
    
    version_id = request.form.get('version_id')
    if not version_id:
        flash('No version specified for restoration', 'error')
        return redirect(url_for('view.document_versions', document_id=document_id))
    
    try:
        response = docs_table.get_item(Key={'document_id': document_id})
        if 'Item' not in response:
            flash('Document not found', 'error')
            return redirect(url_for('view.all_documents'))
            
        document = response['Item']
        
        if document.get('email') != session.get('user_email'):
            flash('Access denied', 'error')
            return redirect(url_for('view.all_documents'))
        
        versions = document.get('versions', [])
        version_to_restore = None
        
        for version in versions:
            if version.get('version_id') == version_id:
                version_to_restore = version
                break
        
        if not version_to_restore:
            flash('Version not found', 'error')
            return redirect(url_for('view.document_versions', document_id=document_id))
        
        current_version = {
            'version_id': datetime.now().strftime("%Y%m%d%H%M%S"),
            'upload_date': document.get('upload_date'),
            'file_size': document.get('file_size'),
            'filename': document.get('filename'),
            's3_key': document.get('s3_key'),
            'document_url': document.get('document_url')
        }
        
        updated_versions = [current_version] + versions
        updated_versions = [v for v in updated_versions if v.get('version_id') != version_id]
        
        version_s3_key = version_to_restore.get('s3_key')
        restored_filename = version_to_restore.get('filename')
        
        new_s3_key = f"documents/{session['user_email']}/{document_id}/{restored_filename}"
        
        s3.copy_object(
            Bucket=BUCKET_NAME,
            CopySource={'Bucket': BUCKET_NAME, 'Key': version_s3_key},
            Key=new_s3_key
        )
        
        new_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{new_s3_key}"
        file_size = version_to_restore.get('file_size', 0)
        timestamp = datetime.now().isoformat()
        
        document_merkle_tree.add_document(document_id, {
            'document_id': document_id,
            'document_name': restored_filename,
            'file_size': file_size,
            'restore_date': timestamp,
            'restored_from': version_id
        })

        document_merkle_tree.rebuild_tree()
        root_hash = document_merkle_tree.get_root_hash()
        
        # Update the Merkle root in the blockchain and get transaction details
        blockchain_result = blockchain_logger.update_merkle_root(root_hash, async_mode=False)
        
        # Base update expression
        update_expression = "set document_url = :url, s3_key = :key, filename = :name, " + \
                            "file_size = :size, upload_date = :date, versions = :ver, " + \
                            "version_count = :vc, restore_date = :rd, restored_from = :rf"
        
        expression_values = {
            ':url': new_url,
            ':key': new_s3_key,
            ':name': restored_filename,
            ':size': file_size,
            ':date': timestamp,
            ':ver': updated_versions,
            ':vc': len(updated_versions),
            ':rd': timestamp,
            ':rf': version_id
        }
        
        # Add blockchain transaction details
        if blockchain_result and blockchain_result.get('success'):
            update_expression += ", blockchain_tx_hash = :tx, blockchain_block_number = :bn, " + \
                                "merkle_root_at_restore = :mr, blockchain_verification = :bv"
            expression_values.update({
                ':tx': blockchain_result.get('tx_hash'),
                ':bn': blockchain_result.get('block_number'),
                ':mr': root_hash,
                ':bv': True
            })
            print(f"Storing blockchain transaction details with restored version: {blockchain_result.get('tx_hash')}")
        else:
            update_expression += ", merkle_root_at_restore = :mr, blockchain_verification = :bv"
            expression_values.update({
                ':mr': root_hash,
                ':bv': False
            })
        
        # Update document with blockchain details
        docs_table.update_item(
            Key={'document_id': document_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        blockchain_logger.log_document_action(
            document_id=document_id,
            action_type=BlockchainLogger.ACTION_RESTORE,
            user_email=session['user_email'],
            metadata={'restored_from': version_id, 'restore_date': timestamp}
        )
        
        flash('Previous version restored successfully', 'success')
        return redirect(url_for('view.view_document', document_id=document_id))
        
    except Exception as e:
        flash(f'Error restoring version: {str(e)}', 'error')
        return redirect(url_for('view.document_versions', document_id=document_id))

@upload_bp.route('/document/delete/<document_id>', methods=['POST'])
@login_required
def delete_document(document_id):
    email = session.get('user_email')
    user_id = session.get('user_id')
    
    try:
        document = None
        
        if docs_table:
            response = docs_table.get_item(
                Key={
                    'document_id': document_id
                }
            )
            document = response.get('Item')
            
            if document and document.get('email') != email:
                flash('You do not have permission to delete this document', 'error')
                return redirect(url_for('view.all_documents'))
                
            if document and 's3_key' in document:
                try:
                    s3.delete_object(
                        Bucket=BUCKET_NAME,
                        Key=document['s3_key']
                    )
                except Exception as e:
                    print(f"Error deleting current version from S3: {str(e)}")
            
            if document and 'versions' in document:
                try:
                    version_keys = [v.get('s3_key') for v in document['versions'] if 's3_key' in v]
                    
                    for key in version_keys:
                        s3.delete_object(
                            Bucket=BUCKET_NAME,
                            Key=key
                        )
                except Exception as e:
                    print(f"Error deleting version files from S3: {str(e)}")
            
            # Store deletion record in blockchain before removing from DynamoDB
            try:
                # Get document details before deletion
                response = docs_table.get_item(Key={'document_id': document_id})
                document_details = response.get('Item', {})
                
                # Log deletion in blockchain with document metadata
                deletion_metadata = {
                    'deletion_date': datetime.now().isoformat(),
                    'document_name': document_details.get('document_name', 'Unknown'),
                    'file_size': document_details.get('file_size', 0),
                    'original_upload_date': document_details.get('upload_date', 'Unknown')
                }
                
                blockchain_logger.log_document_action(
                    document_id=document_id,
                    action_type=BlockchainLogger.ACTION_DELETE,
                    user_email=session['user_email'],
                    metadata=deletion_metadata
                )
                
                # Now remove document from database
                docs_table.delete_item(Key={'document_id': document_id})
                
            except Exception as e:
                print(f"Error logging deletion in blockchain: {str(e)}")
            
            document_merkle_tree.remove_document(document_id)
            document_merkle_tree.rebuild_tree()
            root_hash = document_merkle_tree.get_root_hash()
            blockchain_logger.update_merkle_root(root_hash)
            
            flash('Document and all versions deleted successfully', 'success')
        else:
            flash('Document service unavailable', 'error')
            
    except Exception as e:
        flash(f'Error deleting document: {str(e)}', 'error')
    
    return redirect(url_for('view.all_documents'))