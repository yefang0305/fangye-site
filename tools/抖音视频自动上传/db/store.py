"""SQLite data access layer for MediaPush.

All methods return plain dicts/lists; sqlite3 objects never leak out.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


_SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id     INTEGER NOT NULL REFERENCES groups(id),
    platform     TEXT NOT NULL,
    display_name TEXT NOT NULL,
    profile_path TEXT NOT NULL,
    is_active    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS tasks (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    video_path     TEXT NOT NULL,
    group_id       INTEGER NOT NULL REFERENCES groups(id),
    scheduled_time TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id       INTEGER NOT NULL REFERENCES tasks(id),
    account_id    INTEGER NOT NULL REFERENCES accounts(id),
    status        TEXT NOT NULL DEFAULT 'pending',
    error_msg     TEXT,
    submitted_at  TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 1,
    next_retry_at TEXT
);
"""


class Store:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Idempotent column additions for older DBs created before retry support."""
        cols = {row[1] for row in self._conn.execute("PRAGMA table_info(task_logs)")}
        if "attempt_count" not in cols:
            self._conn.execute("ALTER TABLE task_logs ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 1")
        if "next_retry_at" not in cols:
            self._conn.execute("ALTER TABLE task_logs ADD COLUMN next_retry_at TEXT")

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return {k: row[k] for k in row.keys()}

    # ---- groups ----
    def create_group(self, name: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO groups (name, created_at) VALUES (?, ?)",
            (name, self._now()),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def list_groups(self) -> list[dict]:
        rows = self._conn.execute("SELECT id, name, created_at FROM groups ORDER BY id").fetchall()
        return [self._row_to_dict(r) for r in rows]

    def rename_group(self, group_id: int, new_name: str) -> None:
        self._conn.execute("UPDATE groups SET name = ? WHERE id = ?", (new_name, group_id))
        self._conn.commit()

    def delete_group(self, group_id: int) -> None:
        """Delete a group. Caller must ensure no accounts reference it."""
        if self._conn.execute("SELECT 1 FROM accounts WHERE group_id = ? LIMIT 1", (group_id,)).fetchone():
            raise ValueError(f"group {group_id} still has accounts")
        self._conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        self._conn.commit()

    # ---- accounts ----
    def add_account(self, group_id: int, platform: str, display_name: str, profile_path: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO accounts (group_id, platform, display_name, profile_path) VALUES (?, ?, ?, ?)",
            (group_id, platform, display_name, profile_path),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def list_accounts(self, group_id: Optional[int] = None) -> list[dict]:
        if group_id is None:
            rows = self._conn.execute("SELECT * FROM accounts ORDER BY id").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM accounts WHERE group_id = ? ORDER BY id", (group_id,)
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def update_account_active(self, account_id: int, is_active: int) -> None:
        self._conn.execute("UPDATE accounts SET is_active = ? WHERE id = ?", (is_active, account_id))
        self._conn.commit()

    def delete_account(self, account_id: int) -> None:
        self._conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        self._conn.commit()

    def update_account_display_name(self, account_id: int, name: str) -> None:
        self._conn.execute("UPDATE accounts SET display_name = ? WHERE id = ?", (name, account_id))
        self._conn.commit()

    def move_account_to_group(self, account_id: int, new_group_id: int) -> None:
        self._conn.execute("UPDATE accounts SET group_id = ? WHERE id = ?", (new_group_id, account_id))
        self._conn.commit()

    # ---- tasks ----
    def create_task(self, video_path: str, group_id: int, scheduled_time: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO tasks (video_path, group_id, scheduled_time, created_at) VALUES (?, ?, ?, ?)",
            (video_path, group_id, scheduled_time, self._now()),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def update_task_status(self, task_id: int, status: str) -> None:
        self._conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        self._conn.commit()

    def list_tasks(self, status: Optional[str] = None) -> list[dict]:
        if status is None:
            rows = self._conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM tasks WHERE status = ? ORDER BY id", (status,)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    # ---- task_logs ----
    def create_task_log(self, task_id: int, account_id: int) -> int:
        cur = self._conn.execute(
            "INSERT INTO task_logs (task_id, account_id) VALUES (?, ?)",
            (task_id, account_id),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def update_task_log_status(self, log_id: int, status: str, error_msg: Optional[str] = None) -> None:
        submitted_at = self._now() if status == "submitted" else None
        self._conn.execute(
            "UPDATE task_logs SET status = ?, error_msg = ?, submitted_at = ? WHERE id = ?",
            (status, error_msg, submitted_at, log_id),
        )
        self._conn.commit()

    def update_task_log_for_retry(self, log_id: int, next_retry_at: str) -> None:
        """Schedule a failed log for an automatic retry at the given ISO time.
        Status stays 'failed' until the sweeper picks it up."""
        self._conn.execute(
            "UPDATE task_logs SET next_retry_at = ? WHERE id = ?",
            (next_retry_at, log_id),
        )
        self._conn.commit()

    def list_task_logs_due_for_retry(self, now_iso: str) -> list[dict]:
        """Return failed logs whose next_retry_at has arrived."""
        rows = self._conn.execute(
            "SELECT * FROM task_logs WHERE status = 'failed' AND next_retry_at IS NOT NULL "
            "AND next_retry_at <= ? ORDER BY id",
            (now_iso,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def bump_attempt_and_requeue(self, log_id: int, new_attempt_count: int) -> None:
        """Reset a failed log back to pending for a fresh upload attempt."""
        self._conn.execute(
            "UPDATE task_logs SET status = 'pending', error_msg = NULL, "
            "next_retry_at = NULL, attempt_count = ? WHERE id = ?",
            (new_attempt_count, log_id),
        )
        self._conn.commit()

    def list_task_logs(self, task_id: Optional[int] = None) -> list[dict]:
        if task_id is None:
            rows = self._conn.execute("SELECT * FROM task_logs ORDER BY id").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM task_logs WHERE task_id = ? ORDER BY id", (task_id,)
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def delete_task_logs(self, log_ids: list[int]) -> dict:
        """Delete task_log rows by id and remove tasks left without logs.

        This is a history cleanup operation only; it intentionally does not
        delete video files from disk.
        """
        ids = sorted({int(i) for i in log_ids})
        if not ids:
            return {"task_logs": 0, "tasks": 0}

        placeholders = ",".join("?" for _ in ids)
        cur = self._conn.execute(
            f"DELETE FROM task_logs WHERE id IN ({placeholders})",
            ids,
        )
        deleted_logs = cur.rowcount if cur.rowcount is not None else 0

        cur = self._conn.execute(
            """
            DELETE FROM tasks
            WHERE id NOT IN (SELECT DISTINCT task_id FROM task_logs)
            """
        )
        deleted_tasks = cur.rowcount if cur.rowcount is not None else 0
        self._conn.commit()
        return {"task_logs": deleted_logs, "tasks": deleted_tasks}

    def purge_submitted_history_before(self, cutoff_date: str) -> dict:
        """Delete submitted history rows before cutoff_date (YYYY-MM-DD).

        The history date is the scheduled publish date when present; immediate
        publishes fall back to submitted_at, then task created_at. Failed,
        pending, and uploading rows are intentionally kept so users can still
        inspect and retry actionable records.
        """
        cur = self._conn.execute(
            """
            DELETE FROM task_logs
            WHERE id IN (
                SELECT tl.id
                FROM task_logs tl
                JOIN tasks t ON t.id = tl.task_id
                WHERE tl.status = 'submitted'
                  AND date(
                      COALESCE(
                          NULLIF(t.scheduled_time, ''),
                          NULLIF(tl.submitted_at, ''),
                          t.created_at
                      )
                  ) < date(?)
            )
            """,
            (cutoff_date,),
        )
        deleted_logs = cur.rowcount if cur.rowcount is not None else 0

        cur = self._conn.execute(
            """
            DELETE FROM tasks
            WHERE id NOT IN (SELECT DISTINCT task_id FROM task_logs)
            """
        )
        deleted_tasks = cur.rowcount if cur.rowcount is not None else 0
        self._conn.commit()
        return {"task_logs": deleted_logs, "tasks": deleted_tasks}
