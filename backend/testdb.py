import psycopg2
import os

DATABASE_URL = "postgresql://postgres:Oz3AtqHOdiX4eb0N@db.ubcrlyzxiqfduyvhormn.supabase.co:5432/postgres"

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('SELECT version()')
    result = cursor.fetchone()
    print("SUCCESS:", result)
    cursor.close()
    conn.close()
except Exception as e:
    print("ERROR:", str(e))