"""Initialize database schema by reading and executing SQL from db/schema.sql."""

from db.db import init_database


def setup_database():
    """Ensure the configured database and all base tables/indexes exist."""
    init_database(verbose=True)
    print("\nDatabase schema initialized successfully!")


if __name__ == "__main__":
    try:
        setup_database()
    except Exception as e:
        print(f"Setup failed: {e}")
        print("\nCheck:")
        print("  - MySQL service is running")
        print("  - .env credentials are correct")
        print("  - You can manually run: Get-Content db\\schema.sql | mysql -u root -p")
