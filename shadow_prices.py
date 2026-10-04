"""Shadow prices of the CVRP model.

Two versions are compared for each constraint group:
  * LP duals of the linear relaxation (x continuous in [0, 1]).
  * Integer shadow prices: the change in the MILP optimum Z* when the
    right-hand side is perturbed and the model is re-solved.
"""
import csv
from pathlib import Path

from cvrp_model import read_cvrp, solve_cvrp

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "results"
OUT_DIR.mkdir(exist_ok=True)

coords, q, Q = read_cvrp(ROOT / "NAME _CVRP_10_manual.txt")
C = [i for i in sorted(coords) if i != 1]

ip = solve_cvrp(coords, q, Q)
lp = solve_cvrp(coords, q, Q, relax=True)
Z0, Z_lp = ip["Z"], lp["Z"]
duals, slacks = lp["duals"], lp["slacks"]
print(f"MILP Z* = {Z0}   LP relaxation Z_LP = {Z_lp:.2f}   "
      f"integrality gap = {100 * (Z0 - Z_lp) / Z0:.1f}%")

rows = []

# Customer visit constraints (5): In_j = 1 and Out_j = 1.
# Integer analogue of RHS 1 -> 0: remove customer j and re-solve.
print("\nCustomer constraints In_j / Out_j")
print(f"  {'j':>3} {'pi_In':>7} {'pi_Out':>7} {'LP sum':>7} {'IP: Z*-Z*(-j)':>14}")
for j in C:
    r = solve_cvrp({i: c for i, c in coords.items() if i != j},
                   {i: v for i, v in q.items() if i != j}, Q)
    lp_sum = duals[f"In_{j}"] + duals[f"Out_{j}"]
    rows.append({"constraint": f"In_{j} + Out_{j}", "lp_dual": round(lp_sum, 3),
                 "ip_shadow_price": Z0 - r["Z"], "meaning": f"cost of serving customer {j}"})
    print(f"  {j:>3} {duals[f'In_{j}']:>7.2f} {duals[f'Out_{j}']:>7.2f} {lp_sum:>7.2f} {Z0 - r['Z']:>14}")

# Fleet constraint (7): sum_j x_1j >= K_min.
print("\nFleet constraint Min_Vehicles (RHS K_min = 3)")
print(f"  LP dual = {duals['Min_Vehicles']:.3f}   LP slack = {slacks['Min_Vehicles']:.3f}")
Zk = {k: solve_cvrp(coords, q, Q, K_min=k)["Z"] for k in (4, 5)}
print(f"  IP: K_min 3->4: dZ = {Zk[4] - Z0}   K_min 4->5: dZ = {Zk[5] - Zk[4]}")
rows.append({"constraint": "Min_Vehicles", "lp_dual": round(duals["Min_Vehicles"], 3),
             "ip_shadow_price": Zk[4] - Z0, "meaning": "cost of one more required vehicle"})
print(f"  Depot_Flow LP dual = {duals['Depot_Flow']:.3f}")

# Capacity Q (appears in MTZ (8)-(9) and the bound (3)).
print("\nCapacity Q")
ZQ = {Qv: solve_cvrp(coords, q, Qv)["Z"] for Qv in (49, 51)}
ZQ_lp = {Qv: solve_cvrp(coords, q, Qv, relax=True)["Z"] for Qv in (49, 51)}
print(f"  LP: dZ/dQ ~ {(ZQ_lp[51] - ZQ_lp[49]) / 2:.3f}")
print(f"  IP: Z*(49) = {ZQ[49]}, Z*(50) = {Z0}, Z*(51) = {ZQ[51]}")
rows.append({"constraint": "Capacity Q", "lp_dual": round((ZQ_lp[51] - ZQ_lp[49]) / 2, 3),
             "ip_shadow_price": f"{ZQ[51] - Z0} (+1) / {Z0 - ZQ[49]} (-1)",
             "meaning": "value of one more unit of capacity"})

# Lower bounds (10): u_i >= q_i, i.e. demand of customer i.
print("\nDemand constraints u_min_i (RHS q_i)")
print(f"  {'i':>3} {'LP dual':>8} {'IP +1':>6} {'IP -1':>6}")
for i in C:
    up = solve_cvrp(coords, {**q, i: q[i] + 1}, Q)["Z"]
    down = solve_cvrp(coords, {**q, i: q[i] - 1}, Q)["Z"]
    rows.append({"constraint": f"u_min_{i}", "lp_dual": round(duals[f"u_min_{i}"], 3),
                 "ip_shadow_price": f"{up - Z0} (+1) / {Z0 - down} (-1)",
                 "meaning": f"cost of one more unit of demand at {i}"})
    print(f"  {i:>3} {duals[f'u_min_{i}']:>8.3f} {up - Z0:>6} {Z0 - down:>6}")

active_mtz = {k: v for k, v in duals.items() if k.startswith("MTZ") and abs(v) > 1e-6}
print(f"\nMTZ constraints with non-zero LP dual: {len(active_mtz)} of "
      f"{sum(k.startswith('MTZ') for k in duals)}")
for k, v in sorted(active_mtz.items(), key=lambda kv: -abs(kv[1]))[:10]:
    print(f"  {k:<10} {v:.3f}")

with open(OUT_DIR / "shadow_prices.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
print(f"\nSaved to {OUT_DIR / 'shadow_prices.csv'}")
