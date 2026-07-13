import sqlite3
from datetime import datetime


class TermLearningQueue:
    def __init__(self, db_path):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        conn = self._connect()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS term_learning_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT,
                    raw_message TEXT,
                    frank_answer TEXT,
                    user_feedback TEXT,
                    related_scene TEXT,
                    status TEXT,
                    created_at TEXT,
                    resolved_at TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def record_term(self, term, raw_message, frank_answer="", user_feedback="", related_scene="", status="new"):
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO term_learning_queue
                (term, raw_message, frank_answer, user_feedback, related_scene, status, created_at, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                term, raw_message, frank_answer, user_feedback, related_scene,
                status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), None
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def list_pending(self):
        return self._list("WHERE status IN ('new', 'needs_review') ORDER BY id DESC")

    def list_recent(self, limit=10):
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM term_learning_queue ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def _list(self, clause):
        conn = self._connect()
        try:
            rows = conn.execute(f"SELECT * FROM term_learning_queue {clause}").fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def export_records(self):
        rows = self.list_recent(limit=1000)
        lines = ["# Term Learning Queue", ""]
        for row in rows:
            lines.append(f"- {row['term']} | {row['related_scene']} | {row['status']} | {row['raw_message']}")
        return "\n".join(lines)
