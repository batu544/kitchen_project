import psycopg2

DB_CONFIG = {
    "database": "kitchen",
    "user": "prasanta",
    "password": "prasanta",
    "host": "127.0.0.1",
    "port": "5432",
}


def db_connect():
    # Database connection
    conn = psycopg2.connect(**DB_CONFIG)
    # create a cursor
    cursor = conn.cursor()
    return cursor, conn


def close_connection(cursor, conn):
    conn.commit()
    cursor.close()
    conn.close()
