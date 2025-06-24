import pytest
from flask import session
import boto3
import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash

class TestAuthRoutes:
    def test_login_page(self, client):
        """Test login page loads correctly"""
        response = client.get('/auth/login')  # Updated route
        assert response.status_code == 200
        assert b'Login' in response.data
    
    def test_signup_page(self, client):
        """Test signup page loads correctly"""
        response = client.get('/auth/signup')  # Updated route
        assert response.status_code == 200
        assert b'Sign Up' in response.data
    
    def test_login_process(self, client, mock_aws, blockchain_config):
        """Test user login process"""
        # Skip if we're using real blockchain but it's not available
        if not blockchain_config.get('simulation_mode', True):
            try:
                from web3 import Web3
                provider_url = blockchain_config.get('provider_url')
                w3 = Web3(Web3.HTTPProvider(provider_url))
                if not w3.is_connected():
                    pytest.skip("Real blockchain required but not available")
            except:
                pytest.skip("Could not check blockchain connection")
                
        # First create a test user
        dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')
        user_table = dynamodb.Table('Document_Detail')
        
        user_id = str(uuid.uuid4())
        email = "testuser@example.com"
        password = "TestPassword123"
        
        # Add user to database
        user_table.put_item(Item={
            'email': email,
            'user_id': user_id,
            'password_hash': generate_password_hash(password),
            'name': 'Test User',
            'phone': '1234567890',
            'created_at': datetime.now().isoformat(),
            'last_login': datetime.now().isoformat()
        })
        
        # Try to login
        response = client.post('/auth/login', data={  # Updated route
            'email': email,
            'password': password
        }, follow_redirects=True)
        
        # Check status code first
        assert response.status_code == 200
        
        # With follow_redirects, we should be at the dashboard
        assert b'Dashboard' in response.data or b'Welcome' in response.data
    
    def test_logout(self, authenticated_client):
        """Test user logout"""
        # Verify user is logged in
        with authenticated_client.session_transaction() as sess:
            assert 'user_email' in sess
        
        # Logout
        response = authenticated_client.get('/auth/logout', follow_redirects=True)  # Updated route
        
        # Verify logout was successful
        assert response.status_code == 200
        
        # Check session is cleared
        with authenticated_client.session_transaction() as sess:
            assert 'user_email' not in sess
