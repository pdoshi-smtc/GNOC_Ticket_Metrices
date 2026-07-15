import requests
import csv
import re
import os
from datetime import datetime, UTC
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# =========================
# LOAD ENV VARIABLES
# =========================

load_dotenv()

EMAIL = os.getenv("JIRA_USER_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")

BASE_URL = os.getenv(
    "JIRA_BASE_URL",
    "https://sierrawireless.atlassian.net"
)

ALERTS_ENDPOINT = (
    "/gateway/api/jsm/ops/web/"
    "3a7467b6-6c2f-4bfc-a2d9-21020a74bee4/v1/alerts"
)

auth = HTTPBasicAuth(EMAIL, API_TOKEN)

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# =========================
# USER INPUT
# =========================

start_date = input(
    "Enter Start Date (Saturday) (DD-MM-YYYY): "
).strip()

end_date = input(
    "Enter End Date (Saturday) (DD-MM-YYYY): "
).strip()

query = (
    f"createdAt >= {start_date} "
    f"AND createdAt < {end_date} "
    f'AND (message:("VPLMN DOWN" OR "ROAMING PARTNER DOWN"))'
)

# =========================
# FETCH NOTES
# =========================

def fetch_notes(alert_id):

    url = (
        f"{BASE_URL}"
        f"{ALERTS_ENDPOINT}/{alert_id}/notes"
    )

    try:

        response = requests.get(
            url,
            headers=headers,
            auth=auth
        )

        if response.status_code != 200:
            print(
                f"Failed to fetch notes "
                f"for alert {alert_id}"
            )
            return []

        data = response.json()

        return data.get("values", [])

    except Exception as e:
        print(
            f"Error fetching notes "
            f"for alert {alert_id}: {e}"
        )
        return []


# =========================
# PARSE IMPACT NOTE
# =========================

def extract_impact_details(notes):

    result = {
        "Start Time": "",
        "End Time": "",
        "Duration": "",
        "Error Type": "",
        "MVNO": "",
        "VPLMN": "",
        "Country": "",
        "Customers": "",
        "Device type": "",
        "Impact": ""
    }

    for note in notes:
        note_text = note.get("note", "")

        if "start time" not in note_text.lower():
            continue

        patterns = {
            "Start Time": r"start\s*time\s*[:\-]\s*(.*)",
            "End Time": r"end\s*time\s*[:\-]\s*(.*)",
            "Duration": r"duration\s*[:\-]\s*(.*)",
            "Error Type": r"error\s*type\s*[:\-–—]\s*(.*)",
            "MVNO": r"mvno(?:/s|s)?\s*[:\-]\s*(.*)",
            "VPLMN": r"vplmns?\s*[:\-]\s*(.*)",
            "Country": r"country\s*[:\-]\s*(.*)",
            "Customers": r"customers?\s*[:\-]\s*(.*)",
            "Device type": r"device\s*type\s*[:\-]\s*(.*)",
            "Impact": r"impact\s*[:\-]\s*(.*)"
        }

        for field, pattern in patterns.items():

            match = re.search(
                pattern,
                note_text,
                flags=re.IGNORECASE
            )

            if match:
                result[field] = match.group(1).strip()

        break

    return result


# =========================
# FETCH ALERTS
# =========================

rows = []

offset = 0
limit = 100

while True:

    params = {
        "query": query,
        "sort": "insertedAt",
        "limit": limit,
        "offset": offset,
        "applyVisibilityFilter": "false"
    }

    response = requests.get(
        f"{BASE_URL}{ALERTS_ENDPOINT}",
        headers=headers,
        params=params,
        auth=auth
    )

    response.raise_for_status()

    data = response.json()

    alerts = data.get("values", [])

    if not alerts:
        break

    print(
        f"Fetched {len(alerts)} alerts "
        f"(offset={offset})"
    )

    with ThreadPoolExecutor(max_workers=20) as executor:

        notes_results = list(
            executor.map(
                lambda alert: (
                    alert,
                    fetch_notes(alert["id"])
                ),
                alerts
            )
        )

    for alert, notes in notes_results:

        impact_data = extract_impact_details(notes)

        rows.append({
            "TinyId":
                alert.get("tinyId", ""),
            "Message":
                alert.get("message", ""),
            "CreatedAt":
                datetime.fromtimestamp(
                    alert.get(
                        "createdAt", 0
                    ) / 1000,
                    UTC
                ).strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                ),

            "Start Time":
                impact_data["Start Time"],

            "End Time":
                impact_data["End Time"],

            "Duration":
                impact_data["Duration"],

            "Error Type":
                impact_data["Error Type"],

            "MVNO":
                impact_data["MVNO"],

            "VPLMN":
                impact_data["VPLMN"],
            
            "Country":
                impact_data["Country"],

            "Customers":
                impact_data["Customers"],

            "Device type":
                impact_data["Device type"],

            "Impact":
                impact_data["Impact"]
        })

    if len(alerts) < limit:
        break

    offset += limit


# =========================
# SAVE CSV
# =========================

csv_file = "data/alerts.csv"

with open(
    csv_file,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "TinyId",
            "Message",
            "CreatedAt",
            "Start Time",
            "End Time",
            "Duration",
            "Error Type",
            "MVNO",
            "VPLMN",
            "Country",
            "Customers",
            "Device type",
            "Impact"
        ]
    )

    writer.writeheader()
    writer.writerows(rows)

print(
    f"\nSuccessfully exported "
    f"{len(rows)} alerts to {csv_file}"
)
