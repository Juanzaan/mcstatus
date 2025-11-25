"""
Database Migration Runner
Applies SQL migrations to the database
"""

import sqlite3
import os
from pathlib import Path

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "servers.db")
MIGRATIONS_DIR = Path(__file__).parent

def run_migration(migration_file: str):
    """Run a single migration file"""
    print(f"Running migration: {migration_file}")
    
    with open(MIGRATIONS_DIR / migration_file, 'r') as f:
        sql = f.read()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Execute migration
    try:
        cursor.executescript(sql)
        conn.commit()
        print(f"✅ Migration {migration_file} applied successfully")
    except sqlite3.Error as e:
        print(f"❌ Migration {migration_file} failed: {e}")
        conn.rollback()
    finally:
        conn.close()

def run_all_migrations():
    """Run all pending migrations"""
    migrations = sorted([f for f in os.listdir(MIGRATIONS_DIR) if f.endswith('.sql')])
    
    print(f"Found {len(migrations)} migration(s)")
    
    for migration in migrations:
        run_migration(migration)
    
    print("\n✅ All migrations complete")

if __name__ == "__main__":
    run_all_migrations()
