"""T0's q*n(t) term: abort rates when the inner policy is S's own twin (same coins, executes R's purchases and
releases at window end: ALG_E <= C_R pathwise by G1(b)), and on the P5 family with greedy inner policies.
T0g bounds the slot's service by routing over the leases held after A_E(t) that are inside their prepaid window
(alive for every lender), so ALG(t) <= ahat(t) still holds and m == 0.
Audit of C3 §9: design/theory/audit_guard.md. Uses a5_guard_independent.py and, from code/theory_checks/c3,
pd.py and check_c4_lower.py. Output: out/a6_t0_twin.txt (also printed)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import numpy as np
from a5_guard_independent import (Ix, ex_R, ex_FB, combine, run, ETwin, ERenter, make_lender, Stats, guard_checks, make_inst,
                                  LENDERS, G2C)
from pd import FracPD
from check_c4_lower import single

OUT = []


def out(*a):
    line = ' '.join(str(x) for x in a)
    print(line)
    OUT.append(line)


st = Stats()
cnt = {}
for fam in ('rand', 'tau0', 'slo', 'hq'):
    for seed in range(8):
        I = make_inst(fam, seed)
        ix = Ix(I, f'{fam}#{seed}')
        pdr = FracPD(I).run()
        for r in (1, None):
            R = ex_R(ix, pdr, 5000 + seed, r)
            for gamma in (1.0, G2C):
                for test in ('T0', 'T0g', 'T1'):
                    for allow in ('zero', 'cap'):
                        B = ix.allowance(allow)
                        for lk in LENDERS:
                            rec = run(ix, R, ETwin(ix, R, rent=False), make_lender(ix, lk, seed), gamma, B, test)
                            guard_checks(st, ix, R, gamma, B, test, rec, f'{ix.name} twin0 r={r} {test} {allow} {lk}')
                            k = (test, allow, round(gamma, 3))
                            c = cnt.setdefault(k, [0, 0]); c[0] += 1; c[1] += int(rec['ta'] is not None)
out('E = exact twin of S = R (same coins): abort rate by (test, allowance, gamma)')
for k in sorted(cnt):
    out('  ', k, f'{100 * cnt[k][1] / cnt[k][0]:.1f}% of {cnt[k][0]}')

# P5 family (q = 1e4, one always-active client): greedy (renter) inner policy
cnt2 = {}
for beta in (2, 6, 14, 30):
    T = 48
    I = single(T, [(1, 1), (T, 0)], float(beta), [1.0, 1.3])
    ix = Ix(I, f'P5 beta={beta}')
    pdr = FracPD(I).run()
    FB = ex_FB(ix)
    for sd in range(3):
        for r in (1, None):
            R = ex_R(ix, pdr, 71000 + sd, r)
            for S in (R, combine(ix, FB, R)):
                for test in ('T0', 'T0g', 'T1'):
                    B = ix.allowance('cap')
                    for lk in LENDERS:
                        rec = run(ix, S, ERenter(ix), make_lender(ix, lk, sd), 1.0, B, test)
                        guard_checks(st, ix, S, 1.0, B, test, rec, f'{ix.name} renter {test} {lk}')
                        k = (test,)
                        c = cnt2.setdefault(k, [0, 0, []]); c[0] += 1; c[1] += int(rec['ta'] is not None)
                        if rec['ta'] is not None:
                            c[2].append(rec['ta'])
out('P5 family, E = renter (BL1-like), capped allowance, gamma = 1: abort rate and abort slots')
for k in sorted(cnt2):
    c = cnt2[k]
    out('  ', k, f'{100 * c[1] / c[0]:.1f}% of {c[0]}; abort slots: min {min(c[2]) if c[2] else "-"}, '
          f'share at slot 0 {sum(x == 0 for x in c[2]) / max(1, len(c[2])):.2f}')
viol = sum(v[1] for v in st.d.values())
out('violations of the guard inequalities in these runs:', viol)
for line in st.lines():
    if 'm(t) == 0' in line:
        out(line)
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
with open(os.path.join(HERE, 'out', 'a6_t0_twin.txt'), 'w') as f:
    f.write('\n'.join(OUT) + '\n')
