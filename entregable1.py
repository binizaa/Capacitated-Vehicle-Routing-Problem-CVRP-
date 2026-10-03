import pulp as plp
import math
import itertools
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

IMG_DIR = Path(__file__).parent / "img"
IMG_DIR.mkdir(exist_ok=True)


# 0. Read the instance
def read_cvrp(path):
    coords, q, Q = {}, {}, None
    section = None
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line == "EOF":
            continue
        if line.startswith("CAPACITY"):
            Q = int(line.split(":")[1])
        elif line.endswith("_SECTION"):
            section = line
        elif section == "NODE_COORD_SECTION":
            i, a, b = line.split()
            coords[int(i)] = (float(a), float(b))
        elif section == "DEMAND_SECTION":
            i, dem = line.split()
            q[int(i)] = int(dem)
    return coords, q, Q


coords, q, Q = read_cvrp(Path(__file__).parent / "NAME _CVRP_10_manual.txt")

# 1. Create the minimization problem
model = plp.LpProblem("CVRP_10", plp.LpMinimize)

# 2. Parameters and variables
N = sorted(coords)                          # nodes (1 = depot)
C = [i for i in N if i != 1]                # customers
K = [1, 2, 3]                               # vehicles
A = list(itertools.permutations(N, 2))      # edges

# Euclidean distance (eq. 1)
d = {(i, j): math.floor(math.dist(coords[i], coords[j]) + 0.5) for (i, j) in A}

x = plp.LpVariable.dicts("x", [(i, j, k) for (i, j) in A for k in K], cat="Binary")
u = plp.LpVariable.dicts("u", C, lowBound=0, upBound=Q)

# 3. Objective function (eq. 4)
model += plp.lpSum(d[i, j] * x[i, j, k] for k in K for (i, j) in A), "Objective_Function"

# 4. Constraints
# (5) Each customer has exactly one predecessor
for j in C:
    model += plp.lpSum(x[i, j, k] for k in K for i in N if i != j) == 1, f"Pred_{j}"

# (6) Flow conservation: what enters h must leave h
for h in N:
    for k in K:
        model += (plp.lpSum(x[i, h, k] for i in N if i != h)
                  - plp.lpSum(x[h, j, k] for j in N if j != h) == 0), f"Flow_{h}_{k}"

# (7) Each vehicle leaves the depot at most once
for k in K:
    model += plp.lpSum(x[1, j, k] for j in C) <= 1, f"Departure_{k}"

# (8) Capacity per vehicle
for k in K:
    model += plp.lpSum(q[j] * x[i, j, k] for i in N for j in C if i != j) <= Q, f"Cap_{k}"

# (9) MTZ: subtour elimination
for i in C:
    for j in C:
        if i != j:
            model += (u[j] >= u[i] + q[j] - Q * (1 - plp.lpSum(x[i, j, k] for k in K))), f"MTZ_{i}_{j}"

# (10) Bounds on accumulated load
for i in C:
    model += u[i] >= q[i], f"u_min_{i}"

# 5. Solve
model.solve(plp.PULP_CBC_CMD(msg=False))

# 6. Results
print(f"Status: {plp.LpStatus[model.status]}")
print(f"Minimum distance Z = {plp.value(model.objective)}")
routes = {}
for k in K:
    nxt = {i: j for (i, j) in A if x[i, j, k].varValue > 0.5}
    if 1 not in nxt:
        print(f"Vehicle {k}: unused")
        continue
    route, node = [1], nxt[1]
    while node != 1:
        route.append(node)
        node = nxt[node]
    route.append(1)
    routes[k] = route
    load = sum(q[i] for i in route)
    print(f"Vehicle {k}: {' -> '.join(map(str, route))}  (load {load}/{Q})")


# 7. Plots
def draw_nodes(ax):
    for i, (a, b) in coords.items():
        is_depot = i == 1
        ax.scatter(a, b, s=180 if is_depot else 80, marker="s" if is_depot else "o",
                   color="black" if is_depot else "white", edgecolors="black", zorder=3)
        ax.annotate(str(i), (a, b), textcoords="offset points", xytext=(6, 6))
    ax.set_xlabel("a")
    ax.set_ylabel("b")
    ax.grid(alpha=0.3)


# Nodes only
fig, ax = plt.subplots(figsize=(7, 6))
draw_nodes(ax)
ax.set_title("Nodes (square = depot)")
fig.savefig(IMG_DIR / "nodes.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# Final routes
fig, ax = plt.subplots(figsize=(7, 6))
colors = plt.cm.tab10.colors
for idx, (k, route) in enumerate(routes.items()):
    xs = [coords[i][0] for i in route]
    ys = [coords[i][1] for i in route]
    ax.plot(xs, ys, "-", color=colors[idx % 10], lw=2, label=f"Vehicle {k}", zorder=2)
draw_nodes(ax)
ax.set_title(f"Optimal routes (Z = {plp.value(model.objective):.0f})")
ax.legend()
fig.savefig(IMG_DIR / "routes.png", dpi=200, bbox_inches="tight")
plt.close(fig)

print(f"Plots saved to {IMG_DIR}")
