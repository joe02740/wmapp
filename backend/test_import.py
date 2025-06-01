try:
    from database import init_db, get_db_connection
    print("Database import successful")
    
    # Test connection
    conn = get_db_connection()
    print("Database connection successful")
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()