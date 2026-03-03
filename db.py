import sqlite3

def get_db():
    conn = sqlite3.connect("sales.db", check_same_thread=False)
    return conn
