"""Parametric sensitivity analysis of the CVRP model in entregable1.py.

Since the model is a MILP, LP duals (shadow prices, reduced costs) are not
meaningful for the integer optimum. Instead, every experiment re-solves the
model while varying one parameter and records Z* and the route structure.
"""
import csv
import math
import random
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cvrp_model import distances, read_cvrp, solve_cvrp

ROOT = Path(__file__).parent
IMG_DIR = ROOT / "img"
OUT_DIR = ROOT / "results"
IMG_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)


def route_cost(routes, d):
    return sum(d[r[t], r[t + 1]] for r in routes for t in range(len(r) - 1))


def edge_set(routes):
    """Undirected edges: a route and its reverse are the same solution."""
    return {frozenset((r[t], r[t + 1])) for r in routes for t in range(len(r) - 1)}


def fmt_routes(routes):
    return " | ".join("-".join(map(str, r[1:-1])) for r in routes)


def write_csv(name, rows):
    with open(OUT_DIR / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


coords, q, Q = read_cvrp(ROOT / "NAME _CVRP_10_manual.txt")
C = [i for i in sorted(coords) if i != 1]
d0 = distances(coords)
total_q = sum(q[i] for i in C)

base = solve_cvrp(coords, q, Q)
Z0 = base["Z"]
print(f"Base: Z* = {Z0}, K = {len(base['routes'])}, routes = {fmt_routes(base['routes'])}")


# E1. Vehicle capacity Q
print("\n[E1] Capacity Q")
rows_Q = []
for Qv in [20, 25, 30, 35, 40, 45, 50, 55, 60, 70, 80, 90, 100, 120, 146, 160]:
    r = solve_cvrp(coords, q, Qv)
    rows_Q.append({"Q": Qv, "K_min": math.ceil(total_q / Qv), "K_used": len(r["routes"]),
                   "Z": r["Z"], "routes": fmt_routes(r["routes"])})
    print(f"  Q={Qv:>3}  K_min={rows_Q[-1]['K_min']:>2}  K={len(r['routes']):>2}  Z*={r['Z']}")
write_csv("sens_capacity.csv", rows_Q)


# E2. Uniform demand scaling q_i -> round(alpha * q_i)
print("\n[E2] Demand scaling")
rows_a = []
for alpha in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]:
    qa = {i: round(alpha * q[i]) for i in q}
    r = solve_cvrp(coords, qa, Q)
    rows_a.append({"alpha": alpha, "total_demand": sum(qa.values()),
                   "K_min": math.ceil(sum(qa.values()) / Q), "K_used": len(r["routes"]),
                   "Z": r["Z"], "routes": fmt_routes(r["routes"])})
    print(f"  alpha={alpha:.1f}  demand={rows_a[-1]['total_demand']:>3}  "
          f"K={len(r['routes']):>2}  Z*={r['Z']}")
write_csv("sens_demand_scale.csv", rows_a)


# E3. Fixed fleet size K (constraint (7) as equality)
print("\n[E3] Fixed fleet size K")
rows_K = []
for K in range(1, len(C) + 1):
    r = solve_cvrp(coords, q, Q, K_exact=K)
    rows_K.append({"K": K, "status": r["status"], "Z": r["Z"],
                   "delta_vs_base": None if r["Z"] is None else r["Z"] - Z0,
                   "routes": fmt_routes(r["routes"])})
    print(f"  K={K:>2}  {r['status']:<10} Z*={r['Z']}")
write_csv("sens_fleet.csv", rows_K)

# Fixed cost f per vehicle: objective becomes Z(K) + f*K. The base fleet stays
# optimal while f is below the smallest saving obtained by removing vehicles.
feasible_K = {row["K"]: row["Z"] for row in rows_K if row["Z"] is not None}
K0 = len(base["routes"])
f_break = min(((feasible_K[k] - Z0) / (K0 - k) for k in feasible_K if k < K0),
              default=None)
print(f"  With a fixed cost f per vehicle, K={K0} stays optimal while f <= {f_break}")


# E4. Individual customer demand: q_i -> q_i + delta
print("\n[E4] Individual demand increase")
route_of = {i: r for r in base["routes"] for i in r[1:-1]}
slack = {i: Q - sum(q[j] for j in route_of[i][1:-1]) for i in C}
rows_i = []
for i in C:
    row = {"customer": i, "q": q[i], "route_slack": slack[i]}
    # Z*(delta) is non-decreasing in delta and equals Z0 while delta <= slack.
    for delta in sorted({slack[i] + 1, 5, 10, 15, 20}):
        if q[i] + delta > Q:
            row[f"Z_+{delta}"] = None
            continue
        if delta <= slack[i]:
            row[f"Z_+{delta}"] = Z0
            continue
        r = solve_cvrp(coords, {**q, i: q[i] + delta}, Q)
        row[f"Z_+{delta}"] = r["Z"]
    rows_i.append(row)
    print(f"  customer {i:>2}  q={q[i]:>2}  slack={slack[i]:>2}  Z*(q+slack+1)={row[f'Z_+{slack[i] + 1}']}")
# Rows have different keys; normalise to a fixed set of columns
cols = ["customer", "q", "route_slack", "Z_at_slack+1", "Z_+5", "Z_+10", "Z_+15", "Z_+20"]
write_csv("sens_customer_demand.csv", [
    {c: (row.get(f"Z_+{row['route_slack'] + 1}") if c == "Z_at_slack+1" else row.get(c))
     for c in cols} for row in rows_i])


# E5. Robustness to coordinate noise (Monte Carlo)
print("\n[E5] Coordinate perturbation (Monte Carlo)")
rng = random.Random(42)
E0 = edge_set(base["routes"])
rows_mc = []
for sigma in [1, 2, 3, 5, 8]:
    for rep in range(20):
        cp = {i: (a + rng.gauss(0, sigma), b + rng.gauss(0, sigma)) if i != 1 else (a, b)
              for i, (a, b) in coords.items()}
        dp = distances(cp)
        r = solve_cvrp(cp, q, Q)
        base_cost = route_cost(base["routes"], dp)  # keep base plan, new distances
        rows_mc.append({"sigma": sigma, "rep": rep, "Z_reopt": r["Z"], "Z_base_plan": base_cost,
                        "regret_pct": 100 * (base_cost - r["Z"]) / r["Z"],
                        "same_solution": edge_set(r["routes"]) == E0,
                        "K": len(r["routes"])})
    s = [m for m in rows_mc if m["sigma"] == sigma]
    print(f"  sigma={sigma}  same solution {sum(m['same_solution'] for m in s):>2}/20  "
          f"mean regret {sum(m['regret_pct'] for m in s) / 20:.2f}%  "
          f"max regret {max(m['regret_pct'] for m in s):.2f}%")
write_csv("sens_coordinates_mc.csv", rows_mc)


# Plots
fig, axes = plt.subplots(2, 2, figsize=(12, 9))

ax = axes[0, 0]
pts = [(r["Q"], r["Z"], r["K_used"]) for r in rows_Q if r["Z"] is not None]
ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", color="tab:blue")
for Qv, Z, K in pts:
    ax.annotate(f"K={K}", (Qv, Z), textcoords="offset points", xytext=(4, 6), fontsize=8)
ax.axvline(Q, ls="--", color="gray", lw=1)
ax.set(title="E1. Capacity Q", xlabel="Q", ylabel="Z*")

ax = axes[0, 1]
pts = [(r["alpha"], r["Z"], r["K_used"]) for r in rows_a if r["Z"] is not None]
ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", color="tab:orange")
for a, Z, K in pts:
    ax.annotate(f"K={K}", (a, Z), textcoords="offset points", xytext=(4, 6), fontsize=8)
ax.axvline(1.0, ls="--", color="gray", lw=1)
ax.set(title="E2. Demand scaling", xlabel="alpha (q_i -> alpha q_i)", ylabel="Z*")

ax = axes[1, 0]
ks = sorted(feasible_K)
ax.bar(ks, [feasible_K[k] for k in ks],
       color=["tab:green" if k == K0 else "lightgray" for k in ks], edgecolor="black")
for k in ks:
    ax.annotate(str(feasible_K[k]), (k, feasible_K[k]), ha="center",
                textcoords="offset points", xytext=(0, 3), fontsize=8)
ax.set(title="E3. Fixed fleet size K", xlabel="K", ylabel="Z*", xticks=ks)

ax = axes[1, 1]
sigmas = sorted({m["sigma"] for m in rows_mc})
ax.boxplot([[m["regret_pct"] for m in rows_mc if m["sigma"] == s] for s in sigmas],
           tick_labels=[str(s) for s in sigmas])
ax.set(title="E5. Regret of keeping the base plan", xlabel="coordinate noise sigma",
       ylabel="(Z_base_plan - Z_reopt) / Z_reopt  [%]")

fig.tight_layout()
fig.savefig(IMG_DIR / "sensitivity.png", dpi=200, bbox_inches="tight")
plt.close(fig)
print(f"\nCSV files saved to {OUT_DIR}, plot saved to {IMG_DIR / 'sensitivity.png'}")
