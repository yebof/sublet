"""Timing benchmark (planning only): per-request cost of the reference FracPD (pure Python)."""
import sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'theory_checks' / 'c3'))
import core, pd
for (T, m, n) in [(48, 6, 12), (96, 12, 24), (96, 24, 24)]:
    rng = np.random.default_rng(1)
    I = core.random_instance(rng, T=T, m=m, J=2, n=n, K=3)
    nreq = len(I.elements())
    t0 = time.time(); P = pd.FracPD(I); P.run(); dt = time.time() - t0
    print(f"T={T} m={m} n={n} K=3 requests={nreq} time={dt:.2f}s per_request_ms={1e3*dt/nreq:.2f}", flush=True)
