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
        print("Checking if 'price' column exists...")
        cursor.execute("PRAGMA table_info(plans)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "price" in columns:
            print("'price' column already exists in 'plans' table.")
        else:
            print("Adding 'price' column to 'plans' table...")
            cursor.execute("ALTER TABLE plans ADD COLUMN price FLOAT DEFAULT 0.0")
            conn.commit()
            print("Migration successful: Added 'price' column.")

    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
