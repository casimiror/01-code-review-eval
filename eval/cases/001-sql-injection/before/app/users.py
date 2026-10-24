import sqlite3


def get_connection(path: str = "app.db") -> sqlite3.Connection:
    return sqlite3.connect(path)


def list_users(conn: sqlite3.Connection) -> list[tuple]:
    return conn.execute("SELECT id, name FROM users ORDER BY id").fetchall()
