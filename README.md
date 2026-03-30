# GNOC Incident Dashboard

A Flask-based dashboard for visualizing GNOC Jira incident data.

## Features

- **Date-driven Jira fetch** — pick start/end dates from the UI instead of hardcoding
- **4 Summary cards** — Tickets Created, Tickets Resolved, MTTR (Hours), SLA Breached
- **Pie charts** — Investigation Type & Detection Type breakdowns
- **Filterable & sortable incident table** — filter by Priority, Status, Reporter, Assignee, SLA Status, Investigation Type, Detection Type
- **Weekly historical summary table** — auto-updates when you fetch with a week label

## Setup

```bash
cd jira_dashboard

# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your Jira credentials

# 3. Run
python app.py
```

Open **http://localhost:5000** in your browser.

## Usage

1. Select a **Start Date** and **End Date** in the top bar
2. Optionally enter a **Week Label** (e.g., `W7`) to update the historical table
3. Click **Fetch from Jira** — the app pulls data and refreshes the dashboard
4. Use the **filter dropdowns** above the table to narrow results
5. Click any **column header** to sort

## Files

| File | Purpose |
|---|---|
| `app.py` | Flask server + API routes |
| `fetch_jira.py` | Jira REST API fetcher (importable or standalone CLI) |
| `templates/index.html` | Single-page dashboard UI |
| `data/past_weekly_data.csv` | Historical weekly summary (auto-updated) |
| `data/GNOC_Incident_Time.csv` | Current fetch output (auto-generated) |