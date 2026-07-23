import requests
import csv
import json
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
# ONE-TIME DEBUG STEP (run once, then delete/disable)
# =========================
# This gateway API is internal/undocumented, so before trusting any
# field name for linked Jira issues, dump one raw alert to see its
# actual shape. Uncomment, run, inspect the printed JSON, then decide
# whether linked issues live inside the alert object itself (e.g.
# under a key like "relatedTickets", "linkedIssues", "integrations")
# or need a separate per-alert call.
#
debug_resp = requests.get(
    f"{BASE_URL}{ALERTS_ENDPOINT}",
    headers=headers,
    params={"limit": 1},
    auth=auth
)
print(json.dumps(debug_resp.json(), indent=2))
exit()

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
# FETCH LINKED JIRA ISSUES  (NEW)
# =========================
# NOTE: endpoint path below is a best guess based on the pattern of
# the /notes endpoint. If it 404s, run the debug step above first —
# the linked issue data may already be embedded in the alert object
# returned by the main /alerts call, under a different key.

def fetch_linked_issues(alert_id):

    url = (
        f"{BASE_URL}"
        f"{ALERTS_ENDPOINT}/{alert_id}/linked-issues"
    )

    try:

        response = requests.get(
            url,
            headers=headers,
            auth=auth
        )

        if response.status_code != 200:
            return []

        data = response.json()

        # Adjust this depending on actual response shape once verified
        return data.get("values", []) or data.get("linkedIssues", [])

    except Exception as e:
        print(
            f"Error fetching linked issues "
            f"for alert {alert_id}: {e}"
        )
        return []


def extract_linked_issue_urls(linked_issues):

    keys = []
    urls = []

    for item in linked_issues:

        # Handle a couple of plausible shapes defensively
        issue = item.get("issue", item)

        key = issue.get("key", "")
        url = issue.get("url", "")

        if not url and key:
            url = f"{BASE_URL}/browse/{key}"

        if key:
            keys.append(key)
        if url:
            urls.append(url)

    return ", ".join(keys), ", ".join(urls)


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
        "Impact": "",
        "Action Taken": "",
        "Impact Description": ""
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
            "Impact": r"impact\s*[:\-]\s*(.*)",
            "Action Taken": r"action\s*taken\s*[:\-]\s*(.*)",
            "Impact Description": r"impact\s*description\s*[:\-]\s*(.*)"
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

    # Fetch notes AND linked issues concurrently per alert (NEW: linked issues added)
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

        linked_results = list(
            executor.map(
                lambda alert: (
                    alert["id"],
                    fetch_linked_issues(alert["id"])
                ),
                alerts
            )
        )

    # index linked issues by alert id for quick lookup
    linked_by_id = {aid: issues for aid, issues in linked_results}

    for alert, notes in notes_results:

        impact_data = extract_impact_details(notes)

        linked_issues = linked_by_id.get(alert["id"], [])
        linked_keys, linked_urls = extract_linked_issue_urls(linked_issues)

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
                impact_data["Impact"],

            "Action Taken":
                impact_data["Action Taken"],

            "Impact Description":
                impact_data["Impact Description"],

            "CAB":
                "Yes"
                if "cab" in impact_data["Action Taken"].lower()
                else "No",

            # NEW COLUMNS
            "Linked Jira Key":
                linked_keys,

            "Linked Jira URL":
                linked_urls
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
            "Impact",
            "Action Taken",
            "Impact Description",
            "CAB",
            "Linked Jira Key",   # NEW
            "Linked Jira URL"    # NEW
        ]
    )

    writer.writeheader()
    writer.writerows(rows)

print(
    f"\nSuccessfully exported "
    f"{len(rows)} alerts to {csv_file}"
)