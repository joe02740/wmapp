import psycopg2
import psycopg2.extras
import os
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def get_db_connection():
    """
    Create and return a PostgreSQL database connection.
    Uses DATABASE_URL environment variable or constructs from individual vars.
    """
    try:
        # Try to get full DATABASE_URL first (common in production like Heroku)
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            # Debug logging
            logger.info(f"DATABASE_URL exists: {database_url is not None}")
            if "@" in database_url:
                host_part = database_url.split("@")[1].split("/")[0]
                logger.info(f"Connecting to host: {host_part}")
            
            # Parse the URL
            url = urlparse(database_url)
            conn = psycopg2.connect(
                host=url.hostname,
                port=url.port,
                database=url.path[1:],  # Remove leading slash
                user=url.username,
                password=url.password,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
        else:
            # Use individual environment variables
            logger.info("Using individual DB environment variables")
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'wmhelper'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', ''),
                cursor_factory=psycopg2.extras.RealDictCursor
            )
        
        logger.info("Database connection established successfully")
        return conn
        
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error connecting to database: {str(e)}")
        raise

def init_db():
    """
    Initialize the database with required tables.
    Creates tables if they don't exist.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(255) PRIMARY KEY,
                email VARCHAR(255),
                name VARCHAR(255),
                subscription_tier VARCHAR(50) DEFAULT 'free',
                subscription_end_date TIMESTAMP,
                stripe_customer_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create usage table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) REFERENCES users(id),
                query TEXT,
                scope VARCHAR(50),
                tokens_used INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create chat_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) REFERENCES users(id),
                title VARCHAR(500),
                messages JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_usage_user_id ON usage(user_id);
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_usage_created_at ON usage(created_at);
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at);
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("Database initialized successfully")
        
    except psycopg2.Error as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing database: {str(e)}")
        raise

def execute_query(query, params=None, fetch=False):
    """Execute a database query"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute(query, params)
        
        if fetch:
            result = cursor.fetchall()
        else:
            result = cursor.rowcount
            
        conn.commit()
        cursor.close()
        conn.close()
        
        return result
        
    except Exception as e:
        logger.error(f"Database query error: {str(e)}")
        raise

def test_connection():
    """
    Test the database connection and return status.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        
        logger.info(f"Database connection test successful. PostgreSQL version: {version[0]}")
        return True, f"Connected successfully. PostgreSQL version: {version[0]}"
        
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    # Test the database connection when run directly
    success, message = test_connection()
    print(f"Database test: {'PASSED' if success else 'FAILED'}")
    print(f"Message: {message}")
    
    if success:
        print("Initializing database...")
        try:
            init_db()
            print("Database initialization completed successfully!")
        except Exception as e:
            print(f"Database initialization failed: {str(e)}")