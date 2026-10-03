# Capacitated Vehicle Routing Problem

Didactic CVRP instance: 1 depot, 10 customers and
capacity 50 using a Mixed-Integer Linear Programming model solved with PuLP + CBC.

The full explanation of the mathematical model is in [`main.pdf`](main.pdf). The comments in `entregable1.py` reference the same equation numbers.

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
