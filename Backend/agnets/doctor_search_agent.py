import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import create_agent

from tools.doctor_search_tool import search_doctors


# ============================================================
# 1. Load environment variables
# ============================================================

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError(
        "GROQ_API_KEY is not set in the .env file"
    )


# ============================================================
# 2. Create Groq LLM
# ============================================================

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    api_key=groq_api_key,
)


# ============================================================
# 3. Create Doctor Search Agent
# ============================================================

agent = create_agent(
    model=llm,
    tools=[search_doctors],

    system_prompt="""
You are Agent 1: Doctor Search Agent.

Your job is to search for doctors based on structured
information received from the Intent Classifier.

You will receive:

- condition
- specialty
- location

You MUST use the search_doctors tool when a doctor search
is required.

The search tool has a hard maximum of 5 doctors.

Do not diagnose the patient.

Do not provide medical treatment advice.

Your responsibility is only to find relevant doctor
candidates and clearly present the search results.

After receiving the tool result, summarize the results
clearly for the next stage of the system.
"""
)


# ============================================================
# 4. Function used by main.py
# ============================================================

def run_doctor_search_agent(intent: dict) -> str:
    """
    Receive structured intent from the Intent Classifier
    and send it to Agent 1.
    """

    condition = intent.get("condition")
    specialty = intent.get("specialty")
    location = intent.get("location")

    # --------------------------------------------------------
    # Safety check
    # --------------------------------------------------------

    if not condition:
        condition = "not specified"

    if not specialty:
        specialty = "not specified"

    if not location:
        location = "not specified"

    # --------------------------------------------------------
    # Build Agent 1 request
    # --------------------------------------------------------

    request = f"""
Search for doctors using the following structured intent:

Condition:
{condition}

Specialty:
{specialty}

Location:
{location}

Return a maximum of 5 doctors.
"""

    # --------------------------------------------------------
    # Send request to Agent 1
    # --------------------------------------------------------

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": request
                }
            ]
        }
    )

    # --------------------------------------------------------
    # Get final Agent response
    # --------------------------------------------------------

    final_message = result["messages"][-1]

    return final_message.content


# ============================================================
# 5. Direct test
# ============================================================

if __name__ == "__main__":

    test_intent = {
        "intent": "doctor_search",
        "condition": "knee pain",
        "specialty": "orthopedics",
        "location": "Seattle",
        "needs_reviews": False,
    }

    print("\n========================================")
    print("STARTING DOCTOR SEARCH AGENT")
    print("========================================")

    result = run_doctor_search_agent(test_intent)

    print("\n========================================")
    print("AGENT 1 RESULT")
    print("========================================")

    print(result)