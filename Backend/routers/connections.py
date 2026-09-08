from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import get_db_connection
from authentication.auth import get_current_user_uid

router = APIRouter(tags=["connections"])

class ConnectionCreate(BaseModel):
    parent_uid: Optional[str] = None
    child_uid: Optional[str] = None
    user_uid: Optional[str] = None
    target_uid: Optional[str] = None

@router.post("/connect-users")
def connect_users(data: ConnectionCreate):
    # Support both parent_uid/child_uid and user_uid/target_uid
    u1 = data.user_uid or data.parent_uid
    u2 = data.target_uid or data.child_uid

    if not u1 or not u2:
        raise HTTPException(status_code=400, detail="Both user UIDs must be specified.")

    if u1 == u2:
        raise HTTPException(status_code=400, detail="Cannot connect a user to themselves.")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        query = """
            INSERT INTO user_connections (user_uid, target_uid)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE id=id
        """
        cursor.execute(query, (u1, u2))
        conn.commit()

        return {
            "status": "success",
            "message": "Users connected successfully",
            "user_uid": u1,
            "target_uid": u2
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to connect users: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@router.get("/connections/{firebase_uid}")
def get_user_connections(firebase_uid: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get all connected UIDs
        cursor.execute(
            """
            SELECT target_uid AS connected_uid FROM user_connections WHERE user_uid = %s
            UNION
            SELECT user_uid AS connected_uid FROM user_connections WHERE target_uid = %s
            """,
            (firebase_uid, firebase_uid)
        )
        connected_rows = cursor.fetchall()
        connected_uids = [r["connected_uid"] for r in connected_rows if r["connected_uid"] != firebase_uid]

        if not connected_uids:
            return []

        # Fetch details for connected users from users table if available
        format_strings = ','.join(['%s'] * len(connected_uids))
        cursor.execute(
            f"SELECT firebase_uid, name, email, role, phone FROM users WHERE firebase_uid IN ({format_strings})",
            tuple(connected_uids)
        )
        user_profiles = cursor.fetchall()
        profile_map = {u["firebase_uid"]: u for u in user_profiles}

        results = []
        for uid in connected_uids:
            if uid in profile_map:
                results.append(profile_map[uid])
            else:
                results.append({
                    "firebase_uid": uid,
                    "name": f"User ({uid[:6]}...)",
                    "email": "",
                    "role": "Contact",
                    "phone": ""
                })

        return results
    finally:
        cursor.close()
        conn.close()
