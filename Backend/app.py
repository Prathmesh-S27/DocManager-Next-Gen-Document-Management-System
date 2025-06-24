from flask import Flask, Blueprint, g
from flask_cors import CORS
import threading

# Import security services
from utils.encryption import encryption_service
from utils.bloom_filter import keyword_filter
from utils.keyword_matching import keyword_matcher
from utils.merkle_tree import document_merkle_tree
from blockchain.blockchain_logger import blockchain_logger, BlockchainLogger
from utils.init_database import initialize_database

app = Flask(__name__, 
           template_folder='../Frontend/templates',
           static_folder='../Frontend/static')

# Set the secret key for the session management
app.secret_key = '<YOUR_SECRET_KEY>'
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

# Initialize database tables
print("Initializing database tables...")
db_thread = threading.Thread(target=initialize_database)
db_thread.daemon = True
db_thread.start()
db_thread.join(timeout=10)  # Wait for database initialization with timeout

# Initialize security services immediately
print("Initializing security services...")
# Start blockchain logger worker thread
blockchain_logger.start_worker()

# Flag to track initialization
_merkle_tree_initialized = False

# Modified function to initialize Merkle tree with existing documents
def initialize_merkle_tree():
    try:
        print("Starting Merkle tree initialization...")
        # Initialize Merkle tree with existing documents
        from boto3.dynamodb.conditions import Key
        from utils.aws_config import docs_table
        
        if docs_table:
            # Get all document IDs and build the tree
            response = docs_table.scan(
                ProjectionExpression="document_id, document_name, document_type, file_size, upload_date"
            )
            for item in response.get('Items', []):
                document_merkle_tree.add_document(item['document_id'], item)
            
            document_merkle_tree.rebuild_tree()
            root_hash = document_merkle_tree.get_root_hash()
            
            # Only update blockchain if there are documents and we have a root hash
            if root_hash:
                print(f"Updating blockchain with Merkle root: {root_hash}")
                try:
                    # Directly call the method to verify it exists
                    blockchain_result = blockchain_logger._update_merkle_root_sync_with_details(root_hash)
                    print(f"Blockchain update result: {blockchain_result}")
                except Exception as e:
                    print(f"Error updating blockchain with Merkle root: {e}")
            
            print("Merkle tree initialized successfully")
            return True
    except Exception as e:
        print(f"Error initializing Merkle tree: {e}")
        return False

# Use regular before_request and check if we've initialized
@app.before_request
def check_initialization():
    global _merkle_tree_initialized
    if not _merkle_tree_initialized:
        _merkle_tree_initialized = True
        print("Initializing Merkle tree on first request...")
        # Run in a separate thread to not block the request
        init_thread = threading.Thread(target=initialize_merkle_tree)
        init_thread.daemon = True
        init_thread.start()

# Import all routes before registering any blueprints
from routes import testing
from routes.auth import auth_bp
from routes.user import user_bp
from routes.main import main_bp
from routes.upload_document import upload_bp
from routes.view_document import view_bp
from routes.security import security_bp  # Import the security blueprint

# Register blueprints with clearer URL structure
app.register_blueprint(testing.testing_bp)
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(user_bp, url_prefix='/user')
app.register_blueprint(view_bp, url_prefix='/view')
app.register_blueprint(upload_bp, url_prefix='/upload')
app.register_blueprint(security_bp, url_prefix='/security')  # Register the security blueprint

@app.route('/api/health', methods=['GET'])
def hello_world():
    return 'Server is running!'

if __name__ == '__main__':
    app.run(debug=True, port=5000)