"""Reusable version of the CVRP formulation in entregable1.py (eqs. 1-11),
shared by sensitivity.py and shadow_prices.py."""
import itertools
import math
import time
from pathlib import Path

import pulp as plp


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


def distances(coords):
    return {(i, j): math.floor(math.dist(coords[i], coords[j]) + 0.5)
            for (i, j) in itertools.permutations(coords, 2)}


def solve_cvrp(coords, q, Q, K_exact=None, K_min=None, relax=False, force_edge=None,
               edge_uses=None, time_limit=120):
    """Solve the CVRP. K_exact turns constraint (7) into an equality, K_min
    overrides its right-hand side, force_edge=(i, j) forces the undirected
    edge i-j into the solution, edge_uses=((i, j), n) makes it be traversed
    exactly n times and relax=True makes x continuous in [0, 1]
    (LP relaxation, whose duals and reduced costs are also returned)."""
    N = sorted(coords)
    C = [i for i in N if i != 1]
    A = list(itertools.permutations(N, 2))
    d = distances(coords)

    if max(q[i] for i in C) > Q:
        return {"status": "Infeasible", "Z": None, "routes": [], "time": 0.0}

    if K_min is None:
        K_min = math.ceil(sum(q[i] for i in C) / Q)
    model = plp.LpProblem("CVRP", plp.LpMinimize)
    x = plp.LpVariable.dicts("x", A, lowBound=0, upBound=1,
                             cat="Continuous" if relax else "Binary")
    u = plp.LpVariable.dicts("u", C, lowBound=0, upBound=Q)

    model += plp.lpSum(d[a] * x[a] for a in A)
    for j in C:
        model += plp.lpSum(x[i, j] for i in N if i != j) == 1, f"In_{j}"
        model += plp.lpSum(x[j, i] for i in N if i != j) == 1, f"Out_{j}"
    model += (plp.lpSum(x[1, j] for j in C) == plp.lpSum(x[j, 1] for j in C)), "Depot_Flow"
    if K_exact is None:
        model += plp.lpSum(x[1, j] for j in C) >= K_min, "Min_Vehicles"
    else:
        model += plp.lpSum(x[1, j] for j in C) == K_exact, "Min_Vehicles"
    for i in C:
        for j in C:
            if i != j:
                model += (u[j] >= u[i] + q[j] - Q * (1 - x[i, j])
                          + (Q - q[i] - q[j]) * x[j, i]), f"MTZ_{i}_{j}"
    for i in C:
        model += u[i] >= q[i], f"u_min_{i}"
    if force_edge is not None:
        i, j = force_edge
        model += x[i, j] + x[j, i] >= 1, "Force_Edge"
    if edge_uses is not None:
        (i, j), n = edge_uses
        model += x[i, j] + x[j, i] == n, "Edge_Uses"

    start = time.time()
    model.solve(plp.PULP_CBC_CMD(msg=False, timeLimit=time_limit))
    elapsed = time.time() - start
    status = plp.LpStatus[model.status]
    if status != "Optimal":
        return {"status": status, "Z": None, "routes": [], "time": elapsed}

    if relax:
        return {"status": status, "Z": plp.value(model.objective), "routes": [],
                "time": elapsed, "x": {a: x[a].varValue for a in A},
                "duals": {name: c.pi for name, c in model.constraints.items()},
                "slacks": {name: c.slack for name, c in model.constraints.items()},
                "reduced_costs": {a: x[a].dj for a in A}}

    succ = {i: j for (i, j) in A if i != 1 and x[i, j].varValue > 0.5}
    routes = []
    for first in (j for j in C if x[1, j].varValue > 0.5):
        route, node = [1, first], first
        while succ[node] != 1:
            node = succ[node]
            route.append(node)
        routes.append(route + [1])
    return {"status": status, "Z": round(plp.value(model.objective)),
            "routes": routes, "time": elapsed}
