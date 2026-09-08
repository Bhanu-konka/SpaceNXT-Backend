from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, time
from database import get_db_connection

router = APIRouter(prefix="/medicines", tags=["medicines"])


class MedicineCreate(BaseModel):
    user_uid: str           # Target parent UID whose medicine schedule this is
    medicine_name: str
    dosage: Optional[str] = "1 tablet"
    reminder_time: str      # e.g. "08:00 AM", "1:00 PM", "8:00 PM"
    repeat_type: Optional[str] = "Daily"
    created_by: str         # Parent or Child UID


class MedicineTake(BaseModel):
    medicine_id: int
    marked_by: str
    taken_at: Optional[str] = None  # e.g. "8:02 AM"


def _parse_time_str(time_str: str) -> Optional[time]:
    """Helper to convert reminder time string to datetime.time for status comparison."""
    if not time_str:
        return None
    time_str = time_str.strip().upper()
    formats = ["%I:%M %p", "%I:%M%p", "%H:%M", "%H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            pass
    return None


@router.get("/today/{user_uid}")
def get_today_medicines(user_uid: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        today_date = date.today()
        now_time = datetime.now().time()

        # Ultra-fast single JOIN query
        cursor.execute(
            """
            SELECT 
                m.id, m.user_uid, m.medicine_name, m.dosage, m.reminder_time, m.repeat_type, m.created_by,
                l.taken, l.taken_at
            FROM medicines m
            LEFT JOIN medicine_logs l ON m.id = l.medicine_id AND l.log_date = %s
            WHERE m.user_uid = %s
            ORDER BY m.id ASC
            """,
            (today_date, user_uid)
        )
        meds = cursor.fetchall()

        result = []
        for m in meds:
            rem_time_str = m["reminder_time"]
            rem_time_obj = _parse_time_str(rem_time_str)

            if m.get("taken") == 1:
                status = "taken"
                taken_at = m.get("taken_at") or "Taken"
            elif rem_time_obj and now_time > rem_time_obj:
                status = "missed"
                taken_at = None
            else:
                status = "upcoming"
                taken_at = None

            result.append({
                "id": m["id"],
                "user_uid": m["user_uid"],
                "medicine_name": m["medicine_name"],
                "dosage": m["dosage"] or "",
                "reminder_time": m["reminder_time"],
                "repeat_type": m["repeat_type"] or "Daily",
                "status": status,
                "taken_at": taken_at,
                "created_by": m["created_by"]
            })

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch today's medicines: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@router.post("")
def add_medicine(data: MedicineCreate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        query = """
            INSERT INTO medicines (user_uid, medicine_name, dosage, reminder_time, repeat_type, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data.user_uid,
            data.medicine_name,
            data.dosage,
            data.reminder_time,
            data.repeat_type or "Daily",
            data.created_by
        ))
        conn.commit()
        new_id = cursor.lastrowid

        return {
            "status": "success",
            "message": "Medicine added successfully",
            "id": new_id,
            "user_uid": data.user_uid,
            "medicine_name": data.medicine_name,
            "dosage": data.dosage,
            "reminder_time": data.reminder_time,
            "repeat_type": data.repeat_type or "Daily",
            "created_by": data.created_by
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add medicine: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@router.post("/take")
def mark_medicine_taken(data: MedicineTake):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        today_date = date.today()
        taken_time_str = data.taken_at or datetime.now().strftime("%I:%M %p")

        query = """
            INSERT INTO medicine_logs (medicine_id, log_date, taken, taken_at, marked_by)
            VALUES (%s, %s, 1, %s, %s)
            ON DUPLICATE KEY UPDATE taken=1, taken_at=%s, marked_by=%s
        """
        cursor.execute(query, (
            data.medicine_id,
            today_date,
            taken_time_str,
            data.marked_by,
            taken_time_str,
            data.marked_by
        ))
        conn.commit()

        return {
            "status": "success",
            "message": "Medicine marked as taken",
            "medicine_id": data.medicine_id,
            "taken_at": taken_time_str,
            "marked_by": data.marked_by
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to mark medicine as taken: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@router.delete("/{medicine_id}")
def delete_medicine(medicine_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM medicine_logs WHERE medicine_id = %s", (medicine_id,))
        cursor.execute("DELETE FROM medicines WHERE id = %s", (medicine_id,))
        conn.commit()
        return {"status": "success", "message": "Medicine deleted successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete medicine: {str(e)}")
    finally:
        cursor.close()
        conn.close()
