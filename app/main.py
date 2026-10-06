from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from pathlib import Path
from typing import Annotated

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR.parent / "diary.db"))
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-in-production")

app = FastAPI(title="Школьный дневник")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


class AuthPayload(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


def connect_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), 120_000
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def make_session(user_id: int) -> str:
    payload = str(user_id)
    signature = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def get_user_id(session: str | None) -> int | None:
    if not session or "." not in session:
        return None
    user_id, signature = session.split(".", 1)
    expected = hmac.new(SECRET_KEY.encode(), user_id.encode(), hashlib.sha256).hexdigest()
    if not user_id.isdigit() or not hmac.compare_digest(signature, expected):
        return None
    return int(user_id)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def home() -> FileResponse:
    return FileResponse(BASE_DIR / "templates" / "index.html")


@app.post("/api/register")
def register(payload: AuthPayload, response: Response) -> dict:
    name = (payload.name or "").strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Введите имя минимум из 2 символов")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Пароль должен содержать минимум 6 символов")
    try:
        with connect_db() as connection:
            cursor = connection.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, payload.email.lower(), hash_password(payload.password)),
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Пользователь с этой почтой уже зарегистрирован")

    response.set_cookie("session", make_session(user_id), httponly=True, samesite="lax", secure=COOKIE_SECURE, max_age=60 * 60 * 24 * 30)
    return {"message": "Регистрация прошла успешно", "user": {"name": name, "email": payload.email.lower()}}


@app.post("/api/login")
def login(payload: AuthPayload, response: Response) -> dict:
    with connect_db() as connection:
        user = connection.execute("SELECT * FROM users WHERE email = ?", (payload.email.lower(),)).fetchone()
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Неверная почта или пароль")
    response.set_cookie("session", make_session(user["id"]), httponly=True, samesite="lax", secure=COOKIE_SECURE, max_age=60 * 60 * 24 * 30)
    return {"message": "Вход выполнен", "user": {"name": user["name"], "email": user["email"]}}


@app.post("/api/logout")
def logout(response: Response) -> dict:
    response.delete_cookie("session")
    return {"message": "Вы вышли из аккаунта"}


@app.get("/api/me")
def me(session: Annotated[str | None, Cookie()] = None) -> JSONResponse:
    user_id = get_user_id(session)
    if not user_id:
        return JSONResponse({"authenticated": False})
    with connect_db() as connection:
        user = connection.execute("SELECT name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return JSONResponse({"authenticated": False})
    return JSONResponse({"authenticated": True, "user": dict(user)})
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
