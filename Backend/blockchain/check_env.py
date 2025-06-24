import os
from dotenv import load_dotenv
import sys

def check_environment():
    """Check environment setup for blockchain deployment"""
    print("Checking blockchain environment setup...")
    
    # Check if dotenv is installed
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv is installed")
    except ImportError:
        print("❌ python-dotenv is not installed")
        print("   Please run: pip install python-dotenv")
        return False
    
    # Check if .env file exists
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(dotenv_path):
        print(f"✅ .env file found at {dotenv_path}")
        load_dotenv(dotenv_path)
    else:
        print(f"❌ .env file not found at {dotenv_path}")
        print("   Please create this file with your blockchain keys")
        return False
    
    # Check if GANACHE_PRIVATE_KEY is set
    private_key = os.getenv('GANACHE_PRIVATE_KEY')
    if private_key:
        # Remove 0x prefix if present
        if private_key.startswith('0x'):
            private_key = private_key[2:]
        
        # Check key length and format
        if len(private_key) == 64 and all(c in '0123456789abcdefABCDEF' for c in private_key):
            print("✅ Private key has valid format")
        else:
            print("❌ Private key has invalid format")
            print(f"   Length: {len(private_key)} characters (should be 64)")
            print("   Should be a hexadecimal string")
            return False
    else:
        print("❌ GANACHE_PRIVATE_KEY not found in .env file")
        print("   Please add it as: GANACHE_PRIVATE_KEY=your_key_here")
        return False
    
    # Check other blockchain requirements
    try:
        import web3
        print("✅ web3 package is installed")
    except ImportError:
        print("❌ web3 package is not installed")
        print("   Please run: pip install web3")
        return False
    
    try:
        import solcx
        print("✅ py-solc-x package is installed")
    except ImportError:
        print("❌ py-solc-x package is not installed")
        print("   Please run: pip install py-solc-x")
        return False
    
    print("\nEnvironment check completed successfully! ✨")
    return True

if __name__ == "__main__":
    check_environment()
