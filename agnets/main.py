import os
import sys

# Ensure UTF-8 output encoding for Windows terminal compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

from intent_classifier import classify_intent
from doctor_search_agent import run_doctor_search_agent

load_dotenv()


def process_user_request(user_message: str):
    """
    End-to-end pipeline:
    1. Intent Classifier -> Structured Intent Pydantic model
    2. Check intent type (doctor_search, emergency, other)
    3. If doctor_search -> Agent 1 (Doctor Search Agent) -> search_doctors tool -> Apify
    """
    print("\n========================================")
    print("STEP 1: INTENT CLASSIFICATION")
    print("========================================")
    print(f"User Request: {user_message}\n")

    classification = classify_intent(user_message)
    intent_data = classification.model_dump()

    print(f"intent        : {intent_data.get('intent')}")
    print(f"condition     : {intent_data.get('condition')}")
    print(f"specialty     : {intent_data.get('specialty')}")
    print(f"location      : {intent_data.get('location')}")
    print(f"needs_reviews : {intent_data.get('needs_reviews')}")

    intent = intent_data.get("intent")

    if intent == "emergency":
        print("\n========================================")
        print("EMERGENCY ALERT")
        print("========================================")
        return (
            "EMERGENCY DETECTED: If you are experiencing a life-threatening medical emergency, "
            "please call your local emergency services (like 911) or go to the nearest emergency room immediately."
        )

    elif intent == "other":
        print("\n========================================")
        print("OTHER INTENT")
        print("========================================")
        return (
            "Your request does not appear to be a doctor search or emergency. "
            "Please ask to search for a doctor or medical specialist in a specific city."
        )

    elif intent == "doctor_search":
        print("\n========================================")
        print("STEP 2: DOCTOR SEARCH AGENT (AGENT 1)")
        print("========================================")
        
        location = intent_data.get("location")
        if not location or str(location).lower() in {"none", "not specified", "unknown", "null"}:
            return "Location is required for doctor search. Please provide a city or location."

        agent_result = run_doctor_search_agent(intent_data)
        return agent_result

    else:
        return f"Unknown intent: {intent}"


if __name__ == "__main__":
    test_message = "I have knee pain and need an orthopedic doctor in Seattle"
    result = process_user_request(test_message)

    print("\n========================================")
    print("FINAL SYSTEM OUTPUT")
    print("========================================")
    print(result)