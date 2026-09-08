from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from authentication.auth import verify_firebase_token, get_current_user_uid
from sos_service import trigger_sos_event
from database import get_db_connection
from datetime import datetime

router = APIRouter(tags=["sos"])

class SOSRequest(BaseModel):
    sender_uid: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    message: Optional[str] = "Emergency assistance required"

@router.post("/sos")
async def trigger_sos(
    body: SOSRequest,
    authorization: Optional[str] = Header(None)
):
    # Determine sender_uid from verified token if present, else body.sender_uid
    sender_uid = None
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        try:
            sender_uid = verify_firebase_token(token)
        except Exception:
            pass

    if not sender_uid:
        sender_uid = body.sender_uid

    if not sender_uid:
        raise HTTPException(status_code=401, detail="Authentication token or sender_uid required.")

    result = await trigger_sos_event(
        sender_uid=sender_uid,
        latitude=body.latitude,
        longitude=body.longitude,
        message=body.message or "Emergency assistance required"
    )

    return result

@router.get("/sos/history/{firebase_uid}")
def get_sos_history(firebase_uid: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM sos_events WHERE sender_uid = %s ORDER BY id DESC LIMIT 50",
            (firebase_uid,)
        )
        events = cursor.fetchall()
        for e in events:
            if isinstance(e.get("created_at"), datetime):
                e["created_at"] = e["created_at"].isoformat()
        return events
    finally:
        cursor.close()
        conn.close()
