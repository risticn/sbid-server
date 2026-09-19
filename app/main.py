from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
import secrets
from pathlib import Path

app = FastAPI()

DB_PATH = "data/sbid.db"


class RegisterRequest(BaseModel):
    android_id: str
    device_name: str | None = None
    app_version: str | None = None


def init_db():
    Path("data").mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            android_id TEXT UNIQUE,
            token TEXT,
            device_name TEXT,
            app_version TEXT,
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


@app.post("/api/v1/register")
def register(request: RegisterRequest):

    token = secrets.token_urlsafe(32)

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM devices
        WHERE android_id = ?
    """, (request.android_id,))

    existing = cursor.fetchone()

    if existing:

        cursor.execute("""
            UPDATE devices
            SET
                token = ?,
                device_name = ?,
                app_version = ?
            WHERE android_id = ?
        """, (
            token,
            request.device_name,
            request.app_version,
            request.android_id
        ))

        device_id = existing[0]

    else:

        cursor.execute("""
            INSERT INTO devices
            (
                android_id,
                token,
                device_name,
                app_version
            )
            VALUES (?, ?, ?, ?)
        """, (
            request.android_id,
            token,
            request.device_name,
            request.app_version
        ))

        device_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "device_id": device_id,
        "token": token
    }


@app.get("/devices")
def devices():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            android_id,
            token,
            device_name,
            app_version,
            created
        FROM devices
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows