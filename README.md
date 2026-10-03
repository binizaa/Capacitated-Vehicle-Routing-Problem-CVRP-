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
Minimum distance Z = 317.0
Solve time: 1.52 s
Vehicle 1: 1 -> 3 -> 2 -> 6 -> 1  (load 44/50, distance 100)
Vehicle 2: 1 -> 9 -> 8 -> 7 -> 1  (load 47/50, distance 108)
Vehicle 3: 1 -> 10 -> 1  (load 13/50, distance 22)
Vehicle 4: 1 -> 11 -> 5 -> 4 -> 1  (load 42/50, distance 87)
```

| Nodes | Optimal routes |
|-------|----------------|
| ![Nodes](img/nodes.png) | ![Routes](img/routes.png) |
