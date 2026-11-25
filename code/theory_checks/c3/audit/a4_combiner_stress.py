"""Audit: Theorem 11 doubling combiner, abstract stress test.
Each simulated algorithm X has leases (buy b, end e, cost c) and per-slot service s_X(t).
Combiner as in the draft: follow X; if C_X(t) > gamma*C_Y(t), buy Y's live leases fresh
(those with b <= t < e) and pay Y's service at t, then follow Y.  Random search + hill climbing
for the worst ALG/min(C_A(T),C_B(T)); bound gamma + gamma^2/(gamma-1)."""
import math
import numpy as np

def run(T, leases, serv, gamma):
    C = {}
    for X in (0, 1):
        inc = serv[X].copy()
        for (b, e, c) in leases[X]:
            inc[b] += c
        C[X] = (inc, np.cumsum(inc))
    cur = 0 if C[0][1][0] <= C[1][1][0] else 1
    tot = 0.0
    for t in range(T):
        Y = 1 - cur
        if C[cur][1][t] > gamma * C[Y][1][t] + 1e-12:
            cur = Y
            tot += sum(c for (b, e, c) in leases[cur] if b <= t < e) + serv[cur][t]
        else:
            tot += C[cur][0][t]
    return tot / min(C[0][1][-1], C[1][1][-1])

def rand_inst(rng, T):
    leases, serv = [], []
    for X in (0, 1):
        n = rng.integers(0, 6)
        L = []
        for _ in range(n):
            b = int(rng.integers(0, T)); d = int(rng.integers(1, T + 1))
            L.append((b, min(T, b + d), float(rng.exponential(1.0) * 10 ** rng.uniform(-1, 2))))
        leases.append(L)
        s = rng.exponential(1.0, T) * (rng.random(T) < rng.uniform(0, 1)) * 10 ** rng.uniform(-1, 1)
        serv.append(s + 1e-3)
    return leases, serv

def mutate(rng, inst, T):
    leases, serv = [list(l) for l in inst[0]], [s.copy() for s in inst[1]]
    X = int(rng.integers(0, 2))
    if rng.random() < 0.5 and leases[X]:
        i = int(rng.integers(0, len(leases[X]))); b, e, c = leases[X][i]
        leases[X][i] = (b, e, max(1e-3, c * math.exp(rng.normal(0, 0.5))))
    elif rng.random() < 0.5:
        b = int(rng.integers(0, T)); leases[X].append((b, T, float(10 ** rng.uniform(-1, 2))))
    else:
        t = int(rng.integers(0, T)); serv[X][t] = max(1e-3, serv[X][t] * math.exp(rng.normal(0, 1)) + rng.exponential(0.3))
    return leases, serv

rng = np.random.default_rng(1)
for gamma in [2.0, 1 + 1 / math.sqrt(2)]:
    bound = gamma + gamma ** 2 / (gamma - 1)
    best = 0.0
    for rep in range(300):
        T = int(rng.integers(3, 16))
        inst = rand_inst(rng, T); val = run(T, *inst, gamma)
        for it in range(300):
            cand = mutate(rng, inst, T); v = run(T, *cand, gamma)
            if v >= val:
                inst, val = cand, v
        best = max(best, val)
    print(f"gamma={gamma:.4f}: worst found ALG/min = {best:.3f}  (bound {bound:.3f})  ok={best <= bound + 1e-9}")
