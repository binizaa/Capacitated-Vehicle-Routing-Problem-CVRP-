# CVRP_10 — Capacitated Vehicle Routing Problem (exact MILP)

Exact solution of a small, didactic CVRP instance (1 depot + 10 customers, 3 vehicles,
capacity 50) using a Mixed-Integer Linear Programming model solved with PuLP + CBC.

> 📄 **The full explanation of the mathematical model** (sets, parameters, decision
> variables, objective function and constraints, eqs. 1–10) **is in [`main.pdf`](main.pdf).**
> The comments in `entregable1.py` reference the same equation numbers.

## Repository contents

| File | Description |
|------|-------------|
| `main.pdf` | Report with the formulation and explanation of the model |
| `entregable1.py` | PuLP implementation of the model, solution extraction and plots |
| `NAME _CVRP_10_manual.txt` | Instance in TSPLIB/CVRPLIB format (coordinates, demands, capacity) |
| `img/nodes.png` | Plot of the nodes (square = depot) |
| `img/routes.png` | Plot of the optimal routes |
| `requirements.txt` | Python dependencies |

## Model summary

See `main.pdf` for the detailed derivation. In short:

- **Sets:** nodes `N` (node 1 is the depot), customers `C = N \ {1}`, vehicles `K = {1, 2, 3}`, arcs `A = {(i, j) : i ≠ j}`.
- **Parameters:** rounded Euclidean distance `d_ij` (eq. 1), demand `q_i`, capacity `Q = 50`.
- **Variables:** `x_ijk ∈ {0,1}` (vehicle `k` travels arc `i → j`), `u_i ∈ [0, Q]` (load accumulated on arrival at `i`).
- **Objective (eq. 4):** minimize total distance `Σ_k Σ_(i,j) d_ij · x_ijk`.
- **Constraints:**
  - (5) every customer is visited exactly once;
  - (6) flow conservation per node and vehicle;
  - (7) each vehicle leaves the depot at most once;
  - (8) vehicle capacity;
  - (9) MTZ subtour elimination;
  - (10) lower bounds on accumulated load.

## How to run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python entregable1.py
```

The script prints the solution and writes the plots to `img/`.

## Results

```
Status: Optimal
Minimum distance Z = 337.0
Vehicle 1: 1 -> 9 -> 5 -> 4 -> 10 -> 1  (load 49/50)
Vehicle 2: 1 -> 2 -> 3 -> 11 -> 1  (load 47/50)
Vehicle 3: 1 -> 6 -> 7 -> 8 -> 1  (load 50/50)
```

| Nodes | Optimal routes |
|-------|----------------|
| ![Nodes](img/nodes.png) | ![Routes](img/routes.png) |
