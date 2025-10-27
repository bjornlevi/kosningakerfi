import math
import pandas as pd

districts = [
    ("Norðaustur", 31039, 10),
    ("Norðvestur", 22348, 7),
    ("Reykjavík n.", 47486, 11),
    ("Reykjavík s.", 47503, 11),
    ("Suður", 40994, 10),
    ("Suðvestur", 79052, 14),
]

TOTAL_SEATS = 63

df = pd.DataFrame(districts, columns=["District", "Voters", "Seats_2024"])
df["Voters_per_MP_2024"] = df["Voters"] / df["Seats_2024"]

# Hamilton (largest remainder) allocation proportional to voters
total_voters = df["Voters"].sum()
df["Quota"] = df["Voters"] * TOTAL_SEATS / total_voters
df["Floor"] = df["Quota"].apply(math.floor)
allocated = int(df["Floor"].sum())
remaining = TOTAL_SEATS - allocated
df["Remainder"] = df["Quota"] - df["Floor"]

# Assign remaining seats to the largest remainders
df = df.sort_values("Remainder", ascending=False)
df["Seats_proposed"] = df["Floor"]
for i in range(remaining):
    df.iloc[i, df.columns.get_loc("Seats_proposed")] += 1
df = df.sort_values("District")

# Proposed voters per MP and spreads
df["Voters_per_MP_proposed"] = df["Voters"] / df["Seats_proposed"]

current_min = df["Voters_per_MP_2024"].min()
current_max = df["Voters_per_MP_2024"].max()
current_ratio = current_max / current_min

prop_min = df["Voters_per_MP_proposed"].min()
prop_max = df["Voters_per_MP_proposed"].max()
prop_ratio = prop_max / prop_min

print("Current ratio (max/min):", current_ratio)
print("Proposed ratio (max/min):", prop_ratio)
print(df[[
    "District","Voters","Seats_2024","Voters_per_MP_2024",
    "Seats_proposed","Voters_per_MP_proposed"
]].round(3).to_string(index=False))

