from pathlib import Path
import hashlib
import secrets
import sqlite3

from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(
    title="SBID API",
    version="1.0.0"
)

DB_PATH = "data/sbid.db"


class RegisterRequest(BaseModel):
    android_id: str = Field(min_length=1, max_length=255)
    device_name: str | None = Field(default=None, max_length=255)
    app_version: str | None = Field(default=None, max_length=50)


class ValidateRequest(BaseModel):
    token: str = Field(min_length=1)


def hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def get_database_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def init_db() -> None:
    Path("data").mkdir(exist_ok=True)

    with get_database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                android_id TEXT NOT NULL UNIQUE,
                token_hash TEXT,
                device_name TEXT,
                app_version TEXT,
                created DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(devices)"
            ).fetchall()
        }

        if "token_hash" not in columns:
            connection.execute(
                """
                ALTER TABLE devices
                ADD COLUMN token_hash TEXT
                """
            )

        if "device_name" not in columns:
            connection.execute(
                """
                ALTER TABLE devices
                ADD COLUMN device_name TEXT
                """
            )

        if "app_version" not in columns:
            connection.execute(
                """
                ALTER TABLE devices
                ADD COLUMN app_version TEXT
                """
            )

        if "token" in columns:
            old_tokens = connection.execute(
                """
                SELECT id, token
                FROM devices
                WHERE token IS NOT NULL
                  AND token != ''
                  AND (
                      token_hash IS NULL
                      OR token_hash = ''
                  )
                """
            ).fetchall()

            for row in old_tokens:
                connection.execute(
                    """
                    UPDATE devices
                    SET token_hash = ?
                    WHERE id = ?
                    """,
                    (
                        hash_token(row["token"]),
                        row["id"]
                    )
                )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_devices_token_hash
            ON devices(token_hash)
            """
        )

        connection.commit()


init_db()


@app.get("/")
def root():
    return {
        "service": "SBID API",
        "database": DB_PATH
    }


@app.get("/health")
def health():
    try:
        with get_database_connection() as connection:
            connection.execute("SELECT 1").fetchone()

        return {
            "status": "ok",
            "database": "available"
        }

    except sqlite3.Error:
        return {
            "status": "degraded",
            "database": "unavailable"
        }


@app.post("/api/v1/register")
def register(request: RegisterRequest):
    android_id = request.android_id.strip()

    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)

    with get_database_connection() as connection:
        existing = connection.execute(
            """
            SELECT id
            FROM devices
            WHERE android_id = ?
            """,
            (android_id,)
        ).fetchone()

        if existing:
            connection.execute(
                """
                UPDATE devices
                SET
                    token_hash = ?,
                    device_name = ?,
                    app_version = ?
                WHERE android_id = ?
                """,
                (
                    token_hash,
                    request.device_name,
                    request.app_version,
                    android_id
                )
            )

            device_id = existing["id"]
            registered = False

        else:
            cursor = connection.execute(
                """
                INSERT INTO devices (
                    android_id,
                    token_hash,
                    device_name,
                    app_version
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    android_id,
                    token_hash,
                    request.device_name,
                    request.app_version
                )
            )

            device_id = cursor.lastrowid
            registered = True

        connection.commit()

    return {
        "device_id": device_id,
        "token": token,
        "token_type": "Bearer",
        "registered": registered
    }


@app.post("/api/v1/validate")
def validate(request: ValidateRequest):
    submitted_token_hash = hash_token(request.token)

    with get_database_connection() as connection:
        device = connection.execute(
            """
            SELECT
                id,
                android_id
            FROM devices
            WHERE token_hash = ?
            """,
            (submitted_token_hash,)
        ).fetchone()

    if device:
        return {
            "valid": True,
            "device_id": device["id"],
            "android_id": device["android_id"]
        }

    return {
        "valid": False
    }


@app.get("/devices")
def devices():
    with get_database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                android_id,
                device_name,
                app_version,
                created
            FROM devices
            ORDER BY id
            """
        ).fetchall()

    return [
        {
            "id": row["id"],
            "android_id": row["android_id"],
            "device_name": row["device_name"],
            "app_version": row["app_version"],
            "created": row["created"]
        }
        for row in rows
    ]