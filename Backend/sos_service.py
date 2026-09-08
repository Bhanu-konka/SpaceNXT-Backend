import uuid
from datetime import datetime
from database import get_db_connection
from websocket_manager import manager

def get_connected_uids(sender_uid: str) -> list[str]:
    """Returns a list of all UIDs connected to the given sender_uid in user_connections."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT target_uid AS connected_uid FROM user_connections WHERE user_uid = %s
        UNION
        SELECT user_uid AS connected_uid FROM user_connections WHERE target_uid = %s
        """,
        (sender_uid, sender_uid)
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [row["connected_uid"] for row in rows if row["connected_uid"] != sender_uid]

async def trigger_sos_event(sender_uid: str, latitude: float = None, longitude: float = None, message: str = "Emergency assistance required") -> dict:
    """
    Creates an SOS emergency record in MySQL and broadcasts real-time alert to all connected contacts.
    """
    event_id = str(uuid.uuid4())
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        INSERT INTO sos_events (event_id, sender_uid, latitude, longitude, message, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (event_id, sender_uid, latitude, longitude, message, "TRIGGERED"))
    conn.commit()

    cursor.execute("SELECT * FROM sos_events WHERE event_id = %s", (event_id,))
    event = cursor.fetchone()

    # Fetch sender's name from users table using firebase_uid
    sender_name = "Unknown User"
    try:
        cursor.execute("SELECT name FROM users WHERE firebase_uid = %s", (sender_uid,))
        user_row = cursor.fetchone()
        if user_row and user_row.get("name"):
            sender_name = user_row["name"]
    except Exception as e:
        print(f"[SOS] Error fetching user name for {sender_uid}: {e}")

    cursor.close()
    conn.close()

    created_at_str = event["created_at"].isoformat() if isinstance(event.get("created_at"), datetime) else str(event.get("created_at", ""))

    # Broadcast emergency alert to all connected contacts
    connected_uids = get_connected_uids(sender_uid)

    alert_payload = {
        "type": "sos_alert",
        "event_id": event_id,
        "sender_uid": sender_uid,
        "sender_name": sender_name,
        "latitude": latitude,
        "longitude": longitude,
        "message": message,
        "status": "TRIGGERED",
        "created_at": created_at_str
    }

    if connected_uids:
        print(f"[SOS] Broadcasting SOS alert from UID={sender_uid} ({sender_name}) to {len(connected_uids)} connected contacts: {connected_uids}")
        await manager.broadcast_to_uids(alert_payload, connected_uids)

    return {
        "status": "success",
        "message": "SOS emergency event triggered and broadcasted",
        "event": {
            "event_id": event_id,
            "sender_uid": sender_uid,
            "sender_name": sender_name,
            "latitude": latitude,
            "longitude": longitude,
            "message": message,
            "notified_contacts_count": len(connected_uids),
            "created_at": created_at_str
        }
    }
