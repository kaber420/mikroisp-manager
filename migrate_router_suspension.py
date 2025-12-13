# migrate_router_suspension.py
"""
Migration script to add suspension configuration columns to the routers table.
Run this once to update the database schema.
"""
import sqlite3
import os

# Path to database
db_path = os.path.join(os.path.dirname(__file__), "data", "db", "inventory.sqlite")

print(f"Opening database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check which columns already exist
cursor.execute("PRAGMA table_info(routers)")
existing_columns = [col[1] for col in cursor.fetchall()]
print(f"Existing columns: {existing_columns}")

# Add missing columns
columns_to_add = [
    ("suspension_type", 'TEXT DEFAULT "address_list"'),
    ("address_list_name", 'TEXT DEFAULT "morosos"'),
    ("address_list_strategy", 'TEXT DEFAULT "blacklist"'),
]

for col_name, col_def in columns_to_add:
    if col_name not in existing_columns:
        sql = f"ALTER TABLE routers ADD COLUMN {col_name} {col_def}"
        print(f"Adding column: {col_name}")
        cursor.execute(sql)
    else:
        print(f"Column {col_name} already exists, skipping")

conn.commit()
conn.close()

print("✅ Migration completed successfully!")
