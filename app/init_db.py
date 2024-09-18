import sqlite3

con = sqlite3.connect("roastcraft.db")
cur = con.cursor()

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS settings 
    ( 
        key   TEXT  PRIMARY KEY, 
        value TEXT 
    ); 
    """
)
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS sessions
    (
        session_id INTEGER PRIMARY KEY,
        name TEXT,
        timestamp TEXT,
        data BLOB
    );
    """
)

con.close()
