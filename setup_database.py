"""Initialize database schema by reading and executing SQL from db/schema.sql"""

import mysql.connector
from config import CONFIG


def setup_database():
    """Read schema.sql and execute it to create database and tables."""
    
    # Read schema file
    with open('db/schema.sql', 'r') as f:
        schema_content = f.read()
    
    # Connect to MySQL (without specifying database)
    conn = mysql.connector.connect(
        host=CONFIG["DB_HOST"],
        port=CONFIG["DB_PORT"],
        user=CONFIG["DB_USER"],
        password=CONFIG["DB_PASSWORD"],
        autocommit=True
    )
    
    cursor = conn.cursor()
    
    # Split by semicolon and execute each statement
    statements = schema_content.split(';')
    
    for statement in statements:
        statement = statement.strip()
        if statement:  # Skip empty statements
            try:
                cursor.execute(statement)
                print(f"✓ Executed: {statement[:60]}...")
            except Exception as e:
                print(f"✗ Error: {e}")
                print(f"  Statement: {statement[:100]}")
    
    cursor.close()
    conn.close()
    
    print("\n✓ Database schema initialized successfully!")


if __name__ == "__main__":
    try:
        setup_database()
    except Exception as e:
        print(f"✗ Setup failed: {e}")
        print("\nCheck:")
        print("  - MySQL service is running")
        print("  - .env credentials are correct")
        print("  - You can manually run: Get-Content db\\schema.sql | mysql -u root -p")
