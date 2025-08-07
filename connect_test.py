# connect_test.py
import os
import urllib.request
import ssl
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables from .env file
load_dotenv()

# Get connection details from environment
tidb_host = os.getenv("TIDB_HOST")
tidb_port = os.getenv("TIDB_PORT")
tidb_user = os.getenv("TIDB_USER")
tidb_password = os.getenv("TIDB_PASSWORD")

def download_ca_certificate():
    """Download TiDB Cloud CA certificate if it doesn't exist"""
    ca_cert_path = Path("isrgrootx1.pem")
    
    if not ca_cert_path.exists():
        print("Downloading TiDB Cloud CA certificate...")
        try:
            # Download the Let's Encrypt ISRG Root X1 certificate (used by TiDB Cloud)
            url = "https://letsencrypt.org/certs/isrgrootx1.pem"
            urllib.request.urlretrieve(url, ca_cert_path)
            print(f"CA certificate downloaded to: {ca_cert_path.absolute()}")
        except Exception as e:
            print(f"Failed to download CA certificate: {e}")
            return None
    else:
        print(f"CA certificate already exists: {ca_cert_path.absolute()}")
    
    return ca_cert_path.absolute()

def get_connection_string():
    """Get connection string with proper SSL configuration for TiDB Cloud"""
    # Try to get CA certificate
    ca_cert_path = download_ca_certificate()
    
    if ca_cert_path and ca_cert_path.exists():
        # Use SSL with proper TiDB Cloud configuration
        connection_string = (
            f"mysql+pymysql://{tidb_user}:{tidb_password}@{tidb_host}:{tidb_port}/test"
            f"?ssl_ca={ca_cert_path}&ssl_verify_cert=true&ssl_verify_identity=true"
        )
        return connection_string
    else:
        # Fallback to basic SSL without custom CA
        print("Using basic SSL configuration...")
        return (
            f"mysql+pymysql://{tidb_user}:{tidb_password}@{tidb_host}:{tidb_port}/test"
            f"?ssl_verify_cert=true&ssl_verify_identity=true"
        )

def test_connection():
    """Test the database connection"""
    connection_string = get_connection_string()
    print(f"Connection string: {connection_string}")
    
    try:
        # Create an engine with SSL configuration
        engine = create_engine(
            connection_string,
            connect_args={
                "ssl": {
                    "check_hostname": False,
                    "verify_mode": ssl.CERT_REQUIRED,
                }
            }
        )

        # Connect and execute a simple query
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 'Hello from TiDB!' as message;"))
            for row in result:
                print(f"✅ {row.message}")

        print("✅ Connection to TiDB Cloud successful!")
        return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        # Try alternative SSL configuration
        print("Trying alternative SSL configuration...")
        return test_connection_alternative()

def test_connection_alternative():
    """Alternative connection method with different SSL settings"""
    try:
        # Simplified connection string with SSL enabled
        connection_string = (
            f"mysql+pymysql://{tidb_user}:{tidb_password}@{tidb_host}:{tidb_port}/test"
            f"?ssl=true&ssl_verify_cert=false"
        )
        
        engine = create_engine(connection_string)
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 'Hello from TiDB!' as message;"))
            for row in result:
                print(f"✅ {row.message}")
        
        print("✅ Alternative SSL connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Alternative connection also failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()