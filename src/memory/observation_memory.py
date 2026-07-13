import json
import sqlite3
from datetime import datetime


class ObservationMemory:
    def __init__(self, db_path):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date TEXT,
                    market_summary TEXT,
                    data_timestamp TEXT,
                    created_at TEXT,
                    status TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observation_boards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    board_name TEXT,
                    board_level TEXT,
                    reason TEXT,
                    risk_note TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observation_stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    board_id INTEGER,
                    symbol TEXT,
                    name TEXT,
                    reason TEXT,
                    observe_conditions TEXT,
                    invalidation_conditions TEXT,
                    status TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS observation_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_id INTEGER,
                    review_date TEXT,
                    price_snapshot TEXT,
                    condition_results TEXT,
                    conclusion TEXT,
                    lesson TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def create_run(self, trade_date, market_summary, data_timestamp, status):
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO observation_runs (trade_date, market_summary, data_timestamp, created_at, status)
                VALUES (?, ?, ?, ?, ?)
            """, (trade_date, market_summary, data_timestamp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def add_board(self, run_id, board_name, board_level, reason, risk_note):
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO observation_boards (run_id, board_name, board_level, reason, risk_note)
                VALUES (?, ?, ?, ?, ?)
            """, (run_id, board_name, board_level, reason, risk_note))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def add_stock(self, run_id, board_id, symbol, name, reason, observe_conditions, invalidation_conditions, status="observing"):
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO observation_stocks
                (run_id, board_id, symbol, name, reason, observe_conditions, invalidation_conditions, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, board_id, symbol, name, reason,
                json.dumps(observe_conditions, ensure_ascii=False),
                json.dumps(invalidation_conditions, ensure_ascii=False),
                status
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def add_review(self, stock_id, review_date, price_snapshot, condition_results, conclusion, lesson):
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO observation_reviews
                (stock_id, review_date, price_snapshot, condition_results, conclusion, lesson)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                stock_id, review_date,
                json.dumps(price_snapshot, ensure_ascii=False),
                json.dumps(condition_results, ensure_ascii=False),
                conclusion, lesson
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_run(self, run_id):
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM observation_runs WHERE id = ?", (run_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_recent_runs(self, limit=5):
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM observation_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def list_stocks(self, run_id):
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM observation_stocks WHERE run_id = ? ORDER BY id", (run_id,)).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
