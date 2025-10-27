# utils.py
from typing import Dict, Optional
import pandas as pd

CONSTITUENCIES = [
    ("NA", 31039, 7),
    ("NV", 22348, 5),
    ("RN", 47486, 11),
    ("RS", 47503, 11),
    ("SU", 40994, 10),
    ("SV", 79052, 19),
]

def build_const_df() -> pd.DataFrame:
    df = pd.DataFrame(CONSTITUENCIES, columns=["Constituency","Voters","Seats"])
    df["Voters_per_MP"] = df["Voters"] / df["Seats"]
    return df

def normalize_shares_to_votes(
    shares: Dict[str, Dict[str, float]],
    const_df: pd.DataFrame,
    turnout_rate: float = 0.80,
    total_votes_override: Optional[Dict[str, int]] = None,
    missing_party_policy: str = "redistribute",
) -> Dict[str, Dict[str, int]]:
    """
    Convert constituency-level shares (0..1) into integer votes.
    If 'redistribute', scales given party shares in each constituency to sum to 1.0.
    """
    votes = {}
    for _, row in const_df.iterrows():
        c = row.Constituency
        reg = row.Voters
        total_votes_c = int(round((total_votes_override or {}).get(c, reg * turnout_rate)))
        sum_shares = sum(shares.get(p, {}).get(c, 0.0) for p in shares)
        factor = 1.0
        if sum_shares > 0 and missing_party_policy == "redistribute":
            factor = 1.0 / sum_shares
        for p in shares:
            s = shares[p].get(c, 0.0) * factor
            v = int(round(s * total_votes_c))
            votes.setdefault(p, {})[c] = v
    return votes
