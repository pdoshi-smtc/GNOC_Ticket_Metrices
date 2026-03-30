from collections import defaultdict
from dateutil import parser
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import pandas as pd
import requests
import os
import sys

load_dotenv()

# ==========================
# CONFIG
# ==========================
JIRA_URL = os.getenv("JIRA_BASE_URL", "https://sierrawireless.atlassian.net")
USERNAME = os.getenv("JIRA_USER_EMAIL")
PASSWORD = os.getenv("JIRA_API_TOKEN")

# ==========================
# DATE INPUT FROM USER
# ==========================
def get_date_input():
    print("\n=== GNOC Incident Report - Date Range Selection ===\n")
    
    while True:
        start_date = input("Enter START date (YYYY-MM-DD): ").strip()
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            break
        except ValueError:
            print("  Invalid format. Please use YYYY-MM-DD (e.g., 2026-03-07)")
    
    while True:
        end_date = input("Enter END date   (YYYY-MM-DD): ").strip()
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            if end_dt <= start_dt:
                print("  End date must be after the start date.")
                continue
            break
        except ValueError:
            print("  Invalid format. Please use YYYY-MM-DD (e.g., 2026-03-14)")
    
    return start_date, end_date

start_date, end_date = get_date_input()

JQL = (
    f'project = GNOC AND issuetype = Incident '
    f'AND created >= "{start_date}" AND created < "{end_date}" '
    f'AND priority != P5-Lowest'
)

print(f"\nJQL: {JQL}\n")

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


# ==========================
# FETCH ISSUES (REST API v3)
# ==========================
print("Fetching Jira issues via REST API...")

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
        break

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

    if idx % 100 == 0:
        print(f"Processed {idx} tickets...")

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

    # Initial status
    if status_changes and status_changes[0]["from"]:
        initial_status = status_changes[0]["from"]
    else:
        initial_status = fields.get("status", {}).get("name", "").upper()

    if initial_status in VALID_STATUSES:
        timeline.append((initial_status, created_time))

    # Apply transitions
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
        "Source / Detection": fields.get("customfield_10040"),
        "Investigation Type": fields.get("customfield_10563"),

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

print(f"\nExported {len(df)} tickets to {filename}")
