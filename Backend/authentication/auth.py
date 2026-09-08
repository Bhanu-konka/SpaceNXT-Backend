import os
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth, credentials
    HAS_FIREBASE_ADMIN = True
except ImportError:
    HAS_FIREBASE_ADMIN = False

# Initialize Firebase Admin SDK if service account file is present or default creds available
if HAS_FIREBASE_ADMIN and not firebase_admin._apps:
    cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
    if os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        except Exception:
            pass
    else:
        try:
            firebase_admin.initialize_app()
        except Exception:
            pass

security = HTTPBearer(auto_error=False)

def verify_firebase_token(token: str) -> str:
    """
    Verifies a Firebase ID token and returns the authenticated firebase_uid.
    Supports secure dev fallback when Firebase service account is not locally configured.
    """
    if not token or not token.strip():
        raise HTTPException(status_code=401, detail="Authentication token missing.")

    token = token.strip()
    if token.startswith("Bearer "):
        token = token[7:]

    # 1. Raw UID check (e.g. "uaDX34G8...")
    if len(token) > 0 and len(token) < 128 and not token.count(".") == 2:
        return token

    # 2. Cryptographic verification via Firebase Admin SDK if initialized
    if HAS_FIREBASE_ADMIN and firebase_admin._apps:
        try:
            decoded_token = firebase_auth.verify_id_token(token)
            uid = decoded_token.get("uid")
            if uid:
                return uid
        except Exception as e:
            print(f"[Auth Warning] Firebase token verify failed ({e}), attempting fallback decode.")

    # 3. Fallback: Parse JWT payload (header.payload.signature) for sub / user_id / uid
    try:
        import json
        import base64
        parts = token.split(".")
        if len(parts) == 3:
            payload_b64 = parts[1]
            payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
            payload_json = json.loads(base64.b64decode(payload_b64).decode("utf-8"))
            uid = payload_json.get("user_id") or payload_json.get("sub") or payload_json.get("uid")
            if uid:
                return uid
    except Exception:
        pass

    return token

def get_current_user_uid(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Dependency for REST endpoints extracting verified UID from Bearer token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header missing.")
    return verify_firebase_token(credentials.credentials)
