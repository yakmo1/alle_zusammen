"""
Database Manager für PostgreSQL
Verwaltet Verbindungen, Connection Pooling und Queries
"""

import psycopg2
from psycopg2 import pool, extras
from psycopg2.extensions import connection, cursor
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
import time

from ..utils.logger import get_logger, log_exception
from ..utils.config_loader import get_config

class DatabaseManager:
    """PostgreSQL Database Manager mit Connection Pooling"""

    def __init__(self, db_type: str = 'local'):
        """
        Initialisiert den Database Manager

        Args:
            db_type: 'local' oder 'remote'
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        self.db_type = db_type

        # Database Config laden
        self.db_config = self.config.get_database_config(db_type)

        # Connection Pool
        self.pool = None
        self._init_pool()

    def _init_pool(self):
        """Initialisiert den Connection Pool"""
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.db_config.get('pool_size', 5),
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            self.logger.info(f"Database pool initialized ({self.db_type}): {self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}")
        except Exception as e:
            log_exception(self.logger, e, "Failed to initialize database pool")
            raise

    @contextmanager
    def get_connection(self):
        """
        Context Manager für Database Connection

        Yields:
            psycopg2.connection
        """
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            log_exception(self.logger, e, "Database connection error")
            raise
        finally:
            if conn:
                self.pool.putconn(conn)

    @contextmanager
    def get_cursor(self, dict_cursor: bool = False):
        """
        Context Manager für Database Cursor

        Args:
            dict_cursor: Wenn True, Dictionary Cursor verwenden

        Yields:
            psycopg2.cursor
        """
        with self.get_connection() as conn:
            if dict_cursor:
                cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            else:
                cur = conn.cursor()

            try:
                yield cur
            finally:
                cur.close()

    def execute(self, query: str, params: tuple = None) -> None:
        """
        Führt Query aus (INSERT, UPDATE, DELETE)

        Args:
            query: SQL Query
            params: Query Parameter
        """
        with self.get_cursor() as cur:
            cur.execute(query, params)

    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """
        Führt Query mehrfach aus (Batch)

        Args:
            query: SQL Query
            params_list: Liste von Query Parametern
        """
        with self.get_cursor() as cur:
            extras.execute_batch(cur, query, params_list)

    def fetch_one(self, query: str, params: tuple = None) -> Optional[Tuple]:
        """
        Holt einen einzelnen Row

        Args:
            query: SQL Query
            params: Query Parameter

        Returns:
            Row als Tuple oder None
        """
        with self.get_cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def fetch_all(self, query: str, params: tuple = None) -> List[Tuple]:
        """
        Holt alle Rows

        Args:
            query: SQL Query
            params: Query Parameter

        Returns:
            Liste von Rows als Tuples
        """
        with self.get_cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def fetch_dict(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """
        Holt einen einzelnen Row als Dictionary

        Args:
            query: SQL Query
            params: Query Parameter

        Returns:
            Row als Dictionary oder None
        """
        with self.get_cursor(dict_cursor=True) as cur:
            cur.execute(query, params)
            result = cur.fetchone()
            return dict(result) if result else None

    def fetch_all_dict(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        Holt alle Rows als Dictionaries

        Args:
            query: SQL Query
            params: Query Parameter

        Returns:
            Liste von Rows als Dictionaries
        """
        with self.get_cursor(dict_cursor=True) as cur:
            cur.execute(query, params)
            results = cur.fetchall()
            return [dict(row) for row in results] if results else []

    def table_exists(self, table_name: str) -> bool:
        """
        Prüft ob Tabelle existiert

        Args:
            table_name: Tabellenname

        Returns:
            True wenn Tabelle existiert
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """
        result = self.fetch_one(query, (table_name,))
        return result[0] if result else False

    def create_table_if_not_exists(self, create_query: str) -> None:
        """
        Erstellt Tabelle wenn sie nicht existiert

        Args:
            create_query: CREATE TABLE Query
        """
        self.execute(create_query)

    def get_table_row_count(self, table_name: str) -> int:
        """
        Holt Anzahl Rows in Tabelle

        Args:
            table_name: Tabellenname

        Returns:
            Anzahl Rows
        """
        query = f"SELECT COUNT(*) FROM {table_name}"
        result = self.fetch_one(query)
        return result[0] if result else 0

    def get_table_size(self, table_name: str) -> str:
        """
        Holt Größe der Tabelle

        Args:
            table_name: Tabellenname

        Returns:
            Größe als String (z.B. "10 MB")
        """
        query = "SELECT pg_size_pretty(pg_total_relation_size(%s))"
        result = self.fetch_one(query, (table_name,))
        return result[0] if result else "0 bytes"

    def list_tables(self) -> List[str]:
        """
        Listet alle Tabellen auf

        Returns:
            Liste von Tabellennamen
        """
        query = """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """
        results = self.fetch_all(query)
        return [row[0] for row in results] if results else []

    def vacuum_table(self, table_name: str) -> None:
        """
        Führt VACUUM auf Tabelle aus

        Args:
            table_name: Tabellenname
        """
        with self.get_connection() as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(f"VACUUM ANALYZE {table_name}")
            conn.autocommit = False

    def test_connection(self) -> bool:
        """
        Testet Database Verbindung

        Returns:
            True wenn Verbindung erfolgreich
        """
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                return result[0] == 1
        except Exception as e:
            log_exception(self.logger, e, "Connection test failed")
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Holt Connection Informationen

        Returns:
            Dictionary mit Connection Info
        """
        return {
            'type': self.db_type,
            'host': self.db_config['host'],
            'port': self.db_config['port'],
            'database': self.db_config['database'],
            'user': self.db_config['user'],
            'pool_size': self.db_config.get('pool_size', 5)
        }

    def close(self):
        """Schließt alle Verbindungen"""
        if self.pool:
            self.pool.closeall()
            self.logger.info(f"Database pool closed ({self.db_type})")

    def __enter__(self):
        """Context Manager Enter"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Exit"""
        self.close()

    def __repr__(self) -> str:
        """String Representation"""
        return f"DatabaseManager(type={self.db_type}, host={self.db_config['host']})"


# Singleton Instances
_db_local = None
_db_remote = None

def get_database(db_type: str = 'local') -> DatabaseManager:
    """
    Holt Database Manager Instance

    Args:
        db_type: 'local' oder 'remote'

    Returns:
        DatabaseManager Instance
    """
    global _db_local, _db_remote

    if db_type == 'local':
        if _db_local is None:
            _db_local = DatabaseManager('local')
        return _db_local
    elif db_type == 'remote':
        if _db_remote is None:
            _db_remote = DatabaseManager('remote')
        return _db_remote
    else:
        raise ValueError(f"Invalid db_type: {db_type}")


if __name__ == "__main__":
    # Test
    print("=== Database Manager Test ===\n")

    try:
        db = DatabaseManager('local')

        print("Connection Info:")
        print(db.get_connection_info())

        print("\nTesting connection...")
        if db.test_connection():
            print("✓ Connection successful")
        else:
            print("✗ Connection failed")

        print("\nListing tables:")
        tables = db.list_tables()
        for table in tables[:10]:  # Erste 10
            print(f"  - {table}")

        db.close()

    except Exception as e:
        print(f"✗ Error: {e}")
