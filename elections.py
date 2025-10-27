import math
from typing import Dict, Optional
import pandas as pd

# --- Constituencies (your 63-seat plan)
CONSTITUENCIES = [
    ("Norðaustur", 31039, 7),
    ("Norðvestur", 22348, 5),
    ("Reykjavík n.", 47486, 11),
    ("Reykjavík s.", 47503, 11),
    ("Suður", 40994, 10),
    ("Suðvestur", 79052, 19),
]
const_df = pd.DataFrame(CONSTITUENCIES, columns=["Constituency","Voters","Seats"])
const_df["Voters_per_MP"] = const_df["Voters"] / const_df["Seats"]

def allocate_national_seats(total_seats: int, party_votes_total: Dict[str, int]):
    total_votes = sum(party_votes_total.values())
    if total_votes == 0:
        raise ValueError("Total votes are zero; cannot allocate seats.")

    df = pd.DataFrame(
        [{"Party": p, "Votes": v, "Quota": v * total_seats / total_votes}
         for p, v in party_votes_total.items()]
    )

    df["Floor"] = df["Quota"].apply(math.floor)
    df["VoteShare"] = df["Votes"] / total_votes
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

    return df.set_index("Party")["Seats"].to_dict(), df.sort_values("Votes", ascending=False), logs


def assign_constituency_seats(const_df: pd.DataFrame,
                              party_seats: Dict[str, int],
                              party_votes_by_const: Dict[str, Dict[str, int]]):
    c_remain = {row.Constituency: int(row.Seats) for _, row in const_df.iterrows()}
    vpmp = {row.Constituency: float(row.Voters_per_MP) for _, row in const_df.iterrows()}
    votes = {p: {c: int(party_votes_by_const.get(p, {}).get(c, 0)) for c in c_remain}
             for p in party_seats}
    p_remain = {p: int(s) for p, s in party_seats.items()}
    alloc = {p: {c: 0 for c in c_remain} for p in party_seats}
    logs = []
    total_to_assign = sum(p_remain.values())
    assigned = 0
    while assigned < total_to_assign:
        candidates = []
        for p, sleft in p_remain.items():
            if sleft <= 0:
                continue
            for c, cleft in c_remain.items():
                if cleft <= 0:
                    continue
                candidates.append((votes[p][c], p, c))
        if not candidates:
            break
        # sort by highest cell votes, then party total votes, then party+const name
        candidates.sort(key=lambda x: (x[0], sum(votes[x[1]].values()), x[1], x[2]), reverse=True)
        top_votes, party, const = candidates[0]
        moved_note = None
        if top_votes == 0:
            # last-resort placement if a party has no votes anywhere with seats left
            const = max([cc for cc, cleft in c_remain.items() if cleft > 0], key=lambda cc: c_remain[cc])
            moved_note = "(no votes left anywhere; forced placement)"
        alloc[party][const] += 1
        p_remain[party] -= 1
        c_remain[const] -= 1
        old_party_total = sum(votes[party].values())
        old_cell = votes[party][const]
        deduct = vpmp[const]
        votes[party][const] = max(0, votes[party][const] - deduct)
        new_party_total = sum(votes[party].values())
        msg = f"{party} got a seat in {const} (votes there: {old_cell:.0f} -> {votes[party][const]:.0f}; party total: {old_party_total:.0f} -> {new_party_total:.0f})"
        if moved_note:
            msg = f"{party} seat was moved to {const} {moved_note}"
        logs.append(msg)
        assigned += 1
    alloc_df = pd.DataFrame(alloc).T[const_df['Constituency'].tolist()]
    leftover_const = {c: s for c, s in c_remain.items() if s != 0}
    leftover_party = {p: s for p, s in p_remain.items() if s != 0}
    return alloc_df, logs, leftover_const, leftover_party

def normalize_shares_to_votes(shares: Dict[str, Dict[str, float]],
                              const_df: pd.DataFrame,
                              turnout_rate: float = 0.80,
                              total_votes_override: Optional[Dict[str, int]] = None,
                              missing_party_policy: str = "ignore"):
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
            s = shares[p].get(c, 0.0)
            v = int(round(s * factor * total_votes_c))
            votes.setdefault(p, {})[c] = v
    return votes

# --- 2024 shares (fractions) for all parties
shares = {
  "S": {"Reykjavík n.": 0.261, "Reykjavík s.": 0.229, "Suðvestur": 0.193, "Norðvestur": 0.159, "Norðaustur": 0.213, "Suður": 0.173},
  "D": {"Reykjavík n.": 0.174, "Reykjavík s.": 0.176, "Suðvestur": 0.234, "Norðvestur": 0.180, "Norðaustur": 0.150, "Suður": 0.196},
  "C": {"Reykjavík n.": 0.163, "Reykjavík s.": 0.177, "Suðvestur": 0.201, "Norðvestur": 0.126, "Norðaustur": 0.094, "Suður": 0.112},
  "F": {"Reykjavík n.": 0.119, "Reykjavík s.": 0.135, "Suðvestur": 0.110, "Norðvestur": 0.167, "Norðaustur": 0.143, "Suður": 0.200},
  "M": {"Reykjavík n.": 0.089, "Reykjavík s.": 0.105, "Suðvestur": 0.120, "Norðvestur": 0.148, "Norðaustur": 0.157, "Suður": 0.136},
  "B": {"Reykjavík n.": 0.040, "Reykjavík s.": 0.044, "Suðvestur": 0.059, "Norðvestur": 0.133, "Norðaustur": 0.142, "Suður": 0.120},
  "J": {"Reykjavík n.": 0.059, "Reykjavík s.": 0.056, "Suðvestur": 0.028, "Norðvestur": 0.034, "Norðaustur": 0.038, "Suður": 0.024},
  "P": {"Reykjavík n.": 0.054, "Reykjavík s.": 0.039, "Suðvestur": 0.028, "Norðvestur": 0.018, "Norðaustur": 0.018, "Suður": 0.013},
  "V": {"Reykjavík n.": 0.029, "Reykjavík s.": 0.029, "Suðvestur": 0.015, "Norðvestur": 0.027, "Norðaustur": 0.038, "Suður": 0.013},
  "L": {"Reykjavík n.": 0.010, "Reykjavík s.": 0.010, "Suðvestur": 0.011, "Norðvestur": 0.008, "Norðaustur": 0.008, "Suður": 0.013},
  "Y": {"Reykjavík n.": 0.001, "Reykjavík s.": 0.000, "Suðvestur": 0.000, "Norðvestur": 0.000, "Norðaustur": 0.000, "Suður": 0.000}
}

def main():
    votes_by_const = normalize_shares_to_votes(shares, const_df, turnout_rate=0.8, missing_party_policy="redistribute")
    party_totals = {p: sum(votes_by_const.get(p, {}).values()) for p in shares}
    party_seats, nat_df, rem_logs = allocate_national_seats(63, party_totals)
    alloc_df, seat_logs, leftover_const, leftover_party = assign_constituency_seats(const_df, party_seats, votes_by_const)

    # --- PRINT: National results
    print("=== NATIONAL RESULTS (caps + remainders) ===")
    nat_view = nat_df.copy()
    nat_view["Assigned_Seats"] = nat_view["Party"].map(party_seats.get)
    nat_view = nat_view[["Party","Votes", "VoteShare", "Quota","Floor","Fraction","Cap","Assigned_Seats"]]
    print(nat_view.sort_values(["Assigned_Seats","Votes"], ascending=[False,False])
              .to_string(index=False,
                         formatters={"Quota":"{:,.3f}".format, "Fraction":"{:,.3f}".format}))

    # --- PRINT: Constituency seat matrix
    print("\n=== CONSTITUENCY SEAT ALLOCATION (Party x Constituency) ===")
    print(alloc_df.assign(TOTAL=alloc_df.sum(axis=1)).to_string())

    # --- PRINT: Step-by-step seat assignment
    print("\n=== STEP-BY-STEP ASSIGNMENT LOG ===")
    for ln in seat_logs:
        print(ln)

    # --- Warn if something didn't perfectly fill
    if leftover_const:
        print("\n[WARN] Leftover constituency seats (should be 0):", leftover_const)
    if leftover_party:
        print("\n[WARN] Leftover party seats (should be 0):", leftover_party)

    # --- OPTIONAL: write the log to a file too
    with open("analysis_assignment_log.txt", "w", encoding="utf-8") as f:
        for ln in seat_logs:
            f.write(ln + "\n")

if __name__ == "__main__":
    main()

