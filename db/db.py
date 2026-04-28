# db/db.py
import mysql.connector
from mysql.connector import pooling
from config import CONFIG

# Connection pool — reused across all service calls
_pool = pooling.MySQLConnectionPool(
    pool_name="attendance_pool",
    pool_size=5,
    host=CONFIG["DB_HOST"],
    port=int(CONFIG["DB_PORT"]),
    database=CONFIG["DB_NAME"],
    user=CONFIG["DB_USER"],
    password=CONFIG["DB_PASSWORD"],
    autocommit=False,
)

def get_connection():
    """Get a connection from the pool. Always use as context manager."""
    return _pool.get_connection()
