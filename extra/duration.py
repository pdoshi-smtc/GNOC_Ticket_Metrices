import pandas as pd
import re

MVNOS = [
    "SPARKLE",
    "BICS",
    "JT",
    "MBQT",
    "ORANGE_901",
    "PCCW",
    "MAINGATE"
]

df = pd.read_csv("data/alerts.csv")

# Only roaming alerts
df = df[
    df["Message"]
    .fillna("")
    .str.contains("roaming", case=False, na=False)
]

duration_sum = {mvno: 0 for mvno in MVNOS}


def duration_to_minutes(duration):

    if pd.isna(duration):
        return 0

    duration = str(duration).strip().lower()

    minutes = re.search(r"(\d+)\s*minute", duration)
    hours = re.search(r"(\d+)\s*hour", duration)

    total = 0

    if hours:
        total += int(hours.group(1)) * 60

    if minutes:
        total += int(minutes.group(1))

    return total


for _, row in df.iterrows():

    mvno_field = str(row.get("MVNO", "")).upper()

    duration = duration_to_minutes(
        row.get("Duration", "")
    )

    mvnos = [
        x.strip()
        for x in mvno_field.split(",")
        if x.strip()
    ]

    for mvno in mvnos:

        if mvno in duration_sum:
            duration_sum[mvno] += duration

print("\nTotal Roaming Impact Duration\n")
print("-" * 40)

for mvno, minutes in sorted(
    duration_sum.items(),
    key=lambda x: x[1],
    reverse=True
):
    print(
        f"{mvno:<15} {minutes:>5} mins "
        f"({minutes/60:.2f} hrs)"
    )