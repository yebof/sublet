"""Run a planning benchmark on at most 4 CPUs and report wall time and peak memory.

Usage (always inside a memory-capped scope, one heavy run at a time):
  systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
      ~/venv/bin/python run_capped.py lp_scale.py 0 > small_lp_cfg0.log 2>&1

The benchmarked script runs unchanged as __main__ with the given arguments. CPU affinity is
restricted to 4 cores before it starts, so solver threads (HiGHS) inherit the limit.
Peak RSS is ru_maxrss of this process, which includes the in-process HiGHS solver.
"""
import os
import resource
import runpy
import sys
import time

os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
script, args = sys.argv[1], sys.argv[2:]
sys.argv = [script] + args
t0 = time.time()
runpy.run_path(script, run_name="__main__")
print(f"[run_capped] script={os.path.basename(script)} args={' '.join(args) or '-'} "
      f"cpus={len(os.sched_getaffinity(0))} wall={time.time() - t0:.1f}s "
      f"peak_rss={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f}MB", flush=True)
