import pytest
from utils.merkle_tree import DocumentMerkleTree, document_merkle_tree
import hashlib
import decimal

class TestMerkleTree:
    def test_empty_tree(self):
        """Test operations on an empty Merkle tree"""
        tree = DocumentMerkleTree()
        
        # Empty tree should have no root hash
        assert tree.get_root_hash() == ""
    
    def test_add_document(self):
        """Test adding a document to the tree"""
        tree = DocumentMerkleTree()
        
        # Add a document
        doc_id = "test-doc-1"
        doc_data = {
            "document_id": doc_id,
            "document_name": "Test Document",
            "document_type": "pdf",
            "file_size": 1024,
            "upload_date": "2025-05-10T10:00:00"
        }
        
        tree.add_document(doc_id, doc_data)
        
        # Rebuild the tree
        tree.rebuild_tree()
        
        # Verify root hash is now set
        assert tree.get_root_hash() != ""
    
    def test_document_verification(self):
        """Test document verification in the tree"""
        tree = DocumentMerkleTree()
        
        # Add a document
        doc_id = "test-doc-2"
        doc_data = {
            "document_id": doc_id,
            "document_name": "Verification Test",
            "document_type": "docx",
            "file_size": 2048,
            "upload_date": "2025-05-10T11:00:00"
        }
        
        tree.add_document(doc_id, doc_data)
        tree.rebuild_tree()
        
        # Verify with correct data
        assert tree.verify_document(doc_id, doc_data) == True
        
        # Verify with modified data
        modified_data = doc_data.copy()
        modified_data["document_name"] = "Modified Name"
        assert tree.verify_document(doc_id, modified_data) == False
    
    def test_decimal_handling(self):
        """Test handling of Decimal values from DynamoDB"""
        tree = DocumentMerkleTree()
        
        # Add a document with Decimal
        doc_id = "decimal-test"
        doc_data = {
            "document_id": doc_id,
            "document_name": "Decimal Test",
            "document_type": "pdf",
            "file_size": decimal.Decimal('1024.5'),
            "upload_date": "2025-05-10T12:00:00"
        }
        
        tree.add_document(doc_id, doc_data)
        tree.rebuild_tree()
        
        # Verify document was added and tree built successfully
        assert tree.get_root_hash() != ""
        
        # Verify with float instead of Decimal
        verify_data = doc_data.copy()
        verify_data["file_size"] = float(doc_data["file_size"])
        assert tree.verify_document(doc_id, verify_data) == True
