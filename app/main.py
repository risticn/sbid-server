from fastapi import FastAPI
import sqlite3
from pathlib import Path

app = FastAPI()

DB_PATH = "data/sbid.db"


def init_db():
    Path("data").mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            android_id TEXT UNIQUE,
            token TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


init_db()


@app.get("/")
def root():
    return {
        "service": "SBID API",
        "database": DB_PATH
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.get("/devices")
def get_devices():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            android_id,
            token,
            created
        FROM devices
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows