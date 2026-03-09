import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "patches.db"


@dataclass
class Patch:
    """A saved patch retrieved from the database."""

    id: int
    name: str
    synth: str
    description: str | None
    settings: dict[str, int]
    created_at: datetime
    updated_at: datetime


class PatchLibrary:
    """SQLite-backed storage for synth patches."""

    def __init__(self, db_path: Path = _DEFAULT_DB_PATH):
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc):
        self.close()

    def open(self):
        """Open the database connection and ensure the schema exists."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def close(self):
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not open — call open() first")
        return self._conn

    def _create_schema(self):
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS patches (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                synth TEXT NOT NULL,
                description TEXT,
                settings TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._db.commit()

    def save(
        self,
        name: str,
        synth: str,
        settings: dict[str, int],
        description: str | None = None,
    ) -> Patch:
        """Save a patch. If a patch with this name exists, update it."""
        settings_json = json.dumps(settings)
        now = datetime.now().isoformat()
        try:
            self._db.execute(
                """INSERT INTO patches (name, synth, description, settings, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, synth, description, settings_json, now, now),
            )
        except sqlite3.IntegrityError:
            self._db.execute(
                """UPDATE patches SET synth=?, description=?, settings=?, updated_at=?
                   WHERE name=?""",
                (synth, description, settings_json, now, name),
            )
        self._db.commit()
        return self.get(name)  # type: ignore[return-value]

    def get(self, name: str) -> Patch | None:
        """Get a patch by name. Returns None if not found."""
        row = self._db.execute("SELECT * FROM patches WHERE name = ?", (name,)).fetchone()
        if row is None:
            return None
        return self._row_to_patch(row)

    def list(self, synth: str | None = None) -> list[Patch]:
        """List all patches, optionally filtered by synth name."""
        if synth:
            rows = self._db.execute(
                "SELECT * FROM patches WHERE LOWER(synth) = ? ORDER BY updated_at DESC",
                (synth.lower(),),
            ).fetchall()
        else:
            rows = self._db.execute("SELECT * FROM patches ORDER BY updated_at DESC").fetchall()
        return [self._row_to_patch(row) for row in rows]

    def delete(self, name: str) -> bool:
        """Delete a patch by name. Returns True if a patch was deleted."""
        cursor = self._db.execute("DELETE FROM patches WHERE name = ?", (name,))
        self._db.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _row_to_patch(row: sqlite3.Row) -> Patch:
        return Patch(
            id=row["id"],
            name=row["name"],
            synth=row["synth"],
            description=row["description"],
            settings=json.loads(row["settings"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
