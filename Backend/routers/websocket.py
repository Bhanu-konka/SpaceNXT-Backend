import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from authentication.auth import verify_firebase_token
from websocket_manager import manager
from queue_manager import process_and_send_message, flush_offline_messages

router = APIRouter(tags=["websocket"])

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None),
    uid: str = Query(None)
):
    auth_token = token or uid
    if not auth_token:
        print("[WebSocket Reject] No token or UID query parameter provided.")
        await websocket.close(code=4001, reason="Authentication token missing.")
        return

    try:
        firebase_uid = verify_firebase_token(auth_token)
    except Exception as e:
        print(f"[WebSocket Warning] Token verification fallback: {e}")
        firebase_uid = auth_token

    # Accept connection and register in manager
    await manager.connect(websocket, firebase_uid)
    print(f"[WebSocket Connected] Live socket established for UID: {firebase_uid}")

    # Immediately flush any offline queued messages for this user
    try:
        await flush_offline_messages(firebase_uid)
    except Exception as e:
        print(f"[WebSocket] Error flushing offline messages for {firebase_uid}: {e}")

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
            except Exception:
                continue

            msg_type = data.get("type", "message")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            elif msg_type == "message":
                receiver_uid = data.get("receiver_uid")
                content = data.get("content")

                if receiver_uid and content:
                    print(f"[WebSocket Message Received] From {firebase_uid} -> To {receiver_uid}: '{content}'")
                    await process_and_send_message(
                        sender_uid=firebase_uid,
                        receiver_uid=receiver_uid,
                        content=content
                    )

    except WebSocketDisconnect:
        print(f"[WebSocket Disconnected] UID={firebase_uid}")
        await manager.disconnect(websocket, firebase_uid)
    except Exception as e:
        print(f"[WebSocket Exception] UID={firebase_uid}: {e}")
        await manager.disconnect(websocket, firebase_uid)
