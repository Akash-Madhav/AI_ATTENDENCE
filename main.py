# main.py
from db.db import init_database


if __name__ == "__main__":
    try:
        init_database()
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")

    from ui.app import run

    run()
