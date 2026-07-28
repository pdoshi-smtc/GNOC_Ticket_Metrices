# Fetch_alerts.py
import requests
import csv
import re
import os
from datetime import datetime, UTC
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from fetch_jira_tickets import fetch_gnoc_ticket_details

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
#
# Alert notes list each field on its own single line, e.g.:
#
#   Start Time - 00:49 UTC
#   End Time - 01:09 UTC
#   Duration - 20 Minutes
#   Error Type - System failure
#   MVNO/s - BICS, JT, Sparkle  or BICS & JT
#   VPLMNs - Bouygues Telecom, Orange France, Telia Sverige AB, Free mobile
#   Country -  France
#   Customers - Matooma, Synox, Networth telecom
#   Device type - ESSENTIALS2, ADVANCED4, ADVANCED2,ADVANCED3
#   Impact - Minor
#   Action Taken - Alert closed manually
#
# Each field is extracted strictly from its OWN line — nothing is
# carried over from one line to the next, and only the fields listed
# below are ever captured. Any other line (headers we don't care about,
# free-form commentary, ticket references, etc.) is simply ignored, so
# it can never bleed into a real field's value.

# label -> regex matching just the label text (case-insensitive).
# The label may be followed by ":" or "-" as a separator.
NOTE_FIELD_PATTERNS = {
    "Start Time": r"(?:\d(?:st|nd|rd|th)\s*incident\s*)?start\s*time",
    "End Time": r"(?:\d(?:st|nd|rd|th)\s*incident\s*)?end\s*time",
    "Duration": r"duration",
    "Error Type": r"error\s*type",
    "MVNO": r"mvno(?:/s|s)?|roaming\s*partners?",
    "VPLMN": r"vplmns?",
    "Country": r"countr(?:y|ies)",
    "Customers": r"customers?(?:\s+impacted|\s+affected)?",
    "Device type": r"device\s*type",
    "Impact Description": r"(?:customer\s*impact|impact\s*description)",
    "Impact": r"impact(?!\s*description)",
    "Action Taken": r"action\s*taken",
}

# Compiled once: for each field, a regex that must match the ENTIRE
# line (optional list numbering + label + separator + value), so
# extraction never looks past the current line.
_NOTE_LINE_PATTERNS = {
    field: re.compile(
        rf"^\s*(?:[\*•]|\d{{1,3}}[.)])?\s*(?:{label_pattern})\s*[:\-]\s*(.+?)\s*$",
        flags=re.IGNORECASE
    )
    for field, label_pattern in NOTE_FIELD_PATTERNS.items()
}


def _clean_field_value(value):
    """Trim stray whitespace/punctuation from a single-line value."""

    value = (value or "").strip()
    value = re.sub(r"[ \t]{2,}", " ", value)
    return value.strip(" ,")


# Matches the VPLMN name directly out of the alert's own Message field, e.g.:
#   "kibana: VPLMN DOWN -Hutchison Drei Austria GmbH [MVNO-EU - Lost-Service] - ..."
#   -> "Hutchison Drei Austria GmbH"
# This only applies to "VPLMN DOWN" alerts, where the network being
# monitored IS the VPLMN. "ROAMING PARTNER DOWN" alerts name the roaming
# partner instead (a different field), so they simply won't match here and
# fall back to the note/ticket-derived value further down.
_VPLMN_MESSAGE_RE = re.compile(r"VPLMN\s*DOWN\s*-\s*(.+?)\s*\[", flags=re.IGNORECASE)


def extract_vplmn_from_message(message):
    """Extract the VPLMN name from the alert Message, or "" if not present."""

    if not message:
        return ""

    match = _VPLMN_MESSAGE_RE.search(message)

    return _clean_field_value(match.group(1)) if match else ""


# Matches "System Failure" or "Lost Service" directly out of the alert's own
# Message field, e.g.:
#   "... [MVNO-EU - Lost-Service] ..."          -> "Lost Service"
#   "... [ Diameter/Sigtran - System failure ..." -> "System Failure"
# Normalizes hyphen/space and casing differences to one of these two
# canonical values.
_ERROR_TYPE_MESSAGE_RE = re.compile(
    r"(system\s*failure|lost[\s\-]*service)", flags=re.IGNORECASE
)


def extract_error_type_from_message(message):
    """Extract "System Failure" or "Lost Service" from the Message, or "" if neither is present."""

    if not message:
        return ""

    match = _ERROR_TYPE_MESSAGE_RE.search(message)

    if not match:
        return ""

    return "System Failure" if "system" in match.group(1).lower() else "Lost Service"


def _match_line_field(line):
    """
    Try to match a single line against a known field label.
    Returns (field, value) for the first matching field, or None.
    """

    for field, pattern in _NOTE_LINE_PATTERNS.items():
        match = pattern.match(line)
        if match:
            return field, match.group(1)

    return None


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
        "Impact Description": "",
        "Affected Services": "",
        "CAB": "No",
        "GNOC": ""
    }

    for note in notes:
        # Normalize non-breaking spaces (U+00A0), which can be pasted in
        # from web sources and look like a normal space but aren't matched
        # by \s, so they can silently break "Label - value" line matching.
        note_text = (note.get("note", "") or "").replace("\xa0", " ")
        lower_text = note_text.lower()

        for line in note_text.splitlines():
            matched = _match_line_field(line)

            if matched:
                field, raw_value = matched
                value = _clean_field_value(raw_value)

                if value:
                    if result[field]:
                        result[field] = f"{result[field]} | {value}"
                    else:
                        result[field] = value

        if "cab" in lower_text:
            result["CAB"] = "Yes"

        if "gnoc" in lower_text:

            gnoc_match = re.search(
                r"(GNOC-\d{4,5})",
                note_text,
                flags=re.IGNORECASE
            )

            if gnoc_match:
                result["GNOC"] = gnoc_match.group(1).upper()

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

        message = alert.get("message", "")
        message_vplmn = extract_vplmn_from_message(message)
        vplmn_value = message_vplmn or impact_data["VPLMN"]

        message_error_type = extract_error_type_from_message(message)
        error_type_value = message_error_type or impact_data["Error Type"]

        rows.append({
            "TinyId":
                alert.get("tinyId", ""),
            "Message":
                message,
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
                error_type_value,

            "MVNO":
                impact_data["MVNO"],

            "VPLMN":
                vplmn_value,
            
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

            "Affected Services":
                impact_data["Affected Services"],

            "CAB":
                impact_data["CAB"],

            "GNOC":
                impact_data["GNOC"]
        })

    if len(alerts) < limit:
        break

    offset += limit


# =========================
# ENRICH GNOC TICKETS
# =========================
# For alerts where a GNOC ticket id was captured and CAB is "No",
# fetch each unique GNOC ticket's description once and apply it to
# every alert that references that same GNOC id. Only overwrite a
# field when the ticket actually has a value for it, so an empty
# ticket field never wipes out a value already captured from the
# alert note itself.

gnoc_details_cache = {}

for row in rows:

    if row["GNOC"] and row["CAB"].strip().lower() == "no":

        gnoc_id = row["GNOC"]

        if gnoc_id not in gnoc_details_cache:
            print(f"Fetching GNOC ticket {gnoc_id}...")
            gnoc_details_cache[gnoc_id] = fetch_gnoc_ticket_details(gnoc_id)

        details = gnoc_details_cache[gnoc_id]

        if details:
            if details.get("Customers"):
                row["Customers"] = details["Customers"]

            if details.get("Error Type") and not row["Error Type"]:
                row["Error Type"] = details["Error Type"]

            if details.get("Device type"):
                row["Device type"] = details["Device type"]

            if details.get("Country"):
                row["Country"] = details["Country"]

            if details.get("VPLMN") and not row["VPLMN"]:
                row["VPLMN"] = details["VPLMN"]

            if details.get("Impact Description"):
                row["Impact Description"] = details["Impact Description"]

            if details.get("Affected Services"):
                row["Affected Services"] = details["Affected Services"]

            if details.get("MVNO"):
                row["MVNO"] = details["MVNO"]

            if details.get("Start Time"):
                row["Start Time"] = details["Start Time"]

            if details.get("End Time"):
                row["End Time"] = details["End Time"]

            if details.get("Duration"):
                row["Duration"] = details["Duration"]

            row["Impact"] = "Major"


# =========================
# SAVE CSV
# =========================

os.makedirs("data", exist_ok=True)
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
            "Affected Services",
            "CAB",
            "GNOC"
        ]
    )

    writer.writeheader()
    writer.writerows(rows)

print(
    f"\nSuccessfully exported "
    f"{len(rows)} alerts to {csv_file}"
)