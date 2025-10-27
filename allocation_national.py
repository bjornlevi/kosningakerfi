import math
from typing import Dict, Tuple
import pandas as pd

def allocate_national_seats(total_seats: int, party_votes_total: Dict[str, int]) -> Tuple[Dict[str, int], pd.DataFrame, list]:
    total_votes = sum(party_votes_total.values())
    if total_votes == 0:
        raise ValueError("Total votes are zero; cannot allocate seats.")

    df = pd.DataFrame(
        [{"Party": p, "Votes": v, "Quota": v * total_seats / total_votes}
         for p, v in party_votes_total.items()]
    )

    # add vote share
    df["VoteShare"] = df["Votes"] / total_votes

    # rounding & caps
    df["Floor"] = df["Quota"].apply(math.floor)
    df["Cap"] = df["Quota"].apply(math.ceil)
    df["Fraction"] = df["Quota"] - df["Floor"]
    df["Seats"] = df["Floor"]

    remaining = total_seats - int(df["Seats"].sum())
    logs = []

    while remaining > 0:
        elig = df[df["Seats"] < df["Cap"]].copy()
        if elig.empty:
            break
        elig = elig.sort_values(by=["Fraction", "Votes", "Party"], ascending=[False, False, True])
        winner_party = elig.iloc[0]["Party"]
        df.loc[df["Party"] == winner_party, "Seats"] += 1
        remaining -= 1
        logs.append(f"Remainder seat -> {winner_party}")

    seats_by_party = df.set_index("Party")["Seats"].astype(int).to_dict()
    details = df.sort_values("Votes", ascending=False)
    return seats_by_party, details, logs
