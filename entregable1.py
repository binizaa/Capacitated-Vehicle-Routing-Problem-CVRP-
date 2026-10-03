import pulp as plp
import math
import itertools
import time
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
A = list(itertools.permutations(N, 2))      # arcs

# (1) Euclidean distance rounded to nearest integer
d = {(i, j): math.floor(math.dist(coords[i], coords[j]) + 0.5) for (i, j) in A}

# Minimum number of vehicles
K_min = math.ceil(sum(q[i] for i in C) / Q)

# (2), (11) Binary routing variables
x = plp.LpVariable.dicts("x", A, cat="Binary")
# (3) Accumulated load when leaving customer i
u = plp.LpVariable.dicts("u", C, lowBound=0, upBound=Q)

# 3. Objective function
# (4) Minimize total distance
model += plp.lpSum(d[a] * x[a] for a in A), "Objective_Function"

# 4. Constraints
# (5), (6) Each customer has exactly one predecessor and one successor
for j in C:
    model += plp.lpSum(x[i, j] for i in N if i != j) == 1, f"In_{j}"
    model += plp.lpSum(x[j, i] for i in N if i != j) == 1, f"Out_{j}"

# (6) Depot: as many vehicles leave as return
model += (plp.lpSum(x[1, j] for j in C) == plp.lpSum(x[j, 1] for j in C)), "Depot_Flow"

# (7) At least K_min vehicles leave the depot
model += plp.lpSum(x[1, j] for j in C) >= K_min, "Min_Vehicles"

# (8), (9) Lifted MTZ (Desrochers-Laporte)
for i in C:
    for j in C:
        if i != j:
            model += (u[j] >= u[i] + q[j] - Q * (1 - x[i, j])
                      + (Q - q[i] - q[j]) * x[j, i]), f"MTZ_{i}_{j}"

# (10) Bounds on accumulated load
for i in C:
    model += u[i] >= q[i], f"u_min_{i}"

# 5. Solve
start = time.time()
model.solve(plp.PULP_CBC_CMD(msg=False))
elapsed = time.time() - start

# 6. Results
print(f"Status: {plp.LpStatus[model.status]}")
print(f"Minimum distance Z = {plp.value(model.objective)}")
print(f"Solve time: {elapsed:.2f} s")

succ = {i: j for (i, j) in A if i != 1 and x[i, j].varValue > 0.5}
starts = [j for j in C if x[1, j].varValue > 0.5]

routes = {}
for k, first in enumerate(starts, 1):
    route, node = [1, first], first
    while succ[node] != 1:
        node = succ[node]
        route.append(node)
    route.append(1)
    routes[k] = route
    load = sum(q[i] for i in route if i != 1)
    dist = sum(d[route[t], route[t + 1]] for t in range(len(route) - 1))
    print(f"Vehicle {k}: {' -> '.join(map(str, route))}  (load {load}/{Q}, distance {dist})")


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