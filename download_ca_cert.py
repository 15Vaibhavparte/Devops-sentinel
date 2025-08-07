# download_ca_cert.py
import urllib.request
import ssl
import os

def download_tidb_ca_cert():
    """Download TiDB Cloud CA certificate"""
    ca_cert_url = "https://letsencrypt.org/certs/isrgrootx1.pem"
    ca_cert_path = "isrgrootx1.pem"
    
    try:
        # Create SSL context that doesn't verify certificates for this download
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Download the certificate
        with urllib.request.urlopen(ca_cert_url, context=ssl_context) as response:
            with open(ca_cert_path, 'wb') as f:
                f.write(response.read())
        
        print(f"CA certificate downloaded successfully to: {os.path.abspath(ca_cert_path)}")
        return os.path.abspath(ca_cert_path)
        
    except Exception as e:
        print(f"Failed to download CA certificate: {e}")
        return None

if __name__ == "__main__":
    download_tidb_ca_cert()
