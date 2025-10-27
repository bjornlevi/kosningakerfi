# assignment_greedy.py
from typing import Dict, Tuple, List
import pandas as pd

def assign_constituency_seats_greedy(
    const_df: pd.DataFrame,
    party_seats: Dict[str, int],
    party_votes_by_const: Dict[str, Dict[str, int]],
) -> Tuple[pd.DataFrame, List[str], Dict[str, int], Dict[str, int]]:
    """
    Greedy placement (your original iterative rule):
      - Repeatedly assign the next seat to the (party, constituency) cell with max current votes,
        among parties with seats left and constituencies with seats left.
      - Deduct Voters_per_MP from that cell's votes.
      - If top cell has zero votes (or party has no votes where seats remain), force-place in the
        constituency with most seats left (note logged as 'forced placement').
    Returns:
      - alloc_df (Party x Constituency)
      - action_logs (list)
      - leftover_const (constituencies with seats unfilled; should be empty)
      - leftover_party (parties with seats unassigned; should be empty)
    """
    c_remain = {row.Constituency: int(row.Seats) for _, row in const_df.iterrows()}
    vpmp = {row.Constituency: float(row.Voters_per_MP) for _, row in const_df.iterrows()}
    votes = {p: {c: int(party_votes_by_const.get(p, {}).get(c, 0)) for c in c_remain}
             for p in party_seats}
    p_remain = {p: int(s) for p, s in party_seats.items()}
    alloc = {p: {c: 0 for c in c_remain} for p in party_seats}
    logs: List[str] = []

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

        # Max cell votes; tie-break by party total votes, then party/const name for determinism
        candidates.sort(key=lambda x: (x[0], sum(votes[x[1]].values()), x[1], x[2]), reverse=True)
        top_votes, party, const = candidates[0]

        moved_note = None
        if top_votes == 0:
            # Party has no positive votes where seats remain -> forced placement
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
