# assignment_maxflow.py
from typing import Dict, Tuple, List
from collections import deque
import pandas as pd
import math

def _build_flow_network(const_df, party_seats, party_votes_by_const):
    vpmp = {row.Constituency: float(row.Voters_per_MP) for _, row in const_df.iterrows()}
    const_caps = {row.Constituency: int(row.Seats) for _, row in const_df.iterrows()}
    const_order = list(const_caps.keys())
    parties = list(party_seats.keys())

    S = "_SRC_"; T = "_SNK_"
    def P(p): return f"P::{p}"
    def C(c): return f"C::{c}"

    graph = {}; cap = {}

    def add_edge(u, v, w):
        graph.setdefault(u, []).append(v)
        graph.setdefault(v, []).append(u)
        cap[(u, v)] = cap.get((u, v), 0) + int(w)
        cap.setdefault((v, u), 0)

    # Source -> party (national seats)
    for p in parties:
        add_edge(S, P(p), int(party_seats[p]))

    # Party -> constituency (vote-backed max seats)
    for p in parties:
        for c in const_order:
            votes_pc = int(party_votes_by_const.get(p, {}).get(c, 0))
            max_pc = int(math.floor(votes_pc / vpmp[c])) if vpmp[c] > 0 else 0
            if max_pc > 0:
                add_edge(P(p), C(c), max_pc)

    # Constituency -> Sink (const seats)
    for c in const_order:
        add_edge(C(c), T, int(const_caps[c]))

    meta = {"S": S, "T": T, "parties": parties, "const_order": const_order}
    return graph, cap, meta

def _edmonds_karp(graph, cap, S, T):
    flow = {e: 0 for e in cap.keys()}

    def bfs():
        parent = {S: None}; avail = {S: float("inf")}
        q = deque([S])
        while q:
            u = q.popleft()
            for v in graph[u]:
                resid = cap[(u, v)] - flow[(u, v)]
                if resid > 0 and v not in parent:
                    parent[v] = u; avail[v] = min(avail[u], resid)
                    if v == T:
                        return parent, avail[v]
                    q.append(v)
        return None, 0

    maxflow = 0
    while True:
        parent, aug = bfs()
        if aug == 0:
            break
        maxflow += aug
        v = T
        while v != S:
            u = parent[v]
            flow[(u, v)] += aug
            flow[(v, u)] -= aug
            v = u
    return maxflow, flow

def assign_constituency_seats_optimal(
    const_df: pd.DataFrame,
    party_seats: Dict[str, int],
    party_votes_by_const: Dict[str, Dict[str, int]],
) -> Tuple[pd.DataFrame, int, bool, Dict]:
    """
    Max-flow placement (no forced placements):
      sum_c x_{p,c} = national_seats_p
      sum_p x_{p,c} = const_seats_c
      x_{p,c} <= floor(votes_{p,c} / vpmp_c)
    """
    graph, cap, meta = _build_flow_network(const_df, party_seats, party_votes_by_const)
    S, T = meta["S"], meta["T"]
    parties, const_order = meta["parties"], meta["const_order"]

    total_seats = int(sum(const_df["Seats"]))
    if total_seats != int(sum(party_seats.values())):
        raise ValueError("National seat total != sum of constituency seats.")

    maxflow, flow = _edmonds_karp(graph, cap, S, T)

    # Extract x_{p,c}
    alloc = {p: {c: 0 for c in const_order} for p in parties}
    for p in parties:
        u = f"P::{p}"
        for c in const_order:
            v = f"C::{c}"
            if (u, v) in flow:
                alloc[p][c] = int(flow[(u, v)])

    alloc_df = pd.DataFrame(alloc).T[const_order]
    vpmp = {row.Constituency: float(row.Voters_per_MP) for _, row in const_df.iterrows()}
    cap_pc = {p: {c: int(math.floor(int(party_votes_by_const.get(p, {}).get(c, 0)) / vpmp[c])) if vpmp[c] > 0 else 0
                  for c in const_order} for p in parties}

    diagnostics = {
        "maxflow": maxflow,
        "total_seats": total_seats,
        "party_capacities": {p: sum(cap_pc[p].values()) for p in parties},
        "constituency_capacities": {c: sum(cap_pc[p][c] for p in parties) for c in const_order},
        "edge_capacities": cap_pc,
    }
    feasible = (maxflow == total_seats)
    return alloc_df, maxflow, feasible, diagnostics
