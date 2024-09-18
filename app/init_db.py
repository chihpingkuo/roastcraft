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

cur.execute(
    """
    REPLACE INTO settings(key, value)
    VALUES(?,?)
    """,
    ("device", "ArtisanLog"),
)

cur.execute(
    """
    REPLACE INTO settings(key, value)
    VALUES(?,?)
    """,
    ("serial.port", "COM3"),
)

con.commit()
con.close()
