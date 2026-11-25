"""Independent audit check of prop:s-alg-admissible and prop:s-alg-tied (Supplement S-B.7; MS7 D8(a), design/ms7/plan.md).

Random fractional-step instances: global columns with costs C_F >= 0, a sequence of requests, each with a
candidate list of at most M columns, routing costs delta >= 0 and fallback q > 0; d = M + 1. Three raise rules:
  loop  - S-B.2: raise A = {F: x_F <= y_F} until its constraint holds;
  tied  - the tied raise of s_b_poly.tex (closed forms, ties, one root in the last piece);
  rand  - a random admissible rule: random convex weights on 1-3 random violated constraints, piece ends when the
          first weighted constraint reaches 1 (so (II) holds), repeated until phi >= 1.
Checks: variables in [0, 1]; invariant v + 1/d = exp(Y_v / c_v) / d for c_v > 0; Y_v = 0 for c_v = 0;
dual feasibility Y_v <= c_v ln(1 + d); P <= 2 sum Y; phi >= 1 at the end of every request; for tied: every weighted
constraint has lhs = phi at the piece start and the piece count is <= |F^>| + 1.
"""
import itertools
import math
import sys

import numpy as np
from scipy.optimize import brentq

TOL = 1e-9
STATS={'tie_end':0,'pieces_max':0,'rand_pieces_max':0}


def lhs(A, x, y, f):
    return sum(x[i] if i in A else y[i] for i in range(len(x))) + f


def run(inst, rule, rng):
    C, reqs, q, d = inst["C"], inst["reqs"], inst["q"], inst["d"]
    X = np.zeros(len(C))
    YX = np.zeros(len(C))
    sumY = 0.0
    P_serv = 0.0
    viol = []
    max_pieces_ratio = 0.0
    for (cand, dl) in reqs:
        n = len(cand)
        x = X[cand].copy()
        Cc = C[cand]
        # initialization
        for i in range(n):
            if Cc[i] == 0:
                x[i] = 1.0
        y = np.where(dl == 0, 1.0, 0.0)
        f = 0.0
        Yx = np.zeros(n)
        Yy = np.zeros(n)
        Yf = 0.0
        pieces = 0
        phi = lambda: float(np.minimum(x, y).sum() + f)
        Fgt0 = None
        while phi() < 1 - 1e-12:
            pieces += 1
            if pieces > 5000:
                viol.append(("pieces>5000", rule))
                break
            if rule == "loop":
                A = frozenset(i for i in range(n) if x[i] <= y[i])
                wts = {A: 1.0}
            elif rule == "tied":
                lt = [i for i in range(n) if x[i] < y[i]]
                gt = [i for i in range(n) if x[i] > y[i]]
                eq = [i for i in range(n) if x[i] == y[i]]
                if Fgt0 is None:
                    Fgt0 = len(gt)
                lam = {i: Cc[i] / (Cc[i] + dl[i]) for i in eq}
                cuts = sorted(set([0.0, 1.0] + [lam[i] for i in eq]))
                wts = {}
                for a, b in zip(cuts[:-1], cuts[1:]):
                    u = 0.5 * (a + b)
                    A = frozenset(lt + [i for i in eq if u < lam[i]])
                    wts[A] = wts.get(A, 0.0) + (b - a)
                for A in wts:
                    if abs(lhs(A, x, y, f) - phi()) > 1e-9:
                        viol.append(("tied lhs != phi", lhs(A, x, y, f), phi()))
            else:
                allA = [frozenset(s) for r in range(n + 1) for s in itertools.combinations(range(n), r)]
                va = [A for A in allA if lhs(A, x, y, f) < 1 - 1e-12]
                k = int(rng.integers(1, min(3, len(va)) + 1))
                pick = rng.choice(len(va), size=k, replace=False)
                w = rng.random(k) + 0.05
                w /= w.sum()
                wts = {va[p]: float(wv) for p, wv in zip(pick, w)}
            pix = np.zeros(n)
            piy = np.zeros(n)
            for A, wv in wts.items():
                for i in range(n):
                    if i in A:
                        pix[i] += wv
                    else:
                        piy[i] += wv
            pif = 1.0
            # moving variables must have positive cost
            for i in range(n):
                if pix[i] > 1e-15 and Cc[i] == 0:
                    viol.append(("raise of cost-0 x", rule))
                if piy[i] > 1e-15 and dl[i] == 0:
                    viol.append(("raise of cost-0 y", rule))
            rx = np.where(pix > 0, pix / np.where(Cc > 0, Cc, 1), 0.0)
            ry = np.where(piy > 0, piy / np.where(dl > 0, dl, 1), 0.0)
            rf = pif / q

            def state(z):
                return ((x + 1 / d) * np.exp(rx * z) - 1 / d, (y + 1 / d) * np.exp(ry * z) - 1 / d,
                        (f + 1 / d) * math.exp(rf * z) - 1 / d)

            def lhsz(A, z):
                xs, ys, fs = state(z)
                return lhs(A, xs, ys, fs)

            if rule == "tied":
                # end: first tie or phi = 1
                ties = []
                for i in range(n):
                    if x[i] < y[i] and rx[i] > 0:
                        ties.append(math.log((y[i] + 1 / d) / (x[i] + 1 / d)) / rx[i])
                    if x[i] > y[i] and ry[i] > 0:
                        ties.append(math.log((x[i] + 1 / d) / (y[i] + 1 / d)) / ry[i])
                Df = math.log((1 + 1 / d) / (f + 1 / d)) / rf
                Dt = min(ties) if ties else math.inf
                Dl = min(Dt, Df)
                phz = lambda z: float(np.minimum(*state(z)[:2]).sum() + state(z)[2])
                if phz(Dl) < 1:
                    z1 = Dl
                    tie_end = True
                    STATS['tie_end']+=1
                else:
                    z1 = brentq(lambda z: phz(z) - 1.0, 0.0, Dl, xtol=1e-15, rtol=1e-14)
                    tie_end = False
                    if Dl > Df + 1e-12:
                        viol.append(("root interval > Delta_f",))
                    if Df > q * math.log(1 + d) + 1e-9:
                        viol.append(("Delta_f > q ln(1+d)",))
            else:
                ends = []
                for A in wts:
                    hi = 0.0
                    step = 1e-6
                    while lhsz(A, hi + step) < 1:
                        hi += step
                        step *= 2
                    ends.append(brentq(lambda z: lhsz(A, z) - 1.0, hi, hi + step, xtol=1e-15, rtol=1e-14))
                z1 = min(ends)
            # check (II) on a grid inside the piece
            for A in wts:
                for s in (0.0, 0.25, 0.5, 0.75, 0.999):
                    if lhsz(A, s * z1) >= 1 + 1e-12:
                        viol.append(("(II) violated", rule))
            xs, ys, fs = state(z1)
            if rule == "tied" and tie_end:
                # snap the tied column exactly (the closed form ties it exactly)
                for i in range(n):
                    if abs(xs[i] - ys[i]) < 1e-12 * max(1.0, xs[i]):
                        m = max(xs[i], ys[i])
                        xs[i] = ys[i] = m
            x, y, f = xs, ys, fs
            Yx += pix * z1
            Yy += piy * z1
            Yf += pif * z1
            sumY += z1
        if rule=='tied': STATS['pieces_max']=max(STATS['pieces_max'],pieces)
        if rule=='rand': STATS['rand_pieces_max']=max(STATS['rand_pieces_max'],pieces)
        if rule == "tied" and Fgt0 is not None and pieces > Fgt0 + 1:
            viol.append(("tied pieces > |F^>|+1", pieces, Fgt0))
        if phi() < 1 - 1e-9:
            viol.append(("phi < 1 at end", rule, phi()))
        X[cand] = x
        YX[cand] += Yx
        # invariants on y, f of this request
        for i in range(n):
            if dl[i] > 0:
                if abs(math.log(y[i] + 1 / d) - math.log(1 / d) - Yy[i] / dl[i]) > 1e-7:
                    viol.append(("invariant y", rule))
                if Yy[i] > dl[i] * math.log(1 + d) + 1e-9:
                    viol.append(("dual y", rule))
            elif Yy[i] > 1e-12:
                viol.append(("dual on cost-0 y", rule))
            if y[i] > 1 + 1e-9 or y[i] < -1e-12:
                viol.append(("y range", rule))
        if abs(math.log(f + 1 / d) - math.log(1 / d) - Yf / q) > 1e-7:
            viol.append(("invariant f", rule))
        if f > 1 + 1e-9:
            viol.append(("f range", rule))
        P_serv += float(np.dot(dl, y)) + q * f
    for F in range(len(C)):
        if C[F] > 0:
            if abs(math.log(X[F] + 1 / d) - math.log(1 / d) - YX[F] / C[F]) > 1e-7:
                viol.append(("invariant x", rule))
            if YX[F] > C[F] * math.log(1 + d) + 1e-9:
                viol.append(("dual x", rule))
        elif YX[F] > 1e-12:
            viol.append(("dual on cost-0 x", rule))
        if X[F] > 1 + 1e-9:
            viol.append(("x range", rule))
    P = float(np.dot(C, X)) + P_serv
    if P > 2 * sumY + 1e-7:
        viol.append(("P > 2 sum Y", rule, P, sumY))
    return viol, P, sumY


def instance(rng):
    nF = int(rng.integers(2, 9))
    M = int(rng.integers(1, 5))
    C = rng.choice([0.0, 0.5, 1.0, 3.0, 7.0], size=nF, p=[0.1, 0.2, 0.3, 0.2, 0.2]) * rng.random(nF)
    C = np.round(C, 3)
    q = float(rng.choice([0.5, 2.0, 10.0]))
    reqs = []
    for _ in range(int(rng.integers(1, 12))):
        k = int(rng.integers(0, min(M, nF) + 1))
        cand = rng.choice(nF, size=k, replace=False)
        dl = np.round(rng.choice([0.0, 0.2, 1.0, 4.0], size=k, p=[0.15, 0.35, 0.3, 0.2]) * rng.random(k), 3)
        reqs.append((cand.astype(int), dl.astype(float)))
    return dict(C=C, reqs=reqs, q=q, d=M + 1)


def main(n_inst):
    rng = np.random.default_rng(20261107)
    bad = 0
    for it in range(n_inst):
        inst = instance(rng)
        for rule in ("loop", "tied", "rand"):
            v, P, sY = run(inst, rule, np.random.default_rng(it))
            if v:
                bad += 1
                print("instance", it, rule, v[:3])
    print(STATS)
    print("instances", n_inst, "rules x instances with a violation:", bad)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
