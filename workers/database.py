"""
Database connection and operations module
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
import logging
from config import DATABASE_URL

logger = logging.getLogger(__name__)

# Connection pool
connection_pool = None


def init_db_pool(minconn=1, maxconn=10):
    """Initialize database connection pool"""
    global connection_pool
    try:
        connection_pool = SimpleConnectionPool(
            minconn,
            maxconn,
            DATABASE_URL
        )
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Error initializing database pool: {e}")
        raise


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    connection = None
    try:
        if connection_pool is None:
            init_db_pool()
        connection = connection_pool.getconn()
        yield connection
    finally:
        if connection:
            connection_pool.putconn(connection)


def create_request(quantity, digits):
    """Create a new prime generation request"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                INSERT INTO requests (quantity, digits, status)
                VALUES (%s, %s, 'pending')
                RETURNING id, quantity, digits, status, created_at
                """,
                (quantity, digits)
            )
            result = cursor.fetchone()
            conn.commit()
            return dict(result)


def get_request_status(request_id):
    """Get the status of a request"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT r.id, r.quantity, r.digits, r.status, r.created_at,
                       COUNT(p.id) as generated_count
                FROM requests r
                LEFT JOIN prime_numbers p ON r.id = p.request_id
                WHERE r.id = %s
                GROUP BY r.id, r.quantity, r.digits, r.status, r.created_at
                """,
                (request_id,)
            )
            result = cursor.fetchone()
            return dict(result) if result else None


def get_request_results(request_id):
    """Get all generated prime numbers for a request"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT prime_value, created_at
                FROM prime_numbers
                WHERE request_id = %s
                ORDER BY created_at
                """,
                (request_id,)
            )
            results = cursor.fetchall()
            return [dict(row) for row in results]


def add_prime_number(request_id, prime_value):
    """Add a generated prime number to the database"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO prime_numbers (request_id, prime_value)
                    VALUES (%s, %s)
                    ON CONFLICT (request_id, prime_value) DO NOTHING
                    """,
                    (request_id, str(prime_value))
                )
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                conn.rollback()
                logger.error(f"Error adding prime number: {e}")
                raise


def update_request_status(request_id, status):
    """Update the status of a request"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE requests
                SET status = %s
                WHERE id = %s
                """,
                (status, request_id)
            )
            conn.commit()


def close_db_pool():
    """Close all connections in the pool"""
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        logger.info("Database connection pool closed")
