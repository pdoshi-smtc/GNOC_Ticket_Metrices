import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import re

# ==========================
# CONFIG
# ==========================

CSV_FILE = "data/alerts.csv"
TOP_VPLMNS = 25
TOP_MVNOS = 25

# ==========================
# HELPER FUNCTION
# ==========================

def normalize_name(name):

    name = str(name).strip()

    if not name:
        return ""

    # Preserve acronyms/codes
    if name.upper() == name:
        return name

    return name.title()

# ==========================
# LOAD CSV
# ==========================

df = pd.read_csv(CSV_FILE)

# ==========================
# BUILD VPLMN-MVNO PAIRS
# ==========================

records = []

for _, row in df.iterrows():

    vplmn_value = str(row.get("VPLMN", ""))
    mvno_value = str(row.get("MVNO", ""))

    # Split on comma, semicolon, slash, and "and"
    # Intentionally NOT splitting on &
    vplmns = re.split(
        r"\s*(?:,|;|/|\band\b)\s*",
        vplmn_value,
        flags=re.IGNORECASE
    )

    mvnos = re.split(
        r"\s*(?:,|;|/|\band\b)\s*",
        mvno_value,
        flags=re.IGNORECASE
    )

    vplmns = [
        str(v).strip().upper()
        for v in str(row.get("VPLMN", "")).split(",")
        if str(v).strip()
    ]

    mvnos = [
        str(m).strip().upper()
        for m in str(row.get("MVNO", "")).split(",")
        if str(m).strip()
    ]

    for vplmn in vplmns:
        for mvno in mvnos:

            records.append({
                "VPLMN": vplmn,
                "MVNO": mvno
            })

# ==========================
# CREATE MATRIX
# ==========================

pairs_df = pd.DataFrame(records)

heatmap_df = pd.crosstab(
    pairs_df["VPLMN"],
    pairs_df["MVNO"]
)

# ==========================
# SORT BY IMPACT
# ==========================

heatmap_df = heatmap_df.loc[
    heatmap_df.sum(axis=1)
    .sort_values(ascending=False)
    .index,

    heatmap_df.sum(axis=0)
    .sort_values(ascending=False)
    .index
]

# ==========================
# KEEP TOP N
# ==========================

heatmap_df = heatmap_df.iloc[
    :TOP_VPLMNS,
    :TOP_MVNOS
]

# ==========================
# PLOT
# ==========================

plt.figure(figsize=(20, 12))

sns.heatmap(
    heatmap_df,
    annot=True,
    fmt="d",
    cmap="Blues",
    linewidths=0.5,
    linecolor="white",
    cbar_kws={
        "label": "Incident Count"
    }
)

plt.title(
    "",
    fontsize=18,
    fontweight="bold"
)

plt.xlabel(
    "MVNO",
    fontsize=12,
    fontweight="bold"
)

plt.ylabel(
    "VPLMN",
    fontsize=12,
    fontweight="bold"
)

plt.xticks(
    rotation=45,
    ha="right",
    fontweight="bold"

)

plt.yticks(
    rotation=0,

)

plt.tight_layout()

# Save high-quality image for PPT
plt.savefig(
    "data/vplmn_mvno_heatmap.png",
    dpi=300,
    bbox_inches="tight"
)

print(
    f"Heatmap saved as data/vplmn_mvno_heatmap.png"
)

plt.show()