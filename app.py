from flask import Flask, render_template, request, jsonify
from fetch_jira import fetch_jira_data
import pandas as pd
import os
import json

app = Flask(__name__)

DATA_FILE = "data/GNOC_Incident_Time.csv"
PAST_DATA_FILE = "data/past_weekly_data.csv"


def load_data():
    """Load the current incident CSV data."""
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame()
    df = pd.read_csv(DATA_FILE)
    return df


def load_past_data():
    """Load past weekly summary CSV."""
    if not os.path.exists(PAST_DATA_FILE):
        return pd.DataFrame()
    df = pd.read_csv(PAST_DATA_FILE)
    return df


def compute_summary(df):
    """Compute summary cards from the dataframe."""
    if df.empty:
        return {
            "tickets_created": 0,
            "tickets_resolved": 0,
            "mttr_hours": 0,
            "sla_breached": 0
        }

    tickets_created = len(df)

    final = {"Completed", "Closed", "Cancelled", "Canceled"}
    tickets_resolved = len(df[df["Status"].str.strip().str.title().isin(final)])

    resolution_minutes = df["Time to Resolution (Minutes)"].dropna()
    if len(resolution_minutes) > 0 and tickets_resolved > 0:
        resolved_df = df[df["Status"].str.strip().str.title().isin(final)]
        mttr_hours = round(resolved_df["Time to Resolution (Minutes)"].mean() / 60, 2)
    else:
        mttr_hours = 0

    sla_breached = len(df[df["SLA Status"] == "Breached"])

    return {
        "tickets_created": int(tickets_created),
        "tickets_resolved": int(tickets_resolved),
        "mttr_hours": mttr_hours,
        "sla_breached": int(sla_breached)
    }


def compute_pie_data(df, column):
    """Compute pie chart data for a given column."""
    if df.empty or column not in df.columns:
        return []
    counts = df[column].fillna("Unknown").value_counts()
    return [{"label": str(k), "value": int(v)} for k, v in counts.items()]


def build_table_data(df):
    """Build the main incident table data."""
    if df.empty:
        return []

    cols = [
        "Issue key", "Time to Resolution (Minutes)", "Summary",
        "Investigation Type", "Source / Detection", "Reporter",
        "Priority", "Status", "Assignee", "SLA Status"
    ]
    available_cols = [c for c in cols if c in df.columns]
    subset = df[available_cols].copy()

    # Convert resolution to hours
    if "Time to Resolution (Minutes)" in subset.columns:
        subset["Time to Resolution (Hours)"] = round(subset["Time to Resolution (Minutes)"] / 60, 2)
        subset.drop(columns=["Time to Resolution (Minutes)"], inplace=True)
        # Reorder
        new_cols = ["Issue key", "Time to Resolution (Hours)"] + [
            c for c in subset.columns if c not in ["Issue key", "Time to Resolution (Hours)"]
        ]
        subset = subset[new_cols]

    return subset.fillna("").to_dict(orient="records")


def get_filter_options(df):
    """Extract unique filter options from the data."""
    filters = {}
    for col in ["Investigation Type", "Source / Detection", "Priority", "Status", "Reporter", "Assignee", "SLA Status"]:
        if col in df.columns:
            vals = sorted(df[col].dropna().unique().tolist())
            filters[col] = vals
    return filters


def update_past_data(df, week_label):
    """Update the past weekly summary table with current week data."""
    summary = compute_summary(df)

    # Count by priority
    p1 = len(df[df["Priority"].str.contains("P1", case=False, na=False)]) if "Priority" in df.columns else 0
    p2 = len(df[df["Priority"].str.contains("P2", case=False, na=False)]) if "Priority" in df.columns else 0
    p3 = len(df[df["Priority"].str.contains("P3", case=False, na=False)]) if "Priority" in df.columns else 0
    p4 = len(df[df["Priority"].str.contains("P4", case=False, na=False)]) if "Priority" in df.columns else 0

    # MTTR by priority
    final = {"Completed", "Closed", "Cancelled", "Canceled"}
    resolved_df = df[df["Status"].str.strip().str.title().isin(final)] if not df.empty else pd.DataFrame()

    def mttr_for_priority(prefix):
        if resolved_df.empty or "Priority" not in resolved_df.columns:
            return 0
        subset = resolved_df[resolved_df["Priority"].str.contains(prefix, case=False, na=False)]
        if subset.empty:
            return 0
        return round(subset["Time to Resolution (Minutes)"].mean() / 60, 0)

    p1_mttr = mttr_for_priority("P1")
    p2_mttr = mttr_for_priority("P2")
    p3_mttr = mttr_for_priority("P3")
    p4_mttr = mttr_for_priority("P4")

    new_row = {
        "Week": week_label,
        "Tickets Created": summary["tickets_created"],
        "Tickets Resolved": summary["tickets_resolved"],
        "P1 Tickets": p1,
        "P2 Tickets": p2,
        "P3 Tickets": p3,
        "P4 Tickets": p4,
        "MTTR (hours)": summary["mttr_hours"],
        "P1 - MTTR": p1_mttr,
        "P2 - MTTR": p2_mttr,
        "P3 - MTTR": p3_mttr,
        "P4 - MTTR": p4_mttr,
        "Major (P1/P2) Incidents": p1 + p2,
        "Overall MTTR (hours)": summary["mttr_hours"],
        "Backlog Aging (HOURS)": "NA",
        "Backlog Ticket Volume": "NA"
    }

    if os.path.exists(PAST_DATA_FILE):
        past_df = pd.read_csv(PAST_DATA_FILE)
        # Remove existing row for same week if re-fetching
        past_df = past_df[past_df["Week"] != week_label]
        past_df = pd.concat([past_df, pd.DataFrame([new_row])], ignore_index=True)
    else:
        os.makedirs("data", exist_ok=True)
        past_df = pd.DataFrame([new_row])

    past_df.to_csv(PAST_DATA_FILE, index=False)
    return past_df


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    """Fetch fresh data from Jira."""
    data = request.json
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    week_label = data.get("week_label", "")

    if not start_date or not end_date:
        return jsonify({"error": "start_date and end_date are required"}), 400

    try:
        result = fetch_jira_data(start_date, end_date)
        if result is None:
            return jsonify({"error": "Failed to fetch data from Jira"}), 500

        df = load_data()
        if week_label:
            update_past_data(df, week_label)

        return jsonify({"success": True, "count": len(df)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard")
def api_dashboard():
    """Return all dashboard data as JSON."""
    df = load_data()
    past_df = load_past_data()

    summary = compute_summary(df)
    investigation_pie = compute_pie_data(df, "Investigation Type")
    detection_pie = compute_pie_data(df, "Source / Detection")
    table_data = build_table_data(df)
    filters = get_filter_options(df)

    past_table = past_df.fillna("NA").to_dict(orient="records") if not past_df.empty else []

    return jsonify({
        "summary": summary,
        "investigation_pie": investigation_pie,
        "detection_pie": detection_pie,
        "table": table_data,
        "filters": filters,
        "past_table": past_table
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)