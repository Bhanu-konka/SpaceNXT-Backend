import uuid
from datetime import datetime
from database import get_db_connection
from websocket_manager import manager

def save_message(sender_uid: str, receiver_uid: str, content: str, message_id: str = None) -> dict:
    """Saves a message to MySQL database with initial status 'queued'."""
    if not message_id:
        message_id = str(uuid.uuid4())

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        INSERT INTO messages (message_id, sender_uid, receiver_uid, content, status)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (message_id, sender_uid, receiver_uid, content, "queued"))
    conn.commit()

    # Fetch created row
    cursor.execute("SELECT * FROM messages WHERE message_id = %s", (message_id,))
    msg = cursor.fetchone()

    cursor.close()
    conn.close()

    # Format created_at as ISO string if datetime
    if msg and isinstance(msg.get("created_at"), datetime):
        msg["created_at"] = msg["created_at"].isoformat()

    return msg

def update_message_status(message_id: str, status: str):
    """Updates status of a message in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE messages SET status = %s WHERE message_id = %s", (status, message_id))
    conn.commit()
    cursor.close()
    conn.close()

async def process_and_send_message(sender_uid: str, receiver_uid: str, content: str, message_id: str = None) -> dict:
    """
    Saves message as queued and attempts immediate delivery over WebSocket if receiver is online.
    Updates status to 'delivered' and notifies sender upon successful delivery.
    """
    msg = save_message(sender_uid, receiver_uid, content, message_id)
    msg_id = msg["message_id"]

    payload = {
        "type": "message",
        "message_id": msg_id,
        "sender_uid": sender_uid,
        "receiver_uid": receiver_uid,
        "content": content,
        "status": "queued",
        "created_at": msg.get("created_at", "")
    }

    if manager.is_online(receiver_uid):
        delivered = await manager.send_personal_message(payload, receiver_uid)
        if delivered:
            update_message_status(msg_id, "delivered")
            msg["status"] = "delivered"
            payload["status"] = "delivered"

            # Send delivery receipt back to sender if online
            status_receipt = {
                "type": "status_update",
                "message_id": msg_id,
                "status": "delivered",
                "receiver_uid": receiver_uid
            }
            await manager.send_personal_message(status_receipt, sender_uid)

    return msg

async def flush_offline_messages(receiver_uid: str):
    """
    Called upon user connection/reconnection to deliver all pending queued messages.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT * FROM messages
        WHERE receiver_uid = %s AND status = 'queued'
        ORDER BY id ASC
        """,
        (receiver_uid,)
    )
    queued_messages = cursor.fetchall()
    cursor.close()
    conn.close()

    if not queued_messages:
        return

    print(f"[QueueManager] Flushing {len(queued_messages)} offline messages for UID={receiver_uid}")

    for msg in queued_messages:
        msg_id = msg["message_id"]
        created_at_str = msg["created_at"].isoformat() if isinstance(msg.get("created_at"), datetime) else str(msg.get("created_at", ""))

        payload = {
            "type": "message",
            "message_id": msg_id,
            "sender_uid": msg["sender_uid"],
            "receiver_uid": msg["receiver_uid"],
            "content": msg["content"],
            "status": "delivered",
            "created_at": created_at_str
        }

        delivered = await manager.send_personal_message(payload, receiver_uid)
        if delivered:
            update_message_status(msg_id, "delivered")

            # Notify original sender of delivery
            status_receipt = {
                "type": "status_update",
                "message_id": msg_id,
                "status": "delivered",
                "receiver_uid": receiver_uid
            }
            await manager.send_personal_message(status_receipt, msg["sender_uid"])
