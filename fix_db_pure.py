import sqlite3
import os

def fix_database_pure():
    # Hardcoded path based on previous findings
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, 'instance', 'eye_disease.db')
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        # Fallback to root if instance doesn't exist? (Unlikely given previous findings)
        db_path = os.path.join(base_dir, 'eye_disease.db')
        if not os.path.exists(db_path):
             print(f"Error: Database also not found at {db_path}")
             return

    print(f"Fixing DB at: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ADD COLUMNS
    columns_to_add = [
        ("email", "VARCHAR(120)"),
        ("otp_secret", "VARCHAR(6)"),
        ("otp_expiry", "DATETIME")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_type}")
            print(f"Added {col_name}")
        except sqlite3.OperationalError as e:
            # Check if error is specifically about duplicate column
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                 print(f"Column {col_name} already exists.")
            else:
                 print(f"Could not add {col_name}: {e}")
            
    conn.commit()
    conn.close()
    print("Database fix complete.")

if __name__ == '__main__':
    fix_database_pure()
