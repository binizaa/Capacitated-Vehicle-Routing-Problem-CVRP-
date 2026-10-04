"""Reduced costs and optimality ranges of the CVRP model.

  * Reduced costs: LP relaxation (x.dj) vs the integer reduced cost of an
    unused edge, Z*(edge forced) - Z*.
  * Cost ranges: how much d_ij of a used edge can grow before the base
    solution stops being optimal: min over n < uses of
    (Z*(edge used n times) - Z*) / (uses - n).
  * RHS ranges: interval of Q and of each q_i where the base solution
    (Z* = 317) stays optimal.
"""
import csv
import itertools
from pathlib import Path

from cvrp_model import distances, read_cvrp, solve_cvrp

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "results"
OUT_DIR.mkdir(exist_ok=True)

coords, q, Q = read_cvrp(ROOT / "NAME _CVRP_10_manual.txt")
N = sorted(coords)
C = [i for i in N if i != 1]
d = distances(coords)

base = solve_cvrp(coords, q, Q)
Z0 = base["Z"]
lp = solve_cvrp(coords, q, Q, relax=True)
used = {}  # undirected edge -> times traversed in the base solution
for r in base["routes"]:
    for t in range(len(r) - 1):
        e = tuple(sorted((r[t], r[t + 1])))
        used[e] = used.get(e, 0) + 1
print(f"Base Z* = {Z0}, routes = {base['routes']}")


def write_csv(name, rows):
    with open(OUT_DIR / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


# Edges outside the solution: reduced costs
print("\nReduced costs of unused edges")
rows_rc = []
for e in itertools.combinations(N, 2):
    if e in used:
        continue
    i, j = e
    r = solve_cvrp(coords, q, Q, force_edge=e)
    rc_lp = min(lp["reduced_costs"][i, j], lp["reduced_costs"][j, i])
    rows_rc.append({"edge": f"{i}-{j}", "d": d[i, j], "lp_reduced_cost": round(rc_lp, 3),
                    "ip_reduced_cost": r["Z"] - Z0,
                    "d_lower_limit": d[i, j] - (r["Z"] - Z0)})
rows_rc.sort(key=lambda row: row["ip_reduced_cost"])
for row in rows_rc:
    print(f"  {row['edge']:>6}  d={row['d']:>3}  LP rc={row['lp_reduced_cost']:>7.2f}  "
          f"IP rc={row['ip_reduced_cost']:>4}")
write_csv("reduced_costs.csv", rows_rc)

# Edges in the solution: how much d_ij can increase
print("\nCost ranges of used edges")
rows_cr = []
for e, times in sorted(used.items()):
    Zn = {n: solve_cvrp(coords, q, Q, edge_uses=(e, n))["Z"] for n in range(times)}
    allowed = min((Zn[n] - Z0) / (times - n) for n in Zn)
    rows_cr.append({"edge": f"{e[0]}-{e[1]}", "d": d[e], "times_used": times,
                    "Z_forbidden": Zn[0], "max_increase": allowed,
                    "d_upper_limit": d[e] + allowed})
    print(f"  {e[0]:>2}-{e[1]:<2}  d={d[e]:>3}  used x{times}  Z*(forbidden)={Zn[0]}  "
          f"d can grow by {allowed:g}")
write_csv("cost_ranges.csv", rows_cr)

# RHS range of Q
print("\nRange of Q with Z* = 317")
ZQ = {Qv: solve_cvrp(coords, q, Qv)["Z"] for Qv in range(44, 56)}
Q_range = [Qv for Qv, Z in ZQ.items() if Z == Z0]
print("  " + "  ".join(f"Q={Qv}:{Z}" for Qv, Z in ZQ.items()))
print(f"  Z* = {Z0} for Q in [{min(Q_range)}, {max(Q_range)}]")
write_csv("range_capacity.csv", [{"Q": Qv, "Z": Z} for Qv, Z in ZQ.items()])

# RHS range of each q_i. Z*(q_i) is non-decreasing, so the upper limit is the
# route slack (verified by re-solving at slack + 1) and the lower limit is
# found by binary search.
print("\nRange of each q_i with Z* = 317")
route_of = {i: r for r in base["routes"] for i in r[1:-1]}
rows_q = []
for i in C:
    slack = Q - sum(q[j] for j in route_of[i][1:-1])
    upper = min(q[i] + slack, Q)
    above = solve_cvrp(coords, {**q, i: upper + 1}, Q)["Z"] if upper < Q else None
    lo, hi = 0, q[i]  # Z*(hi) == Z0; find smallest value keeping Z0
    while lo < hi:
        mid = (lo + hi) // 2
        if solve_cvrp(coords, {**q, i: mid}, Q)["Z"] == Z0:
            hi = mid
        else:
            lo = mid + 1
    below = solve_cvrp(coords, {**q, i: lo - 1}, Q)["Z"] if lo > 0 else None
    rows_q.append({"customer": i, "q": q[i], "lower": lo, "upper": upper,
                   "Z_below": below, "Z_above": above})
    print(f"  q_{i:<2}={q[i]:>2}  range [{lo}, {upper}]  Z* below={below}  Z* above={above}")
write_csv("range_demand.csv", rows_q)
