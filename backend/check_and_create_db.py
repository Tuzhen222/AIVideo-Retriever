"""Check and create database if needed"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
import psycopg2
import psycopg2.extras

def list_and_create_db():
    """List databases and create if needed"""
    params = {
        "host": settings.POSTGRES_HOST,
        "port": settings.POSTGRES_PORT,
        "dbname": "postgres",  # Connect to default database
        "user": settings.POSTGRES_USER,
        "password": settings.POSTGRES_PASSWORD,
        "cursor_factory": psycopg2.extras.RealDictCursor
    }
    
    if ".rds.amazonaws.com" in settings.POSTGRES_HOST.lower():
        params["sslmode"] = "require"
    
    try:
        # List databases
        conn = psycopg2.connect(**params)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT datname 
            FROM pg_database 
            WHERE datistemplate = false
            ORDER BY datname;
        """)
        
        databases = [db['datname'] for db in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        print("=" * 70)
        print("Database Status Check")
        print("=" * 70)
        print(f"Target Database: {settings.POSTGRES_DB}")
        print(f"\n📋 Existing databases:")
        for db in databases:
            marker = " ← Target" if db == settings.POSTGRES_DB else ""
            print(f"   - {db}{marker}")
        
        if settings.POSTGRES_DB in databases:
            print(f"\n✅ Database '{settings.POSTGRES_DB}' already exists!")
            return True
        else:
            print(f"\n⚠️  Database '{settings.POSTGRES_DB}' does not exist")
            print(f"   Creating database '{settings.POSTGRES_DB}'...")
            
            # Create database
            conn = psycopg2.connect(**params)
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}";')
            cursor.close()
            conn.close()
            
            print(f"✅ Database '{settings.POSTGRES_DB}' created successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if list_and_create_db():
        print("\n✅ Ready! You can now test connection: py test_db_connection.py")
    else:
        sys.exit(1)

