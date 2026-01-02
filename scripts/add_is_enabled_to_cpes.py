import sqlite3
import os

# Define path to the database
# Based on app/db/engine_sync.py: DATABASE_FILE = os.path.join(DATA_DIR, "db", "inventory.sqlite")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "db", "inventory.sqlite")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    print(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        print("Checking if 'is_enabled' column exists in 'cpes' table...")
        cursor.execute("PRAGMA table_info(cpes)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "is_enabled" in columns:
            print("'is_enabled' column already exists in 'cpes' table.")
        else:
            print("Adding 'is_enabled' column to 'cpes' table...")
            cursor.execute("ALTER TABLE cpes ADD COLUMN is_enabled INTEGER DEFAULT 1 NOT NULL")
            conn.commit()
            print("Migration successful: Added 'is_enabled' column with default value 1 (True).")

    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
