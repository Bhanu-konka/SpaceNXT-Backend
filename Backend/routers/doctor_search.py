import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any

# Ensure agnets directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agnets")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "agnets")))

from intent_classifier import classify_intent
from doctor_search_agent import run_doctor_search_agent
from tools.doctor_search_tool import execute_apify_doctor_search

router = APIRouter(prefix="/api", tags=["Doctor Search AI Agent"])


class DoctorSearchRequest(BaseModel):
    message: str


class DoctorInfo(BaseModel):
    name: str
    category: Optional[str] = "Not available"
    rating: Optional[Any] = "Not available"
    review_count: Optional[Any] = "Not available"
    address: Optional[str] = "Not available"
    phone: Optional[str] = "Not available"
    website: Optional[str] = "Not available"
    google_maps_url: Optional[str] = "Not available"
    place_id: Optional[str] = ""


class IntentData(BaseModel):
    intent: str
    condition: Optional[str] = None
    specialty: Optional[str] = None
    location: Optional[str] = None
    needs_reviews: bool = False


class DoctorSearchResponse(BaseModel):
    success: bool
    message: str
    intent: IntentData
    doctors: List[DoctorInfo] = []
    agent_summary: Optional[str] = None


@router.post("/doctor-search", response_model=DoctorSearchResponse)
@router.post("/ai/doctor-search", response_model=DoctorSearchResponse)
def search_doctors_endpoint(request: DoctorSearchRequest):
    user_msg = request.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message prompt cannot be empty.")

    try:
        classification = classify_intent(user_msg)
        intent_dict = classification.model_dump()
        intent_type = intent_dict.get("intent")
        location = intent_dict.get("location")

        intent_obj = IntentData(
            intent=intent_type,
            condition=intent_dict.get("condition"),
            specialty=intent_dict.get("specialty"),
            location=location,
            needs_reviews=intent_dict.get("needs_reviews", False)
        )

        if intent_type == "emergency":
            return DoctorSearchResponse(
                success=False,
                message="EMERGENCY DETECTED: If you are experiencing a life-threatening medical emergency, please call your local emergency services (like 911) or go to the nearest emergency room immediately.",
                intent=intent_obj,
                doctors=[]
            )

        if intent_type == "other":
            return DoctorSearchResponse(
                success=False,
                message="Your request does not appear to be a doctor search or emergency. Please ask to search for a doctor or medical specialist in a specific city.",
                intent=intent_obj,
                doctors=[]
            )

        if not location or str(location).lower() in {"none", "not specified", "unknown", "null"}:
            return DoctorSearchResponse(
                success=False,
                message="Location is required for doctor search. Please include a city or location in your request.",
                intent=intent_obj,
                doctors=[]
            )

        # Run Doctor Search Agent and fetch Apify structured results
        apify_res = execute_apify_doctor_search(
            condition=intent_dict.get("condition") or "",
            specialty=intent_dict.get("specialty") or "",
            location=location
        )

        if apify_res.get("error"):
            return DoctorSearchResponse(
                success=False,
                message=apify_res["error"],
                intent=intent_obj,
                doctors=[]
            )

        # Agent 1 summary
        agent_summary = run_doctor_search_agent(intent_dict)

        doctors = [DoctorInfo(**doc) for doc in apify_res.get("doctors", [])]

        return DoctorSearchResponse(
            success=True,
            message=f"Found {len(doctors)} doctors in {location}.",
            intent=intent_obj,
            doctors=doctors,
            agent_summary=agent_summary
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Doctor Search Pipeline error: {str(e)}")
