"""Audit b5: the closed-form corollaries of O1-A and O1-C on a fine (rho, m) grid, including
non-integer rho, plus the Theta(.) summaries.
  O1-A Cor.1: LB_A(k=m) = m(rho+1)/(2(rho+m-1))
  O1-A Cor.2: max_k LB_A(k) >= min(rho, m)/4   (m >= 3)
  O1-C Cor.1: LB_C(1/2) >= min(rho+1, 0.63 log2 m)/4, and mu_{m,1/2} >= (1-1/e)(floor(log2 m)+1)
  Summary ratios: UB_I1/LB_I1 = min(rho, 2m)/max_k LB_A ; UB_I2/LB_I2 = min(rho, 2H_m+1)/max_p LB_C
Output: out/b5_formulas.txt
"""
import os, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')


def g_fn(k, m):
    return sum(max(0.0, 1.0 - (j - 1) / (m - 1)) for j in range(1, k))


def lbA(rho, m, k):
    return ((rho - 1) * g_fn(k, m) + k) / (rho - 1 + k)


def best_lbA(rho, m):
    # g grows until k = m, after that g is flat; LB_A is then decreasing in k when g < ... scan to 4m + 4 rho
    kmax = int(4 * m + 4 * rho + 10)
    return max(lbA(rho, m, k) for k in range(2, kmax))


def mu(m, p):
    s, g = 0.0, 0
    while True:
        term = 1.0 - (1.0 - (1.0 - p) ** g) ** m
        s += term
        g += 1
        if term < 1e-14 and g > 5:
            return s


def lbC(rho, m, p):
    u = mu(m, p)
    return ((rho - 1) * p + 1) / ((rho - 1) / u + 1)


def best_lbC(rho, m):
    return max(lbC(rho, m, p) for p in np.linspace(0.005, 0.995, 199))


def harm(m):
    return sum(1.0 / i for i in range(1, m + 1))


def main():
    os.makedirs(OUT, exist_ok=True)
    rhos = list(np.round(np.concatenate([np.linspace(1.0, 4, 13), np.geomspace(4, 512, 15)]), 4))
    ms = [3, 4, 5, 6, 8, 12, 16, 32, 64, 128, 256, 1024]
    worst2, worstC, worstK1 = (math.inf, None), (math.inf, None), (math.inf, None)
    worst_mu = (math.inf, None)
    gapI1, gapI2 = (0, None), (0, None)
    for m in ms:
        u = mu(m, 0.5)
        lb = (1 - 1 / math.e) * (math.floor(math.log2(m)) + 1)
        if u / lb < worst_mu[0]:
            worst_mu = (u / lb, m)
        for rho in rhos:
            bA = best_lbA(rho, m)
            v = bA / (min(rho, m) / 4)
            if v < worst2[0]:
                worst2 = (v, (float(rho), m))
            k1 = lbA(rho, m, m) / (0.5 * rho * m / (m + rho - 1))
            if k1 < worstK1[0]:
                worstK1 = (k1, (float(rho), m))
            c = lbC(rho, m, 0.5) / (min(rho + 1, 0.63 * math.log2(m)) / 4)
            if c < worstC[0]:
                worstC = (c, (float(rho), m))
            g1 = min(rho, 2 * m) / bA
            if g1 > gapI1[0]:
                gapI1 = (g1, (float(rho), m))
    for m in [3, 8, 64, 1024]:
        for rho in [4, 16, 64, 256]:
            bC = best_lbC(rho, m)
            g2 = min(rho, 2 * harm(m) + 1) / bC
            if g2 > gapI2[0]:
                gapI2 = (g2, (rho, m))
    L = ['b5: closed-form corollaries on a grid (rho in [1, 512] incl. non-integers, m in 3..1024)',
         f'O1-A Cor.1  min LB_A(k=m) / (rho m/(2(m+rho-1)))      = {worstK1[0]:.4f} at (rho, m) = {worstK1[1]}   (claim: >= 1)',
         f'O1-A Cor.2  min max_k LB_A / (min(rho,m)/4)            = {worst2[0]:.4f} at {worst2[1]}   (claim: >= 1)',
         f'O1-C        min mu_(m,1/2) / ((1-1/e)(floor(log2 m)+1)) = {worst_mu[0]:.4f} at m = {worst_mu[1]}   (claim: >= 1)',
         f'O1-C Cor.1  min LB_C(1/2) / (min(rho+1, 0.63 log2 m)/4) = {worstC[0]:.4f} at {worstC[1]}   (claim: >= 1)',
         f'I1 gap      max min(rho,2m) / max_k LB_A               = {gapI1[0]:.3f} at {gapI1[1]}   (constant-factor gap of Theta(min(rho,m)))',
         f'I2 gap      max min(rho,2H_m+1) / max_p LB_C           = {gapI2[0]:.3f} at {gapI2[1]}   (on the coarse grid)']
    txt = '\n'.join(L)
    print(txt)
    open(os.path.join(OUT, 'b5_formulas.txt'), 'w').write(txt + '\n')


if __name__ == '__main__':
    main()
