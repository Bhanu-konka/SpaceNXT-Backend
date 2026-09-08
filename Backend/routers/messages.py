from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from database import get_db_connection
from queue_manager import process_and_send_message
from authentication.auth import get_current_user_uid

router = APIRouter(tags=["messages"])

class SendMessageRequest(BaseModel):
    sender_uid: Optional[str] = None
    receiver_uid: str
    content: str

@router.get("/messages/history")
def get_chat_history(
    user1_uid: str = Query(...),
    user2_uid: str = Query(...),
    limit: int = Query(100, ge=1, le=500)
):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        query = """
            SELECT * FROM messages
            WHERE (sender_uid = %s AND receiver_uid = %s)
               OR (sender_uid = %s AND receiver_uid = %s)
            ORDER BY id ASC
            LIMIT %s
        """
        cursor.execute(query, (user1_uid, user2_uid, user2_uid, user1_uid, limit))
        rows = cursor.fetchall()

        for r in rows:
            if isinstance(r.get("created_at"), datetime):
                r["created_at"] = r["created_at"].isoformat()

        return rows
    finally:
        cursor.close()
        conn.close()

@router.post("/messages/send")
async def send_message_rest(
    body: SendMessageRequest,
    current_uid: str = Depends(get_current_user_uid)
):
    # Sender UID must match verified token
    sender_uid = current_uid or body.sender_uid
    if not sender_uid:
        raise HTTPException(status_code=400, detail="Sender UID missing.")

    if sender_uid == body.receiver_uid:
        raise HTTPException(status_code=400, detail="Cannot send message to yourself.")

    msg = await process_and_send_message(sender_uid, body.receiver_uid, body.content)
    return {
        "status": "success",
        "message": msg
    }
