import sqlite3
import os

db_path = 'instance/eye_disease.db'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(diagnosis)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'doctor_id' not in columns:
            print("Adding 'doctor_id' column to 'diagnosis' table...")
            cursor.execute("ALTER TABLE diagnosis ADD COLUMN doctor_id INTEGER REFERENCES user(id)")
            conn.commit()
            print("Successfully added 'doctor_id' column.")
        else:
            print("'doctor_id' column already exists.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
else:
    print(f"Database file {db_path} not found.")
