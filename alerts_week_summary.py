import pandas as pd

# =====================================
# READ ALERTS CSV
# =====================================

df = pd.read_csv("data/alerts.csv")

# Convert CreatedAt column to datetime
df["CreatedAt"] = pd.to_datetime(
    df["CreatedAt"],
    format="%Y-%m-%d %H:%M:%S UTC",
    errors="coerce"
)

# =====================================
# MESSAGE SERIES
# =====================================

message_series = df["Message"].fillna("").str.upper()

# =====================================
# ALERT COUNTS
# =====================================

vplmn_count = (
    message_series
    .str.contains("VPLMN", regex=False)
    .sum()
)

roaming_count = (
    message_series
    .str.contains("ROAMING", regex=False)
    .sum()
)

lost_service_count = (
    message_series
    .str.contains("LOST-SERVICE", regex=False)
    .sum()
)

system_failure_count = (
    message_series
    .str.contains("SYSTEM FAILURE", regex=False)
    .sum()
)

total_alerts = vplmn_count + roaming_count

lost_service_percentage = (
    (lost_service_count / total_alerts) * 100
    if total_alerts > 0 else 0
)

system_failure_percentage = (
    (system_failure_count / total_alerts) * 100
    if total_alerts > 0 else 0
)

# =====================================
# week-wise SUMMARY
# =====================================

df["Sort Date"] = df["CreatedAt"].dt.date

weekly_summary = pd.DataFrame(
    sorted(df["Sort Date"].dropna().unique()),
    columns=["Sort Date"]
)

weekly_summary["Created Date"] = pd.to_datetime(
    weekly_summary["Sort Date"]
).dt.strftime("%a %d")

weekly_summary["VPLMN Down"] = (
    df[
        message_series.str.contains(
            "VPLMN",
            regex=False
        )
    ]
    .groupby("Sort Date")
    .size()
    .reindex(
        weekly_summary["Sort Date"],
        fill_value=0
    )
    .values
)

weekly_summary["Roaming Partner Down"] = (
    df[
        message_series.str.contains(
            "ROAMING",
            regex=False
        )
    ]
    .groupby("Sort Date")
    .size()
    .reindex(
        weekly_summary["Sort Date"],
        fill_value=0
    )
    .values
)

weekly_summary["Lost Service"] = (
    df[
        message_series.str.contains(
            "LOST-SERVICE",
            regex=False
        )
    ]
    .groupby("Sort Date")
    .size()
    .reindex(
        weekly_summary["Sort Date"],
        fill_value=0
    )
    .values
)

weekly_summary["System Failure"] = (
    df[
        message_series.str.contains(
            "SYSTEM FAILURE",
            regex=False
        )
    ]
    .groupby("Sort Date")
    .size()
    .reindex(
        weekly_summary["Sort Date"],
        fill_value=0
    )
    .values
)

weekly_summary = weekly_summary[
    [
        "Created Date",
        "VPLMN Down",
        "Roaming Partner Down",
        "Lost Service",
        "System Failure"
    ]
]

# =====================================
# PRINT SUMMARY
# =====================================

print("\n========== ALERT SUMMARY ==========")
print(f"VPLMN Down Alerts          : {vplmn_count}")
print(f"Roaming Partner Down Alerts: {roaming_count}")
print(f"Total Alerts               : {total_alerts}")
print(
    f"Lost Service Alerts        : "
    f"{lost_service_count} "
    f"({lost_service_percentage:.2f}%)"
)

print(
    f"System Failure Alerts      : "
    f"{system_failure_count} "
    f"({system_failure_percentage:.2f}%)"
)

print("\n========== DAY WISE ==========")
print(weekly_summary.to_string(index=False))

# =====================================
# SAVE week-wise SUMMARY
# =====================================

weekly_summary.to_csv(
    "data/alert_weekly_summary.csv",
    index=False
)

print("\nSaved week-wise summary to data/alert_weekly_summary.csv")



# =====================================
# SAVE VPLMN-MVNO details table
# ====================================

import pandas as pd

df = pd.read_csv("data/alerts.csv")

# Remove rows without VPLMN
df = df[df["VPLMN"].notna()]

# Clean MVNO column
df["MVNO"] = (
    df["MVNO"]
    .fillna("")
    .astype(str)
)

# Extract numeric part from Duration
df["Duration"] = (
    df["Duration"]
    .astype(str)
    .str.extract(r"(\d+\.?\d*)")[0]
    .astype(float)
)

# Select required columns
result = df[
    [
        "TinyId",
        "CreatedAt",
        "VPLMN",
        "MVNO",
        "Duration"
    ]
].copy()

# Sort by Duration descending
result = result.sort_values(
    by="Duration",
    ascending=False
)

# print(result.to_string(index=False))

# Export
result.to_excel(
    r"data\VPLMN_MVNO_table.xlsx",
    index=False
)

print(
    "\nSaved VPLMN_MVNO details to data/VPLMN_MVNO_table.xlsx"
)