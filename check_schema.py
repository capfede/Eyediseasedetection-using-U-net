import sqlite3

def check_schema():
    conn = sqlite3.connect('eye_disease.db')
    cursor = conn.cursor()
    
    # List tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", tables)
    
    for table in tables:
        t_name = table[0]
        print(f"\nColumns in '{t_name}':")
        cursor.execute(f"PRAGMA table_info({t_name})")
        print(cursor.fetchall())
        
    conn.close()

if __name__ == '__main__':
    check_schema()
