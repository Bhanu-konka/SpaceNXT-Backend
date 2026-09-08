import os

from dotenv import load_dotenv
from apify_client import ApifyClient
from langchain_core.tools import tool

load_dotenv()

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

if not APIFY_API_TOKEN:
    raise ValueError("APIFY_API_TOKEN is not set in the .env file")

client = ApifyClient(APIFY_API_TOKEN)

MAX_DOCTORS = 5


def execute_apify_doctor_search(
    condition: str,
    specialty: str,
    location: str
) -> dict:
    """
    Executes Apify Google Maps crawler actor and returns both structured doctor list
    and plain text formatting for Agent 1.
    """
    if not location or str(location).lower() in {
        "none",
        "not specified",
        "unknown",
        "null",
    }:
        return {
            "error": "Location is required for doctor search. Please provide a city or location.",
            "text": "Location is required for doctor search. Please provide a city or location.",
            "doctors": []
        }

    search_term = f"{specialty} doctor" if specialty and specialty.lower() != "not specified" else "doctor"

    print("\n========================================")
    print("TOOL: APIFY GOOGLE MAPS SEARCH")
    print("========================================")
    print(f"Condition : {condition}")
    print(f"Specialty : {specialty}")
    print(f"Location  : {location}")
    print(f"Search    : {search_term}")
    print(f"Maximum   : {MAX_DOCTORS}")

    run_input = {
        "searchStringsArray": [search_term],
        "locationQuery": location,
        "maxCrawledPlacesPerSearch": MAX_DOCTORS,
        "language": "en",
    }

    try:
        run = client.actor(
            "compass/crawler-google-places"
        ).call(
            run_input=run_input
        )
    except Exception as error:
        err_msg = f"Apify Google Maps search failed. Error: {error}"
        return {"error": err_msg, "text": err_msg, "doctors": []}

    if not run:
        err_msg = "Apify did not return a completed run."
        return {"error": err_msg, "text": err_msg, "doctors": []}

    if hasattr(run, "default_dataset_id"):
        dataset_id = run.default_dataset_id
    elif isinstance(run, dict):
        dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
    else:
        dataset_id = getattr(run, "default_dataset_id", None)

    print(f"\nApify Dataset ID: {dataset_id}")

    try:
        items = list(
            client.dataset(dataset_id).iterate_items(
                limit=MAX_DOCTORS
            )
        )
    except Exception as error:
        err_msg = f"Failed to retrieve Apify dataset. Error: {error}"
        return {"error": err_msg, "text": err_msg, "doctors": []}

    if not items:
        msg = f"No doctor results found in {location}."
        return {"error": None, "text": msg, "doctors": []}

    doctors_list = []
    text_results = [
        f"Live Google Maps results for {specialty} doctors in {location}:",
        ""
    ]

    for index, item in enumerate(items[:MAX_DOCTORS], start=1):
        name = item.get("title", "Name unavailable")
        category = item.get("categoryName", "Not available")
        rating = item.get("totalScore", "Not available")
        reviews = item.get("reviewsCount", "Not available")
        
        street = item.get("street", "")
        city = item.get("city", "")
        state = item.get("state", "")
        country = item.get("countryCode", "")

        addr_parts = [p for p in [street, city, state, country] if p]
        address = ", ".join(addr_parts) if addr_parts else "Address unavailable"

        phone = item.get("phone", "Not available")
        website = item.get("website", "Not available")
        google_maps_url = item.get("url", "Not available")
        place_id = item.get("placeId", "")

        doctors_list.append({
            "name": name,
            "category": category,
            "rating": rating,
            "review_count": reviews,
            "address": address,
            "phone": phone,
            "website": website,
            "google_maps_url": google_maps_url,
            "place_id": place_id,
        })

        text_results.append(
            f"{index}. {name}\n"
            f"   Category: {category}\n"
            f"   Rating: {rating}\n"
            f"   Reviews: {reviews}\n"
            f"   Address: {address}\n"
            f"   Phone: {phone}\n"
            f"   Website: {website}\n"
            f"   Google Maps: {google_maps_url}\n"
        )

    return {
        "error": None,
        "text": "\n".join(text_results),
        "doctors": doctors_list
    }


@tool
def search_doctors(
    condition: str,
    specialty: str,
    location: str
) -> str:
    """
    Search Google Maps through Apify for real doctors
    or medical practices.

    Returns a maximum of 5 results.
    """
    res = execute_apify_doctor_search(condition, specialty, location)
    return res["text"]


if __name__ == "__main__":
    result = search_doctors.invoke({
        "condition": "knee pain",
        "specialty": "orthopedic",
        "location": "Seattle",
    })

    print("\n========================================")
    print("LIVE APIFY RESULT")
    print("========================================")
    print(result)