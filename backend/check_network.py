"""
Check network connectivity to RDS
"""
import socket
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings

def check_port_connectivity(host, port, timeout=5):
    """Check if port is accessible"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Error checking port: {e}")
        return False

def get_public_ip():
    """Get public IP address"""
    try:
        import urllib.request
        ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
        return ip
    except:
        return "Unable to determine"

if __name__ == "__main__":
    print("=" * 70)
    print("Network Connectivity Check for RDS")
    print("=" * 70)
    print(f"RDS Host: {settings.POSTGRES_HOST}")
    print(f"RDS Port: {settings.POSTGRES_PORT}")
    print(f"Your Public IP: {get_public_ip()}")
    print("-" * 70)
    
    print(f"\n🔍 Testing TCP connection to {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}...")
    
    # Resolve hostname to IP
    try:
        ip = socket.gethostbyname(settings.POSTGRES_HOST)
        print(f"   Resolved IP: {ip}")
    except Exception as e:
        print(f"   ❌ Cannot resolve hostname: {e}")
        sys.exit(1)
    
    # Test port connectivity
    print(f"\n🔌 Testing port {settings.POSTGRES_PORT}...")
    if check_port_connectivity(settings.POSTGRES_HOST, settings.POSTGRES_PORT, timeout=10):
        print("   ✅ Port is accessible!")
        print("\n✅ Network connectivity is OK!")
        print("   If database connection still fails, check:")
        print("   - Database credentials (username/password)")
        print("   - Database name exists")
    else:
        print("   ❌ Port is NOT accessible (connection timeout)")
        print("\n❌ Network connectivity issue detected!")
        print("\n💡 Fix steps:")
        print("   1. Go to AWS Console → RDS → Your Database")
        print("   2. Check 'Publicly accessible' = Yes")
        print("   3. Go to EC2 → Security Groups → Find your RDS security group")
        print("   4. Edit Inbound Rules → Add rule:")
        print("      - Type: PostgreSQL")
        print("      - Port: 5432")
        print("      - Source: 0.0.0.0/0 (or your IP: {})".format(get_public_ip()))
        print("   5. Save rules and wait 1-2 minutes")
        print("   6. Try connecting again")
    
    print("\n" + "=" * 70)

