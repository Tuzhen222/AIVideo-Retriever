"""
Test RDS PostgreSQL connection script
"""
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.db import get_connection, init_database
from app.core.config import settings
import psycopg2


def test_connection():
    """Test database connection and log results"""
    print("=" * 70)
    print("Testing RDS PostgreSQL Connection")
    print("=" * 70)
    print(f"Host: {settings.POSTGRES_HOST}")
    print(f"Port: {settings.POSTGRES_PORT}")
    print(f"Database: {settings.POSTGRES_DB}")
    print(f"User: {settings.POSTGRES_USER}")
    print(f"Password: {'*' * len(settings.POSTGRES_PASSWORD) if settings.POSTGRES_PASSWORD else '(empty)'}")
    print("-" * 70)
    
    try:
        print("\n🔌 Attempting to connect...")
        with get_connection() as conn:
            print("✅ Connection successful!")
            
            cursor = conn.cursor()
            
            # Get PostgreSQL version
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"\n📊 PostgreSQL Version:")
            print(f"   {version['version']}")
            
            # Get current database
            cursor.execute("SELECT current_database();")
            db_name = cursor.fetchone()
            print(f"\n📁 Current Database: {db_name['current_database']}")
            
            # Get current user
            cursor.execute("SELECT current_user;")
            user = cursor.fetchone()
            print(f"👤 Current User: {user['current_user']}")
            
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'query_submissions'
                );
            """)
            table_exists = cursor.fetchone()
            
            if table_exists['exists']:
                print("\n✅ Table 'query_submissions' exists")
                
                # Count records
                cursor.execute("SELECT COUNT(*) as count FROM query_submissions")
                count = cursor.fetchone()
                print(f"📊 Total records: {count['count']}")
                
                # Get table structure
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'query_submissions'
                    ORDER BY ordinal_position;
                """)
                columns = cursor.fetchall()
                print(f"\n📋 Table structure:")
                for col in columns:
                    nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                    print(f"   - {col['column_name']}: {col['data_type']} ({nullable})")
            else:
                print("\n⚠️  Table 'query_submissions' does not exist")
                print("   Initializing database to create tables...")
                init_database()
                print("✅ Database initialized!")
            
            print("\n" + "=" * 70)
            print("✅ All connection tests passed!")
            print("=" * 70)
            return True
            
    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection failed!")
        print(f"   Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check RDS status in AWS Console (should be 'Available')")
        print("   2. Verify Security Group allows your IP on port 5432")
        print("   3. Check .env file: POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD")
        print("   4. Ensure Publicly accessible = Yes (if connecting from local)")
        return False
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 Starting Database Connection Test...\n")
    success = test_connection()
    
    if not success:
        sys.exit(1)
    
    print("\n✨ Test completed successfully!")

