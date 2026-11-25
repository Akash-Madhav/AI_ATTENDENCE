# db/db.py
from pathlib import Path
import re
import mysql.connector
from mysql.connector import errorcode, pooling
from config import CONFIG

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
_pool = None


def _validate_db_name(db_name: str) -> str:
    """Ensure database name only contains safe identifier characters."""
    if not re.fullmatch(r"[A-Za-z0-9_]+", db_name):
        raise ValueError(f"Invalid database name: {db_name!r}")
    return db_name


def _parse_schema_statements(schema_sql: str) -> list[str]:
    """Strip SQL line comments and split schema SQL into executable statements."""
    cleaned_lines = [
        line for line in schema_sql.splitlines()
        if not line.lstrip().startswith("--")
    ]
    cleaned_sql = "\n".join(cleaned_lines)
    return [stmt.strip() for stmt in cleaned_sql.split(";") if stmt.strip()]


def init_database(verbose: bool = False) -> None:
    """Create the configured database and execute base schema queries if missing."""
    db_name = _validate_db_name(CONFIG["DB_NAME"])
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    statements = _parse_schema_statements(schema_sql)

    conn = mysql.connector.connect(
        host=CONFIG["DB_HOST"],
        port=int(CONFIG["DB_PORT"]),
        user=CONFIG["DB_USER"],
        password=CONFIG["DB_PASSWORD"],
        autocommit=True,
    )
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{db_name}`")
        if verbose:
            print(f"[OK] Database '{db_name}' ready.")

        for statement in statements:
            upper = statement.upper()
            # Database creation and selection are already handled using CONFIG["DB_NAME"]
            if upper.startswith("CREATE DATABASE") or upper.startswith("USE "):
                continue
            try:
                cursor.execute(statement)
                if verbose:
                    first_line = statement.splitlines()[0][:60]
                    print(f"[OK] Executed: {first_line}...")
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_DUP_KEYNAME:
                    continue
                raise
    finally:
        cursor.close()
        conn.close()


def _get_pool() -> pooling.MySQLConnectionPool:
    """Lazily initialize the connection pool after ensuring the schema exists."""
    global _pool
    if _pool is None:
        init_database()
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
    return _pool


def get_connection():
    """Get a connection from the pool. Always use as context manager."""
    return _get_pool().get_connection()
