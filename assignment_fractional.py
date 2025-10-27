# assignment_fractional.py
from typing import Dict, Tuple, List
import pandas as pd
import math

def assign_fractional_fill(
    const_df: pd.DataFrame,
    votes_by_const: Dict[str, Dict[str, int]],
    # starting allocation, e.g. from max-flow (Party x Constituency, ints)
    alloc_df_start: pd.DataFrame,
    # national caps per party = ceil(quota)
    party_caps: Dict[str, int],
) -> Tuple[pd.DataFrame, List[str], Dict[str, int], Dict[str, int]]:
    """
    Incrementally 'promote' fractional seats by largest remainder until
    all constituency seats are filled or no eligible candidates remain.

    Constraints enforced:
      - Per-constituency seat totals (c_remain)
      - Per-party national cap (ceil(quota))
      - Per-cell cap: seats_{p,c} <= ceil(votes_{p,c}/VPMP_c)

    Inputs:
      const_df: columns ["Constituency","Voters","Seats","Voters_per_MP"]
      votes_by_const: dict party -> dict constituency -> votes (ints)
      alloc_df_start: DataFrame Party x Constituency with current seats (ints)
      party_caps: dict party -> cap (ceil(quota))
    Returns:
      alloc_df: updated allocation (Party x Constituency)
      logs:    list of textual steps taken
      leftover_const: dict constituency -> seats unfilled (0 if full)
      leftover_party: dict party -> seats still available under cap (0 if at cap)
    """
    # Working copies
    alloc = alloc_df_start.copy().astype(int)
    parties = list(alloc.index)
    consts = list(const_df["Constituency"])

    # Constituency remaining seats
    c_seats = dict(zip(const_df["Constituency"], const_df["Seats"]))
    c_used = {c: int(alloc[c].sum()) for c in consts}
    c_remain = {c: int(c_seats[c] - c_used[c]) for c in consts}

    # Per-party remaining under national cap
    p_used = {p: int(alloc.loc[p].sum()) for p in parties}
    p_cap = {p: int(party_caps.get(p, 0)) for p in parties}
    p_remain = {p: int(max(0, p_cap[p] - p_used[p])) for p in parties}

    # Precompute VPMP and per-cell quotients and cell caps
    vpmp = {row.Constituency: float(row.Voters_per_MP) for _, row in const_df.iterrows()}
    q = {p: {c: (votes_by_const.get(p, {}).get(c, 0) / vpmp[c]) if vpmp[c] > 0 else 0.0 for c in consts}
         for p in parties}
    ucap = {p: {c: int(math.ceil(q[p][c])) for c in consts} for p in parties}

    logs: List[str] = []

    total_to_fill = sum(c_remain.values())
    filled = 0

    while filled < total_to_fill:
        # Build candidate list: (remainder_for_next_seat, votes, party, const)
        candidates = []
        for p in parties:
            if p_remain.get(p, 0) <= 0:
                continue
            for c in consts:
                if c_remain.get(c, 0) <= 0:
                    continue
                s_now = int(alloc.at[p, c])
                # cell cap: can't exceed ceil(q)
                if s_now >= ucap[p][c]:
                    continue
                # remainder for next seat at this cell
                r_next = q[p][c] - s_now
                # only consider positive remainder
                if r_next <= 0:
                    continue
                candidates.append( (r_next, votes_by_const.get(p, {}).get(c, 0), p, c) )

        if not candidates:
            # No eligible fractional seats left under constraints
            break

        # Pick the largest remainder; tiebreak by higher votes, then party, then constituency
        candidates.sort(key=lambda t: (t[0], t[1], t[2], t[3]), reverse=True)
        r_next, votes_cell, party, const = candidates[0]

        # Assign one seat
        alloc.at[party, const] += 1
        p_remain[party] -= 1
        c_remain[const] -= 1
        filled += 1

        logs.append(
            f"{party} +1 in {const} by fractional fill "
            f"(next-remainder={r_next:.3f}, now {alloc.at[party,const]} / ceil(q)={ucap[party][const]}, "
            f"party used {p_cap[party]-p_remain[party]}/{p_cap[party]}, const left {c_remain[const]})"
        )

    leftover_const = {c: s for c, s in c_remain.items() if s != 0}
    leftover_party = {p: r for p, r in p_remain.items() if r != 0}
    return alloc, logs, leftover_const, leftover_party
