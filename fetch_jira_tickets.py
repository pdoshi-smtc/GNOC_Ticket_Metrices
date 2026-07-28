# fetch_jira_tickets
from collections import defaultdict
from dateutil import parser
from datetime import datetime, timezone
from dotenv import load_dotenv
import pandas as pd
import requests
import os
import re
import html
import sys

load_dotenv()

# ==========================
# CONFIG
# ==========================
JIRA_URL = os.getenv("JIRA_BASE_URL", "https://sierrawireless.atlassian.net")
USERNAME = os.getenv("JIRA_USER_EMAIL")
PASSWORD = os.getenv("JIRA_API_TOKEN")

VALID_STATUSES = {
    "OPEN",
    "WORK IN PROGRESS",
    "IN REVIEW",
    "COMPLETED",
    "CANCELLED",
    "CANCELED",
    "CLOSED"
}

FINAL_STATUSES = {
    "COMPLETED",
    "CLOSED",
    "CANCELLED",
    "CANCELED"
}

# ==========================
# SLA CONFIG (MINUTES)
# ==========================
SLA_MINUTES = {
    "HIGHEST": 2 * 60,
    "HIGH": 4 * 60,
    "MEDIUM": 24 * 60,
    "LOW": 48 * 60,
    "LOWEST": 60 * 60
}

def get_sla_minutes(priority_name):
    if not priority_name:
        return None
    priority_name = priority_name.upper()
    for key, minutes in SLA_MINUTES.items():
        if key in priority_name:
            return minutes
    return None


def _render_description_to_text(description_html):
    """Convert Jira's rendered (HTML) description into plain text lines."""

    text = description_html or ""

    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n", text)
    text = re.sub(r"(?i)</li>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)

    text = html.unescape(text)

    # Jira's rendered HTML frequently inserts non-breaking spaces (&nbsp;),
    # which html.unescape() turns into the U+00A0 character. It LOOKS like
    # a normal space but Python's \s regex class does NOT match it — so a
    # single stray nbsp anywhere around a label/colon can silently break
    # matching for that one field while everything around it works fine.
    # Normalizing it to a regular space up front avoids that entirely.
    text = text.replace("\xa0", " ")

    return text


# ==========================
# BULLET / LABEL BLOCK PARSING
# ==========================
#
# GNOC ticket descriptions are written as bullet lists, e.g.:
#
#   * Customers Impacted: ChargePoint Inc, Nextivity, ...
#   * Error Type: Lost Service, System Failure
#   * Start Time: 1st instance - 08:29 UTC, 2026-07-24
#     2nd instance - 02:00 UTC 24th july
#   * Sparkle Ticket: CSFA-00688931
#
# A single regex trying to capture "everything after label X until the
# next KNOWN label" is fragile: any unrecognized bullet (like "Sparkle
# Ticket:") lets the capture run straight through it and swallow real
# fields (Start Time, End Time, etc.) that come after.
#
# Instead, we split the whole text into (label, value) blocks up front —
# a new block starts at every bullet/label line, and absorbs any
# following non-bullet lines (continuations) until the next bullet line.
# Unrecognized labels just become blocks we never look up; they can no
# longer corrupt neighboring fields.

_HEADER_LINE_RE = re.compile(
    r"^\s*(?:[\*\-•]|\d{1,3}[.)])?\s*([A-Za-z0-9][A-Za-z0-9 /&'()]{1,40}?)\s*:\s*(.*)$"
)


def _split_labeled_blocks(text):
    """Split free-form text into (label, value) blocks based on bullet/label lines."""

    blocks = []
    current_label = None
    current_lines = []

    for line in (text or "").splitlines():
        match = _HEADER_LINE_RE.match(line)

        if match:
            if current_label is not None:
                blocks.append((current_label, "\n".join(current_lines).strip()))
            current_label = match.group(1).strip()
            current_lines = [match.group(2)] if match.group(2) else []
        elif current_label is not None:
            current_lines.append(line)

    if current_label is not None:
        blocks.append((current_label, "\n".join(current_lines).strip()))

    return blocks


def _normalize_label(label):
    label = label.lower().strip()
    label = re.sub(r"[^a-z0-9 ]", "", label)
    label = re.sub(r"\s+", " ", label).strip()
    return label


def _clean_field_value(value):
    """Collapse embedded newlines/tabs so the value is a single readable line."""

    value = (value or "").strip(" \n\t,")
    value = re.sub(r"[ \t]*\n[ \t]*", " | ", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    return value.strip(" |,")


# Maps each canonical output field to the set of normalized label
# variants (as they might literally appear in a ticket) that should be
# recognized as that field.
DESCRIPTION_FIELD_SYNONYMS = {
    "Customers": {
        "customer", "customers", "customers impacted", "customer impacted",
        "customers affected", "customer affected"
    },
    "Error Type": {"error type"},
    "MVNO": {"mvno", "mvnos", "roaming partner", "roaming partners"},
    "VPLMN": {"vplmn", "vplmns"},
    "Device type": {"device type"},
    "Country": {"country", "countries"},
    "Impact Description": {"customer impact", "impact description"},
    "Start Time": {
        "start time", "1st incident start time", "2nd incident start time",
        "3rd incident start time"
    },
    "End Time": {
        "end time", "1st incident end time", "2nd incident end time",
        "3rd incident end time"
    },
    "Duration": {"duration"},
}


def _extract_fields_from_blocks(blocks, synonyms):
    """Given (label, value) blocks, return {canonical_field: value} using synonyms.

    If more than one block maps to the same canonical field (e.g. a
    ticket that uses separate "1st Incident Start Time" / "2nd Incident
    Start Time" labels), the values are joined with " | " rather than
    the later one silently overwriting the earlier one.
    """

    result = {field: "" for field in synonyms}

    for raw_label, raw_value in blocks:
        normalized = _normalize_label(raw_label)
        value = _clean_field_value(raw_value)

        if not value:
            continue

        for field, variants in synonyms.items():
            if normalized in variants:
                if result[field]:
                    result[field] = f"{result[field]} | {value}"
                else:
                    result[field] = value
                break

    return result


def _format_custom_field_value(value):
    """
    Normalize a Jira custom field value into a single readable string.
    Custom fields can come back as a plain string, a single option object
    (e.g. {"value": "..."} for a select field), or a list of option
    objects (for multi-select/checkbox fields).
    """

    if value is None:
        return ""

    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(item.get("value") or item.get("name") or "")
            else:
                parts.append(str(item))
        return ", ".join(p for p in parts if p)

    if isinstance(value, dict):
        return value.get("value") or value.get("name") or ""

    return str(value)


def fetch_gnoc_ticket_details(gnoc_id):
    """
    Fetch a single GNOC Jira ticket and extract Customers, Error Type,
    MVNO, VPLMN, Device type, Country, Impact Description, Start Time,
    End Time, Duration (from the description) and Affected Services
    (from customfield_10330).
    Returns None if the ticket could not be fetched.
    """

    url = f"{JIRA_URL}/rest/api/3/issue/{gnoc_id}"

    params = {
        "fields": "description,customfield_10330",
        "expand": "renderedFields"
    }

    try:
        response = requests.get(
            url,
            params=params,
            auth=(USERNAME, PASSWORD),
            headers={"Accept": "application/json"}
        )

        if response.status_code != 200:
            print(f"Failed to fetch Jira ticket {gnoc_id}: {response.status_code}")
            return None

        data = response.json()

        description_html = data.get("renderedFields", {}).get("description", "")
        text = _render_description_to_text(description_html)

        blocks = _split_labeled_blocks(text)
        result = _extract_fields_from_blocks(blocks, DESCRIPTION_FIELD_SYNONYMS)

        raw_affected_services = data.get("fields", {}).get("customfield_10330")
        result["Affected Services"] = _format_custom_field_value(raw_affected_services)

        return result

    except Exception as e:
        print(f"Error fetching Jira ticket {gnoc_id}: {e}")
        return None


def fetch_jira_data(start_date, end_date):
    """
    Fetch Jira issues between start_date and end_date.
    Dates should be strings in YYYY-MM-DD format.
    Returns the output CSV filename.
    """
    JQL = f'project = GNOC AND issuetype = Incident AND created >= "{start_date}" AND created < "{end_date}" AND priority != P5-Lowest'

    print(f"Fetching Jira issues from {start_date} to {end_date}...")

    url = f"{JIRA_URL}/rest/api/3/search/jql"

    all_issues = []
    start_at = 0
    max_results = 100

    while True:
        params = {
            "jql": JQL,
            "startAt": start_at,
            "maxResults": max_results,
            "expand": "changelog",
            "fields": "summary,status,priority,assignee,reporter,creator,created,updated,resolutiondate,issuetype,project,components,customfield_10040,customfield_10563"
        }

        response = requests.get(
            url,
            params=params,
            auth=(USERNAME, PASSWORD),
            headers={"Accept": "application/json"}
        )

        if response.status_code != 200:
            print("Error:", response.status_code, response.text)
            return None

        data = response.json()
        issues = data.get("issues", [])

        if not issues:
            break

        all_issues.extend(issues)
        print(f"Fetched {len(all_issues)} tickets...")

        if len(issues) < max_results:
            break

        start_at += max_results

    print(f"Total tickets fetched: {len(all_issues)}")

    # ==========================
    # PROCESS ISSUES
    # ==========================
    rows = []
    now = datetime.now(timezone.utc)

    for idx, issue in enumerate(all_issues, start=1):
        fields = issue.get("fields", {})

        created_time = parser.parse(fields.get("created"))

        resolution_time = (
            parser.parse(fields.get("resolutiondate"))
            if fields.get("resolutiondate")
            else now
        )

        # ==========================
        # BUILD STATUS TIMELINE
        # ==========================
        status_changes = []

        for history in issue.get("changelog", {}).get("histories", []):
            for item in history.get("items", []):
                if item.get("field") == "status":
                    status_changes.append({
                        "from": item.get("fromString").upper() if item.get("fromString") else None,
                        "to": item.get("toString").upper(),
                        "time": parser.parse(history.get("created"))
                    })

        status_changes.sort(key=lambda x: x["time"])

        timeline = []

        if status_changes and status_changes[0]["from"]:
            initial_status = status_changes[0]["from"]
        else:
            initial_status = fields.get("status", {}).get("name", "").upper()

        if initial_status in VALID_STATUSES:
            timeline.append((initial_status, created_time))

        for change in status_changes:
            if change["to"] in VALID_STATUSES:
                timeline.append((change["to"], change["time"]))

        timeline.sort(key=lambda x: x[1])

        # ==========================
        # TIME PER STATUS
        # ==========================
        time_in_status = defaultdict(float)

        for i in range(len(timeline)):
            status, start = timeline[i]
            end = timeline[i + 1][1] if i + 1 < len(timeline) else resolution_time

            if status in FINAL_STATUSES:
                continue

            if end > start:
                time_in_status[status] += (end - start).total_seconds()

        # ==========================
        # CONVERT TO MINUTES
        # ==========================
        open_min = int(time_in_status.get("OPEN", 0) / 60)
        wip_min = int(time_in_status.get("WORK IN PROGRESS", 0) / 60)
        review_min = int(time_in_status.get("IN REVIEW", 0) / 60)
        completed_min = int(time_in_status.get("COMPLETED", 0) / 60)
        cancelled_min = int(
            (time_in_status.get("CANCELLED", 0) + time_in_status.get("CANCELED", 0)) / 60
        )
        closed_min = int(time_in_status.get("CLOSED", 0) / 60)

        # ==========================
        # SLA CALCULATION
        # ==========================
        time_to_resolution_min = open_min + wip_min + review_min

        priority_name = fields.get("priority", {}).get("name")
        sla_minutes = get_sla_minutes(priority_name)

        if sla_minutes is None:
            sla_status = None
            time_breached_min = 0
        else:
            if time_to_resolution_min > sla_minutes:
                sla_status = "Breached"
                time_breached_min = time_to_resolution_min - sla_minutes
            else:
                sla_status = "Met"
                time_breached_min = 0

        # ==========================
        # ROW OUTPUT
        # ==========================
        rows.append({
            "Issue key": issue.get("key"),
            "Summary": fields.get("summary"),
            "Issue Type": fields.get("issuetype", {}).get("name"),
            "Status": fields.get("status", {}).get("name"),
            "Project name": fields.get("project", {}).get("name"),
            "Project type": fields.get("project", {}).get("projectTypeKey"),
            "Priority": priority_name,
            "Resolution": fields.get("resolution", {}).get("name") if fields.get("resolution") else None,
            "Assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else "Unassigned",
            "Reporter": fields.get("reporter", {}).get("displayName"),
            "Creator": fields.get("creator", {}).get("displayName"),
            "Created": fields.get("created"),
            "Updated": fields.get("updated"),
            "Resolved": fields.get("resolutiondate"),
            "Components": ", ".join([c.get("name") for c in fields.get("components", [])]),
            "Source / Detection": fields.get("customfield_10040", {}).get("value") if isinstance(fields.get("customfield_10040"), dict) else fields.get("customfield_10040"),
            "Investigation Type": fields.get("customfield_10563", {}).get("value") if isinstance(fields.get("customfield_10563"), dict) else fields.get("customfield_10563"),

            "OPEN (Minutes)": open_min,
            "WORK IN PROGRESS (Minutes)": wip_min,
            "IN REVIEW (Minutes)": review_min,
            "COMPLETED (Minutes)": completed_min,
            "CANCELLED (Minutes)": cancelled_min,
            "CLOSED (Minutes)": closed_min,

            "Time to Resolution (Minutes)": time_to_resolution_min,
            "SLA Status": sla_status,
            "Time Breached (Minutes)": time_breached_min
        })

    # ==========================
    # EXPORT CSV
    # ==========================
    os.makedirs("data", exist_ok=True)
    filename = "data/GNOC_Incident_Time.csv"

    df = pd.DataFrame(rows)
    df.to_csv(filename, index=False)

    print(f"Exported {len(df)} tickets to {filename}")
    return filename


if __name__ == "__main__":
    if len(sys.argv) == 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
    else:
        start_date = input("Enter start date (YYYY-MM-DD): ").strip()
        end_date = input("Enter end date (YYYY-MM-DD): ").strip()

    fetch_jira_data(start_date, end_date)