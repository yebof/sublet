"""Exact small-game values on the T4 family with tau = 1, H = 0 (D = 1).

For tiny (m, T, rho) we compute, over ALL oblivious schedules omega (R_l subset of {1..T-1}):
  det    = min over deterministic algorithms of max_omega ALG/OPT(sigma, omega).  This is also the
           value against an adaptive(-offline) lender for randomized algorithms.
  rand_I1 = min over randomized algorithms of max_omega E[ALG]/OPT, own-lease feedback
           (sequence-form LP, Koller-Megiddo-von Stengel).
  rand_I2 = the same with full feedback (all sites' announcement bits are observed).
Algorithms: 'multi' = may hold any non-empty set of leases each slot; 'single' = exactly one.
With D = 1, re-buying a live lease and fallback are dominated, so actions are target sets.
Output: out/o1_game.txt, out/o1_game.json
"""
import os, sys, json, itertools, time
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog
import multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fam import Fam, opt_dp

OUT = os.path.join(HERE, 'out')


def all_omegas(m, T):
    slots = list(range(1, T))
    per = [tuple(s for s, b in zip(slots, bits) if b) for bits in itertools.product([0, 1], repeat=len(slots))]
    for combo in itertools.product(per, repeat=m):
        yield [np.array(c, dtype=int) for c in combo]


class Tree:
    def __init__(self, m, T, beta, a, mode, info):
        self.m, self.T, self.beta, self.a, self.info = m, T, beta, a, info
        if mode == 'multi':
            self.actions = [frozenset(c) for r in range(1, m + 1) for c in itertools.combinations(range(m), r)]
        else:
            self.actions = [frozenset([l]) for l in range(m)]
        self.nodes = []      # node: (t, alive frozenset, parent_seq, list of (action, seq))
        self.seq_cost = []
        self.child = []      # seq -> dict obs -> node id
        self._build(0, frozenset(), -1)

    def _obs_list(self, S):
        if self.info == 'I1':
            base = sorted(S)
        else:
            base = list(range(self.m))
        return [frozenset(c) for r in range(len(base) + 1) for c in itertools.combinations(base, r)]

    def _build(self, t, alive, parent):
        nid = len(self.nodes)
        acts = []
        self.nodes.append((t, alive, parent, acts))
        for S in self.actions:
            sid = len(self.seq_cost)
            self.seq_cost.append(self.beta * len(S - alive) + self.a * len(S))
            self.child.append({})
            acts.append((S, sid))
            if t + 1 < self.T:
                for o in self._obs_list(S):
                    self.child[sid][o] = self._build(t + 1, S - o, sid)
        return nid

    def path_coefs(self, R):
        """sequences consistent with schedule R (list of sets) and their cost increments."""
        out = []
        stack = [0]
        while stack:
            nid = stack.pop()
            t, alive, parent, acts = self.nodes[nid]
            for S, sid in acts:
                out.append(sid)
                if t + 1 < self.T:
                    ann = frozenset(l for l in range(self.m) if (t + 1) in R[l])
                    o = (ann & S) if self.info == 'I1' else ann
                    stack.append(self.child[sid][o])
        return out

    def det_value(self, Rs, opts):
        """min over deterministic strategies of max over omega of cost/OPT."""
        memo = {}

        def V(nid, Om, acc):
            t, alive, parent, acts = self.nodes[nid]
            best = np.inf
            for S, sid in acts:
                c = acc + self.seq_cost[sid]
                if t + 1 >= self.T:
                    v = c / min(opts[w] for w in Om)
                else:
                    parts = {}
                    for w in Om:
                        ann = frozenset(l for l in range(self.m) if (t + 1) in Rs[w][l])
                        o = (ann & S) if self.info == 'I1' else ann
                        parts.setdefault(o, []).append(w)
                    v = max(V(self.child[sid][o], tuple(ws), c) for o, ws in parts.items())
                best = min(best, v)
            return best
        return V(0, tuple(range(len(Rs))), 0.0)


def solve(args):
    m, T, rho, mode, info, want_det = args
    F = Fam(m, rho, 1, 0, T)
    oms = list(all_omegas(m, T))
    opts = [opt_dp(F, om)[0] for om in oms]
    Rs = [[set(map(int, om[l])) for l in range(m)] for om in oms]
    t0 = time.time()
    tr = Tree(m, T, F.beta, F.a, mode, info)
    nS = len(tr.seq_cost)
    # equality constraints (sequence form)
    rows, cols, vals, b = [], [], [], []
    for nid, (t, alive, parent, acts) in enumerate(tr.nodes):
        r = len(b)
        for S, sid in acts:
            rows.append(r); cols.append(sid); vals.append(1.0)
        if parent >= 0:
            rows.append(r); cols.append(parent); vals.append(-1.0); b.append(0.0)
        else:
            b.append(1.0)
    Aeq = sp.csr_matrix((vals, (rows, cols)), shape=(len(b), nS + 1))
    cost = np.array(tr.seq_cost)
    rows, cols, vals = [], [], []
    for w, R in enumerate(Rs):
        sids = tr.path_coefs(R)
        rows += [w] * len(sids); cols += sids; vals += list(cost[sids] / opts[w])
        rows.append(w); cols.append(nS); vals.append(-1.0)
    Aub = sp.csr_matrix((vals, (rows, cols)), shape=(len(Rs), nS + 1))
    c = np.zeros(nS + 1); c[-1] = 1.0
    res = linprog(c, A_ub=Aub, b_ub=np.zeros(len(Rs)), A_eq=Aeq, b_eq=np.array(b),
                  bounds=[(0, None)] * nS + [(None, None)], method='highs')
    out = dict(m=m, T=T, rho=rho, mode=mode, info=info, n_seq=nS, n_omega=len(Rs),
               rand=float(res.fun), status=int(res.status), sec=time.time() - t0)
    if want_det:
        out['det'] = tr.det_value(Rs, opts)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    for rho in [3, 9, 33]:
        jobs += [(2, 4, rho, 'multi', 'I1', True), (2, 4, rho, 'multi', 'I2', True),
                 (2, 5, rho, 'multi', 'I1', True), (2, 5, rho, 'multi', 'I2', True),
                 (2, 6, rho, 'multi', 'I1', False),
                 (3, 4, rho, 'single', 'I1', True), (3, 4, rho, 'single', 'I2', True),
                 (3, 5, rho, 'single', 'I1', True), (3, 4, rho, 'multi', 'I1', True)]
    with mp.Pool(5) as pool:
        res = pool.map(solve, jobs)
    with open(os.path.join(OUT, 'o1_game.json'), 'w') as f:
        json.dump(res, f, indent=1)
    L = ['Exact game values, tau=1, H=0 (D=1), all 2^(m(T-1)) oblivious schedules',
         'm T rho mode    info  #seq     #omega  rand(oblivious)  det(=adaptive)  status']
    for r in res:
        L.append(f"{r['m']} {r['T']} {r['rho']:<3} {r['mode']:<7} {r['info']}    {r['n_seq']:<8} {r['n_omega']:<7} "
                 f"{r['rand']:.4f}           {r.get('det', float('nan')):.4f}          {r['status']}")
    txt = '\n'.join(L)
    print(txt)
    with open(os.path.join(OUT, 'o1_game.txt'), 'w') as f:
        f.write(txt + '\n')


if __name__ == '__main__':
    main()
