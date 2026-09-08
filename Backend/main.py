import mysql.connector
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
import os

from database import init_db, get_db_connection
from routers import connections, messages, websocket, sos, doctor_search, medicines

app = FastAPI(title="SpaceNXT Elderly Care Backend", version="2.0.0")
router = APIRouter()

# =========================
# INITIALIZE DATABASE SCHEMA
# =========================
@app.on_event("startup")
def on_startup():
    try:
        init_db()
    except Exception as e:
        print(f"Warning on startup DB init: {e}")


# =========================
# REQUEST MODEL - USERS
# =========================

class UserCreate(BaseModel):
    firebase_uid: str
    name: str
    email: str

    phone: Optional[str] = None
    role: str

    profile_image: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None


# =========================
# REQUEST MODEL - REGISTERED USER
# =========================

class RegisteredUserCreate(BaseModel):
    firebase_uid: str
    email: str


# =========================
# GET ALL USERS
# =========================

@router.get("/users")
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users


# =========================
# CREATE USER
# =========================

@router.post("/users")
def create_user(user: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO users
        (
            firebase_uid,
            name,
            email,
            phone,
            role,
            profile_image,
            date_of_birth,
            gender,
            address
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
    """

    values = (
        user.firebase_uid,
        user.name,
        user.email,
        user.phone,
        user.role,
        user.profile_image,
        user.date_of_birth,
        user.gender,
        user.address
    )

    cursor.execute(query, values)
    conn.commit()
    user_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return {
        "message": "User created successfully",
        "user_id": user_id,
        "firebase_uid": user.firebase_uid
    }


# =========================
# REGISTERED USERS
# =========================

@router.post("/registered-users")
def register_user(user: RegisteredUserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check whether Firebase UID already exists
    cursor.execute(
        """
        SELECT firebase_uid
        FROM registered_users
        WHERE firebase_uid = %s
        """,
        (user.firebase_uid,)
    )

    existing_user = cursor.fetchone()

    if existing_user:
        cursor.close()
        conn.close()
        return {
            "registered": True,
            "message": "User already registered. Please login now."
        }

    # Insert new registered user
    query = """
        INSERT INTO registered_users
        (
            firebase_uid,
            email
        )
        VALUES
        (
            %s,
            %s
        )
    """

    values = (
        user.firebase_uid,
        user.email
    )

    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

    return {
        "registered": True,
        "message": "User registered successfully",
        "firebase_uid": user.firebase_uid,
        "email": user.email
    }


# =========================
# CHECK REGISTERED USER
# =========================

@router.get("/registered-users/{firebase_uid}")
def check_registered_user(firebase_uid: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT firebase_uid, email
        FROM registered_users
        WHERE firebase_uid = %s
        """,
        (firebase_uid,)
    )

    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        return {
            "registered": True,
            "firebase_uid": user["firebase_uid"],
            "email": user["email"]
        }

    return {
        "registered": False,
        "message": "User is not registered. Please sign in first."
    }


# =========================
# REGISTER ROUTERS
# =========================

app.include_router(router)
app.include_router(connections.router)
app.include_router(messages.router)
app.include_router(websocket.router)
app.include_router(sos.router)
app.include_router(doctor_search.router)
app.include_router(medicines.router)