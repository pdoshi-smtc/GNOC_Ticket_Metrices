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

# Filter only VPLMN DOWN alerts
vplmn_df = df[
    df["Message"].fillna("").str.contains("VPLMN DOWN", case=False, regex=False)
].copy()

# Identify alerts with missing VPLMN (no longer printed)
missing_vplmn = vplmn_df[
    vplmn_df["VPLMN"].isna() | (vplmn_df["VPLMN"].str.strip() == "")
].copy()

# Keep only rows with VPLMN present
vplmn_df = vplmn_df[
    vplmn_df["VPLMN"].notna() & (vplmn_df["VPLMN"].str.strip() != "")
].copy()

# Clean columns
vplmn_df["MVNO"] = vplmn_df["MVNO"].fillna("")

vplmn_df["Duration"] = (
    vplmn_df["Duration"]
    .str.extract(r"(\d+\.?\d*)")[0]
    .astype(float)
)

# Prepare final table (sorted by Duration)
final_df = vplmn_df[
    ["TinyId", "CreatedAt", "VPLMN", "Country", "MVNO", "Duration"]
].sort_values(
    by="Duration",
    ascending=False
)

# Prepare missing_vplmn rows to match the same columns
# (fill any columns not present in missing_vplmn with blank/NaN)
missing_export = missing_vplmn.reindex(
    columns=["TinyId", "CreatedAt", "VPLMN", "Country", "MVNO", "Duration"]
)

# Append missing_vplmn rows at the very end of the table
combined_df = pd.concat([final_df, missing_export], ignore_index=True)

# Export
combined_df.to_excel(
    "data/VPLMN_MVNO_table.xlsx",
    index=False
)