# run_election.py
import pandas as pd
from allocation_national import allocate_national_seats
from assignment_greedy import assign_constituency_seats_greedy
from assignment_maxflow import assign_constituency_seats_optimal
from utils import build_const_df, normalize_shares_to_votes

# 2024 constituency shares (fractions)
shares = {
  "S": {"RN": 0.261, "RS": 0.229, "SV": 0.193, "NV": 0.159, "NA": 0.213, "SU": 0.173},
  "D": {"RN": 0.174, "RS": 0.176, "SV": 0.234, "NV": 0.180, "NA": 0.150, "SU": 0.196},
  "C": {"RN": 0.163, "RS": 0.177, "SV": 0.201, "NV": 0.126, "NA": 0.094, "SU": 0.112},
  "F": {"RN": 0.119, "RS": 0.135, "SV": 0.110, "NV": 0.167, "NA": 0.143, "SU": 0.200},
  "M": {"RN": 0.089, "RS": 0.105, "SV": 0.120, "NV": 0.148, "NA": 0.157, "SU": 0.136},
  "B": {"RN": 0.040, "RS": 0.044, "SV": 0.059, "NV": 0.133, "NA": 0.142, "SU": 0.120},
  "J": {"RN": 0.059, "RS": 0.056, "SV": 0.028, "NV": 0.034, "NA": 0.038, "SU": 0.024},
  "P": {"RN": 0.054, "RS": 0.039, "SV": 0.028, "NV": 0.018, "NA": 0.018, "SU": 0.013},
  "V": {"RN": 0.029, "RS": 0.029, "SV": 0.015, "NV": 0.027, "NA": 0.038, "SU": 0.013},
  "L": {"RN": 0.010, "RS": 0.010, "SV": 0.011, "NV": 0.008, "NA": 0.008, "SU": 0.013},
  "Y": {"RN": 0.001, "RS": 0.000, "SV": 0.000, "NV": 0.000, "NA": 0.000, "SU": 0.000}
}

def main():
    const_df = build_const_df()

    # Build integer votes from shares (80% turnout; redistributes missing to sum to 1)
    votes_by_const = normalize_shares_to_votes(
        shares, const_df, turnout_rate=0.80, missing_party_policy="redistribute"
    )

    # NATIONAL SEATS (same for both methods)
    party_totals = {p: sum(votes_by_const.get(p, {}).values()) for p in shares}
    party_seats, nat_df, rem_logs = allocate_national_seats(63, party_totals)

    # --- Print national analysis
    nat_view = nat_df.copy()
    nat_view["Assigned_Seats"] = nat_view["Party"].map(party_seats.get)
    print("=== NATIONAL RESULTS (caps + remainders) ===")
    print(nat_view[["Party","Votes","VoteShare","Quota","Floor","Fraction","Cap","Assigned_Seats"]]
          .sort_values(["Assigned_Seats","Votes"], ascending=[False,False])
          .to_string(index=False, formatters={"VoteShare":"{:,.3f}".format, "Quota":"{:,.3f}".format, "Fraction":"{:,.3f}".format}))
    print("\nRemainder assignment log:")
    for ln in rem_logs:
        print("  " + ln)

    # --- GREEDY ASSIGNMENT
    from assignment_greedy import assign_constituency_seats_greedy
    alloc_greedy, logs_greedy, leftover_const_g, leftover_party_g = assign_constituency_seats_greedy(
        const_df=const_df, party_seats=party_seats, party_votes_by_const=votes_by_const
    )
    print("\n=== GREEDY ASSIGNMENT (Party x Constituency) ===")
    print(alloc_greedy.assign(TOTAL=alloc_greedy.sum(axis=1)).to_string())
    if leftover_const_g or leftover_party_g:
        print("\n[Greedy WARN] Leftover constituency seats:", leftover_const_g, "Leftover party seats:", leftover_party_g)
    greedy_tbl = alloc_greedy.assign(TOTAL=alloc_greedy.sum(axis=1))
    # append the SUM row (column totals, including TOTAL)
    sum_row = greedy_tbl.sum(axis=0, numeric_only=True)
    greedy_tbl.loc["SUM"] = sum_row

    print("\n=== GREEDY ASSIGNMENT (Party x Constituency) ===")
    print(greedy_tbl.to_string())

    # --- OPTIMAL (MAX-FLOW) ASSIGNMENT
    alloc_opt, flow_value, feasible, diag = assign_constituency_seats_optimal(
        const_df=const_df, party_seats=party_seats, party_votes_by_const=votes_by_const
    )
    opt_tbl = alloc_opt.assign(TOTAL=alloc_opt.sum(axis=1))
    opt_tbl.loc["SUM"] = opt_tbl.sum(axis=0, numeric_only=True)
    print("\n=== OPTIMAL (MAX-FLOW) ASSIGNMENT (Party x Constituency) ===")
    print(opt_tbl.to_string())

    print("\nMax-flow seats placed:", flow_value, "out of", int(sum(const_df["Seats"])))
    print("Feasible (no forced placements)?", feasible)
    print("\nParty vote-backed capacities vs national seats:")
    for p, cap_sum in diag["party_capacities"].items():
        print(f"  {p}: {cap_sum} (national: {party_seats[p]})")
    print("\nConstituency vote-backed capacity sums:")
    seats_map = dict(zip(const_df["Constituency"], const_df["Seats"]))
    for c, cap_sum in diag["constituency_capacities"].items():
        need = int(seats_map[c])
        print(f"  {c}: {cap_sum} (needs {need})")

    # nat_df must have Cap column (ceil(quota)); if not, recompute it
    # Example: cap_map = nat_df.set_index("Party")["Cap"].astype(int).to_dict()
    cap_map = nat_df.set_index("Party")["Cap"].astype(int).to_dict()

    # alloc_opt is the Party x Constituency from max-flow (may place < 63 seats)
    from assignment_fractional import assign_fractional_fill

    alloc_ff, ff_logs, leftover_const, leftover_party = assign_fractional_fill(
        const_df=const_df,
        votes_by_const=votes_by_const,
        alloc_df_start=alloc_opt,   # start from max-flow placement
        party_caps=cap_map,            # do not exceed ceil(quota) per party
    )

    ff_tbl = alloc_ff.assign(TOTAL=alloc_ff.sum(axis=1))
    ff_tbl.loc["SUM"] = ff_tbl.sum(axis=0, numeric_only=True)
    print("\n=== FRACTIONAL FILL (Party x Constituency) ===")
    print(ff_tbl.to_string())

    if leftover_const:
        print("\n[WARN] Unfilled constituency seats after fractional fill:", leftover_const)
    if leftover_party:
        print("[NOTE] Parties still below caps after fill:", leftover_party)
    for ln in ff_logs[:10]:
        print("  " + ln)
    print(f"... ({len(ff_logs)} steps)")

if __name__ == "__main__":
    main()
