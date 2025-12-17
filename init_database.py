#!/usr/bin/env python3
"""
Initialize database schema for violations tracking
"""

import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

# Read schema SQL
with open('database/schema.sql', 'r') as f:
    schema_sql = f.read()

# Split into individual statements
statements = [s.strip() for s in schema_sql.split(';') if s.strip()]

try:
    # Connect to MySQL
    conn = pymysql.connect(
        host=os.getenv('MYSQL_HOST'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE')
    )
    
    cursor = conn.cursor()
    
    print(f"Connected to MySQL: {os.getenv('MYSQL_DATABASE')}")
    print(f"Executing {len(statements)} SQL statements...\n")
    
    # Execute each statement
    for i, statement in enumerate(statements, 1):
        try:
            cursor.execute(statement)
            # Get table name from CREATE TABLE statement
            if 'CREATE TABLE' in statement:
                table_name = statement.split('CREATE TABLE')[1].split('(')[0].strip()
                print(f"✓ [{i}/{len(statements)}] Created table: {table_name}")
            else:
                print(f"✓ [{i}/{len(statements)}] Executed statement")
        except Exception as e:
            print(f"✗ [{i}/{len(statements)}] Error: {e}")
    
    conn.commit()
    
    # Verify tables created
    print("\nVerifying tables...")
    cursor.execute("SHOW TABLES LIKE 'violations'")
    if cursor.fetchone():
        print("✓ violations table created")
    
    cursor.execute("SHOW TABLES LIKE 'violation_summary'")
    if cursor.fetchone():
        print("✓ violation_summary table created")
    
    # Show table structures
    print("\n" + "="*60)
    print("violations table structure:")
    print("="*60)
    cursor.execute("DESCRIBE violations")
    for row in cursor.fetchall():
        print(f"  {row[0]:20} {row[1]:20} {row[2]:8} {row[3]:8}")
    
    print("\n" + "="*60)
    print("violation_summary table structure:")
    print("="*60)
    cursor.execute("DESCRIBE violation_summary")
    for row in cursor.fetchall():
        print(f"  {row[0]:20} {row[1]:20} {row[2]:8} {row[3]:8}")
    
    cursor.close()
    conn.close()
    
    print("\n✅ Database initialization complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
