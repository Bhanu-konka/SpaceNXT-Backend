import os
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel, Field
from typing import Literal
from langchain_groq import ChatGroq

# ============================================================
# 1. Load environment variables
# ============================================================

env_path = find_dotenv(usecwd=True)
if not env_path:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for candidate in [
        os.path.join(current_dir, ".env"),
        os.path.join(current_dir, "..", ".env"),
        os.path.join(current_dir, "agnets", ".env"),
        os.path.join(current_dir, "..", "agnets", ".env"),
    ]:
        if os.path.exists(candidate):
            env_path = candidate
            break

if env_path:
    load_dotenv(env_path)
else:
    load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError(
        "GROQ_API_KEY is not set in the .env file"
    )


# ============================================================
# 2. Define the structured output
# ============================================================

class IntentClassification(BaseModel):

    # --------------------------------------------------------
    # Fixed set of allowed intents
    # --------------------------------------------------------

    intent: Literal[
        "doctor_search",
        "emergency",
        "other"
    ] = Field(
        description=(
            "The main intent of the user's request. "
            "Use doctor_search when the user wants to find "
            "or search for a doctor. "
            "Use emergency when the user describes potentially "
            "life-threatening symptoms requiring urgent care. "
            "Use other for requests that do not belong to these."
        )
    )

    # --------------------------------------------------------
    # Health condition/problem
    # --------------------------------------------------------

    condition: str | None = Field(
        default=None,
        description=(
            "The health problem or symptom explicitly "
            "mentioned by the user."
        )
    )

    # --------------------------------------------------------
    # Medical specialty
    # --------------------------------------------------------

    specialty: str | None = Field(
        default=None,
        description=(
            "The relevant medical specialty if it can "
            "reasonably be inferred."
        )
    )

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    location: str | None = Field(
        default=None,
        description=(
            "The location where the user wants to find "
            "a doctor. Return null if not provided."
        )
    )

    # --------------------------------------------------------
    # Reviews
    # --------------------------------------------------------

    needs_reviews: bool = Field(
        default=False,
        description=(
            "True if the user explicitly asks for doctor "
            "reviews, ratings, comparison, or review-based "
            "evaluation."
        )
    )


# ============================================================
# 3. Create Groq LLM
# ============================================================

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    api_key=groq_api_key,
)


# ============================================================
# 4. Enable structured output
# ============================================================

structured_llm = llm.with_structured_output(
    IntentClassification
)


# ============================================================
# 5. Intent Classification Function
# ============================================================

def classify_intent(
    user_message: str
) -> IntentClassification:

    prompt = f"""
You are the Intent Classifier for a medical doctor-search
application.

Your job is ONLY to understand the user's request and convert
it into structured information for the next agent.

Do NOT diagnose the user.
Do NOT provide treatment.
Do NOT provide medical advice.

------------------------------------------------------------
ALLOWED INTENTS
------------------------------------------------------------

You MUST use exactly one of these:

1. doctor_search

Use doctor_search when the user wants to:
- find a doctor
- search for a doctor
- locate a doctor
- find a specialist
- get doctor recommendations

Examples:
"I need an orthopedic doctor"
"I have knee pain and need a doctor"
"Find a cardiologist in Seattle"

2. emergency

Use emergency when the user describes symptoms that could
represent a medical emergency and require urgent attention.

Examples:
"I am having severe chest pain right now"
"I have very severe heart pain"
"I am having difficulty breathing"
"I suddenly cannot speak properly"

Do not diagnose the condition. Just classify the request
as potentially requiring emergency attention.

3. other

Use other when the request is unrelated to finding a doctor
or handling a potentially urgent medical situation.

------------------------------------------------------------
CONDITION
------------------------------------------------------------

Extract the health problem or symptom explicitly as described
by the user.

Do not invent a diagnosis.

------------------------------------------------------------
SPECIALTY
------------------------------------------------------------

Infer an appropriate medical specialty when reasonable.

Examples:

knee pain
→ orthopedics

heart-related symptoms
→ cardiology

skin problem
→ dermatology

Do not invent a specialty when there is not enough information.

------------------------------------------------------------
LOCATION
------------------------------------------------------------

Extract the location if the user provides one.

If no location is provided:

location = null

Do NOT invent a location.

------------------------------------------------------------
REVIEWS
------------------------------------------------------------

Set needs_reviews to true only when the user asks for:
- reviews
- ratings
- doctor comparison
- review-based ranking
- reputation

Otherwise:

needs_reviews = false

------------------------------------------------------------
IMPORTANT
------------------------------------------------------------

The intent value MUST be exactly:

doctor_search

OR

emergency

OR

other

Never return "search".

Never return "doctor".

Never return "find_doctor".

------------------------------------------------------------
USER REQUEST
------------------------------------------------------------

{user_message}
"""

    result = structured_llm.invoke(prompt)

    return result


# ============================================================
# 6. Test the classifier
# ============================================================

if __name__ == "__main__":

    user_message = input(
        "Enter your request: "
    )

    result = classify_intent(
        user_message
    )

    print("\n========================================")
    print("INTENT CLASSIFICATION")
    print("========================================")

    print(f"Intent: {result.intent}")
    print(f"Condition: {result.condition}")
    print(f"Specialty: {result.specialty}")
    print(f"Location: {result.location}")
    print(f"Needs Reviews: {result.needs_reviews}")