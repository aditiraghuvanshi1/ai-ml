"""SQLite data-access layer. Every query is parameterised (no string-built SQL values)."""
import os
import sqlite3
from contextlib import contextmanager
from typing import Optional

# Columns that API callers are allowed to write. Used as a whitelist when building UPDATEs.
WRITABLE_COLUMNS = (
    "name", "date_of_birth", "email", "phone", "course", "address", "enrollment_date",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    date_of_birth   TEXT NOT NULL,
    email           TEXT UNIQUE,
    phone           TEXT,
    course          TEXT,
    address         TEXT,
    enrollment_date TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (email IS NOT NULL OR phone IS NOT NULL)
);
"""


def db_path() -> str:
    """Read the path on every call so tests can point to a temporary database."""
    return os.environ.get("STUDENTS_DB_PATH", "students.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def _row(row: Optional[sqlite3.Row]) -> Optional[dict]:
    return dict(row) if row is not None else None


def create_student(data: dict) -> dict:
    cols = [c for c in WRITABLE_COLUMNS if c in data]
    placeholders = ", ".join("?" for _ in cols)
    sql = f"INSERT INTO students ({', '.join(cols)}) VALUES ({placeholders})"
    with get_conn() as conn:
        cur = conn.execute(sql, [data[c] for c in cols])
        new_id = cur.lastrowid
        return _row(conn.execute("SELECT * FROM students WHERE id = ?", (new_id,)).fetchone())


def get_student(student_id: int) -> Optional[dict]:
    with get_conn() as conn:
        return _row(conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone())


def list_students(
    name: Optional[str] = None,
    course: Optional[str] = None,
    born_after: Optional[str] = None,    # on or after this ISO date
    born_before: Optional[str] = None,   # on or before this ISO date
    limit: int = 50,
    offset: int = 0,
) -> list:
    where, params = [], []
    if name:
        where.append("name LIKE ?")
        params.append(f"%{name}%")
    if course:
        where.append("course LIKE ?")
        params.append(f"%{course}%")
    if born_after:
        where.append("date_of_birth >= ?")
        params.append(born_after)
    if born_before:
        where.append("date_of_birth <= ?")
        params.append(born_before)
    sql = "SELECT * FROM students"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id LIMIT ? OFFSET ?"
    params += [limit, offset]
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def count_students(**filters) -> int:
    where, params = [], []
    if filters.get("course"):
        where.append("course LIKE ?")
        params.append(f"%{filters['course']}%")
    if filters.get("born_after"):
        where.append("date_of_birth >= ?")
        params.append(filters["born_after"])
    if filters.get("born_before"):
        where.append("date_of_birth <= ?")
        params.append(filters["born_before"])
    sql = "SELECT COUNT(*) FROM students"
    if where:
        sql += " WHERE " + " AND ".join(where)
    with get_conn() as conn:
        return conn.execute(sql, params).fetchone()[0]


def distinct_courses() -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT course FROM students WHERE course IS NOT NULL ORDER BY course"
        ).fetchall()
        return [r[0] for r in rows]


def update_student(student_id: int, fields: dict) -> Optional[dict]:
    """Update only the supplied columns. Returns the new row, or None if the id does not exist."""
    cols = [c for c in WRITABLE_COLUMNS if c in fields]
    with get_conn() as conn:
        if cols:
            sets = ", ".join(f"{c} = ?" for c in cols)
            cur = conn.execute(
                f"UPDATE students SET {sets} WHERE id = ?",
                [fields[c] for c in cols] + [student_id],
            )
            if cur.rowcount == 0:
                return None
        return _row(conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone())


def delete_student(student_id: int) -> bool:
    with get_conn() as conn:
        return conn.execute("DELETE FROM students WHERE id = ?", (student_id,)).rowcount > 0
