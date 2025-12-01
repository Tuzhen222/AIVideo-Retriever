"""
Test PostgreSQL setup script
- Starts PostgreSQL container
- Tests connection
- Cleans up after testing
"""
import sys
import os
import subprocess
import time
import signal

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.db import get_connection, init_database
from app.core.config import settings
import psycopg2
import psycopg2.extras

# Global variable to track cleanup
cleanup_needed = False
postgres_container_name = None
test_host = None  # Override host for local testing

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n⚠️  Interrupted! Cleaning up...")
    cleanup()
    sys.exit(1)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def run_command(cmd, check=True, capture_output=False):
    """Run shell command"""
    try:
        if capture_output:
            result = subprocess.run(
                cmd, shell=True, check=check, 
                capture_output=True, text=True
            )
            return result.stdout.strip()
        else:
            result = subprocess.run(cmd, shell=True, check=check)
            return None
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return None

def start_postgres_container():
    """Start PostgreSQL container using docker-compose"""
    global cleanup_needed, postgres_container_name
    
    print("=" * 60)
    print("Starting PostgreSQL Container")
    print("=" * 60)
    
    # Check if docker-compose is available
    try:
        run_command("docker-compose --version", capture_output=True)
    except:
        try:
            run_command("docker compose version", capture_output=True)
            compose_cmd = "docker compose"
        except:
            print("❌ docker-compose or docker compose not found!")
            return False
    else:
        compose_cmd = "docker-compose"
    
    # Get project directory (parent of backend)
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_dir)
    
    # Check which docker-compose file to use
    compose_file = "docker-compose.dev.yml" if os.path.exists("docker-compose.dev.yml") else "docker-compose.yml"
    
    print(f"Using {compose_file}")
    print(f"Project directory: {project_dir}")
    
    # Start only postgres service
    print("\nStarting PostgreSQL service...")
    try:
        run_command(f"{compose_cmd} -f {compose_file} up -d postgres")
        print("✅ PostgreSQL container started")
        cleanup_needed = True
        
        # Get container name
        output = run_command(
            f"{compose_cmd} -f {compose_file} ps postgres -q",
            capture_output=True
        )
        if output:
            container_id = output.split('\n')[0] if '\n' in output else output
            container_name = run_command(
                f"docker inspect --format='{{{{.Name}}}}' {container_id}",
                capture_output=True
            )
            postgres_container_name = container_name.lstrip('/') if container_name else "postgres"
        
        return True
    except Exception as e:
        print(f"❌ Failed to start PostgreSQL container: {e}")
        return False

def get_test_connection():
    """Get connection for testing - uses localhost if running from local"""
    global test_host
    
    if test_host:
        # Override connection string for local testing
        conn_str = (
            f"host={test_host} "
            f"port={settings.POSTGRES_PORT} "
            f"dbname={settings.POSTGRES_DB} "
            f"user={settings.POSTGRES_USER} "
            f"password={settings.POSTGRES_PASSWORD}"
        )
        
        class TestConnection:
            def __enter__(self):
                self.conn = psycopg2.connect(
                    conn_str,
                    cursor_factory=psycopg2.extras.RealDictCursor
                )
                return self.conn
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.conn:
                    if exc_type:
                        self.conn.rollback()
                    else:
                        self.conn.commit()
                    self.conn.close()
                return False
        
        return TestConnection()
    else:
        # Use normal connection (for Docker network)
        return get_connection()

def wait_for_postgres(max_wait=30):
    """Wait for PostgreSQL to be ready"""
    print("\n" + "=" * 60)
    print("Waiting for PostgreSQL to be ready")
    print("=" * 60)
    
    elapsed = 0
    while elapsed < max_wait:
        try:
            with get_test_connection() as conn:
                print("✅ PostgreSQL is ready!")
                return True
        except Exception as e:
            elapsed += 2
            if elapsed < max_wait:
                print(f"   Waiting... ({elapsed}/{max_wait}s) - {str(e)[:50]}")
                time.sleep(2)
            else:
                print(f"❌ PostgreSQL not ready after {max_wait}s")
                return False
    return False

def test_connection():
    """Test PostgreSQL connection"""
    global test_host
    
    print("\n" + "=" * 60)
    print("Testing PostgreSQL Connection")
    print("=" * 60)
    actual_host = test_host if test_host else settings.POSTGRES_HOST
    print(f"Host: {actual_host}")
    print(f"Port: {settings.POSTGRES_PORT}")
    print(f"Database: {settings.POSTGRES_DB}")
    print(f"User: {settings.POSTGRES_USER}")
    print("-" * 60)
    
    try:
        print("Attempting to connect to PostgreSQL...")
        with get_test_connection() as conn:
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Connection successful!")
            print(f"PostgreSQL version: {version['version'][:50]}...")
            
            # Test database info
            cursor.execute("SELECT current_database(), current_user;")
            db_info = cursor.fetchone()
            print(f"Current database: {db_info['current_database']}")
            print(f"Current user: {db_info['current_user']}")
            
            # Test table existence
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'query_submissions'
                );
            """)
            table_exists = cursor.fetchone()['exists']
            
            if table_exists:
                print(f"✅ Table 'query_submissions' exists")
                cursor.execute("SELECT COUNT(*) as count FROM query_submissions")
                count = cursor.fetchone()['count']
                print(f"   Records in table: {count}")
            else:
                print(f"⚠️  Table 'query_submissions' does not exist yet")
            
            print("-" * 60)
            print("✅ Connection test passed!")
            return True
            
    except Exception as e:
        print(f"❌ Connection failed!")
        print(f"Error: {e}")
        return False

def test_init_database():
    """Test database initialization"""
    global test_host
    
    print("\n" + "=" * 60)
    print("Testing Database Initialization")
    print("=" * 60)
    
    # Temporarily override POSTGRES_HOST for local testing
    original_host = settings.POSTGRES_HOST
    if test_host:
        settings.POSTGRES_HOST = test_host
    
    try:
        init_database()
        print("✅ Database initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    finally:
        # Always restore original host
        settings.POSTGRES_HOST = original_host

def cleanup():
    """Clean up PostgreSQL container"""
    global cleanup_needed
    
    if not cleanup_needed:
        return
    
    print("\n" + "=" * 60)
    print("Cleaning Up")
    print("=" * 60)
    
    # Get project directory
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    original_dir = os.getcwd()
    
    try:
        os.chdir(project_dir)
        
        # Check which compose command to use
        try:
            run_command("docker-compose --version", capture_output=True)
            compose_cmd = "docker-compose"
        except:
            compose_cmd = "docker compose"
        
        # Check which docker-compose file was used
        compose_file = "docker-compose.dev.yml" if os.path.exists("docker-compose.dev.yml") else "docker-compose.yml"
        
        print(f"Stopping PostgreSQL container...")
        run_command(f"{compose_cmd} -f {compose_file} stop postgres", check=False)
        
        print(f"Removing PostgreSQL container...")
        run_command(f"{compose_cmd} -f {compose_file} rm -f postgres", check=False)
        
        print("✅ Cleanup completed!")
        cleanup_needed = False
        
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")
    finally:
        os.chdir(original_dir)

def main():
    """Main test function"""
    global test_host
    
    try:
        # Step 0: Detect if running from local (not in Docker)
        # If POSTGRES_HOST is "postgres", we're likely running from local
        # and need to use "localhost" instead
        if settings.POSTGRES_HOST == "postgres":
            # Check if we can resolve "postgres" hostname
            try:
                import socket
                socket.gethostbyname("postgres")
                # If successful, we're in Docker network, use "postgres"
                test_host = None
            except socket.gaierror:
                # Cannot resolve "postgres", we're running from local
                print("ℹ️  Detected local environment - using 'localhost' for connection")
                test_host = "localhost"
        
        # Step 1: Start PostgreSQL
        if not start_postgres_container():
            return False
        
        # Step 2: Wait for PostgreSQL to be ready
        if not wait_for_postgres():
            return False
        
        # Step 3: Test connection
        if not test_connection():
            return False
        
        # Step 4: Test database initialization (optional)
        print("\n" + "-" * 60)
        test_init = input("Do you want to test database initialization? (y/n): ").strip().lower()
        if test_init == 'y':
            if not test_init_database():
                return False
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return True
        
    finally:
        # Always cleanup
        cleanup()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

