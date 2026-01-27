from app import app, db
import sqlite3
import os

def fix_database():
    # Use app context to get the correct URI logic, but we might need to manipulate SQL directly if SQLAlchemy models are already updated but DB is not.
    # Actually, simpler: define the path manually or use app.config
    
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    print(f"App DB URI: {db_uri}")
    
    # If it is sqlite:///eye_disease.db, Flask-SQLAlchemy < 3 uses CWD, >= 3 uses instance/
    # Let's check where the file is.
    
    base_dir = os.path.abspath(os.path.dirname(__file__))
    instance_path = os.path.join(base_dir, 'instance', 'eye_disease.db')
    root_path = os.path.join(base_dir, 'eye_disease.db')
    
    target_db = None
    if os.path.exists(instance_path):
        print(f"Found DB at: {instance_path}")
        target_db = instance_path
    elif os.path.exists(root_path):
        print(f"Found DB at: {root_path}")
        target_db = root_path
    else:
        print("No DB file found!")
        return

    conn = sqlite3.connect(target_db)
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
            print(f"Could not add {col_name}: {e}")
            
    conn.commit()
    conn.close()
    print("Database fix complete.")

if __name__ == '__main__':
    fix_database()
