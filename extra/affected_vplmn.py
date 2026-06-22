# import pandas as pd

# # Read CSV
# df = pd.read_csv("data/alerts.csv")

# vplmn_search = input(
#     "Enter VPLMN Name: "
# ).strip().lower()

# matching_rows = df[
#     df["VPLMN"]
#     .fillna("")
#     .str.lower()
#     .str.contains(vplmn_search, na=False)
# ]

# print(f"\nFound {len(matching_rows)} matching alerts\n")

# if matching_rows.empty:
#     print("No matches found.")
# else:

#     # Unique MVNOs
#     unique_mvnos = sorted(
#         matching_rows["MVNO"]
#         .fillna("")
#         .astype(str)
#         .str.strip()
#         .unique()
#     )

#     print("=" * 60)
#     print("Unique MVNOs")
#     print("=" * 60)

#     for mvno in unique_mvnos:
#         if mvno:
#             print(mvno)

#     print(f"\nTotal Unique MVNOs: {len(unique_mvnos)}")

#     print("\n" + "=" * 60)
#     print("Matching Alerts")
#     print("=" * 60)

#     for _, row in matching_rows.iterrows():

#         print(f"TinyId    : {row['TinyId']}")
#         print(f"MVNO      : {row['MVNO']}")
#         print(f"VPLMN     : {row['VPLMN']}")
#         print(f"Impact    : {row['Impact']}")
#         print(f"Message   : {row['Message']}")
#         print("-" * 60)

import pandas as pd

df = pd.read_csv("data/alerts.csv")

vplmn_search = input(
    "Enter VPLMN Name: "
).strip().lower()

matching_rows = df[
    df["VPLMN"]
    .fillna("")
    .str.lower()
    .str.contains(vplmn_search, na=False)
]

mvnos = set()

for value in matching_rows["MVNO"].dropna():

    for mvno in str(value).split(","):
        mvno = mvno.strip()

        if mvno:
            mvnos.add(mvno)

print("\nMatching MVNOs:\n")

for mvno in sorted(mvnos):
    print(mvno)

print(f"\nTotal Unique MVNOs: {len(mvnos)}")