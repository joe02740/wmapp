import psycopg2
import psycopg2.extras
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection"""
    try:
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable not set")
        
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

def init_db():
    """Test database connection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Just test the connection
        cursor.execute('SELECT 1')
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            logger.info("Database connection successful")
        else:
            logger.warning("Database connection test failed")
        
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
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