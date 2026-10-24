import sqlite3


def get_connection(path: str = "app.db") -> sqlite3.Connection:
    return sqlite3.connect(path)


def list_users(conn: sqlite3.Connection) -> list[tuple]:
    return conn.execute("SELECT id, name FROM users ORDER BY id").fetchall()


def find_users_by_name(conn: sqlite3.Connection, name: str) -> list[tuple]:
    query = f"SELECT id, name FROM users WHERE name LIKE '%{name}%'"
    return conn.execute(query).fetchall()
