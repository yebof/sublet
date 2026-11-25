#!/usr/bin/env bash
# Re-run every analysis step in order (outputs in analysis/out, figures in analysis/fig). The log, with the peak
# memory and wall time of every step (GNU time, "peak RSS" lines), is written to out/run_all.log.
# Each step runs in a memory-capped systemd scope without swap, so an out-of-memory kill stops only that step (and,
# with set -e, the run). Caps: 6 GB for the readers of the MaaS and WildChat raw traces (a2, a2b, a2c, a10, a4, a4b)
# and for a12 (simulator inputs from the Azure 2024, BurstGPT and MaaS raw traces; it reads a1's, a2's and a3's outputs,
# so it runs after them; run alone seven times under the 6 GB cap on 2026-10-16 it peaked at 1.7-1.8 GB, GNU time at
# most 1,788,740 KB, in 133-153 s), 3 GB for every other step. a2, a3, a8 and a12 read
# their raw tables one row group or chunk at a time to fit these caps.
# Peaks of the run of 2026-10-16 (out/run_all.log; GNU time reports the largest single process): a2 5.2 GB, a3 2.2 GB,
# a8 1.9 GB, a2b 1.6 GB, a2c 1.1 GB, a10 0.9 GB per process (4 workers), a4b 0.8 GB, every other step under 0.3 GB;
# the whole run took 18 min, of which the C2 audit step took 9 min. a4b changed after that run (borrower models of
# 2026-10-16): run alone under the same 6 GB cap it peaks at 0.9 GB (GNU time: 906,932 KB) in 18 s, and the a4b
# section of the log predates the change until the next full run. a12 changed likewise (the per-site slack split of
# the multi-site MaaS clusters, sim_spec §10 S34, reads instance_week_5min once more): run alone under the 6 GB cap
# it peaks at 2.2 GB (GNU time: 2,194,100 KB) in 279 s, and its section of the log predates the change.
# Order matters: a5b -> c2_audit (theory_checks/c2/audit model_switch_cost_default.py and switch_cost_crossover.py,
# which read a5b's JSON) -> a11, which reads their outputs and asserts that their prices equal a5b's; a9 -> a9b -> a11
# (buffers). c2/por_default.py (Table PoR at the default prices, about 20 min) is not run here: c2/audit/run_all.sh
# runs it, and a11 asserts that its prices equal a5b's.
# a13 (the Section II extract of MS6, design/ms6_spec.md §6 II) runs last: it reads a1's, a2's and a9's outputs only
# and exits nonzero if a recomputed value no longer matches the design's rounded value.
# MS7 (design/ms7/plan.md §3 X2, change C55): a4c (WildChat calendar weeks and the fit-part borrower model; it reads
# the WildChat raw trace through a4b.read(), so 6 GB like a4b; run alone on 2026-11-07: 0.73 GB, 27-65 s) runs after
# a4b, whose stored early model it reproduces; a14 (out-of-sample notice buffers; reads a1's and a2's series and
# a11's menu windows, seconds) runs after a11.
set -e -o pipefail
cd "$(dirname "$0")"
PY=${PY:-$HOME/venv/bin/python}
exec > >(tee out/run_all.log) 2>&1
echo "run_all.sh started $(date -Is)"
cap() {
  local mem=$1; shift
  /usr/bin/time -f "    peak RSS %M KB, %e s (cap $mem)" \
    systemd-run --user --scope -q -p MemoryMax="$mem" -p MemorySwapMax=0 "$PY" "$@"
}
BIG=" a2_lender_maas a2b_lender_maas_daily a2c_sm_coverage a12_sim_inputs a4_timezone_wildchat a4b_wildchat_weekly a4c_wildchat_weeks a10_maas_catalog "
for s in a1_lender_spotgpu a2_lender_maas a2b_lender_maas_daily a2c_sm_coverage a3_borrower_demand a12_sim_inputs a4_timezone_wildchat \
         a4b_wildchat_weekly a4c_wildchat_weeks a5_reclaim_cost_calibration a5b_exposure_thresholds c2_audit a10_maas_catalog \
         a6_spot_contrast a8_asi_topology a9_notice_buffer a9b_notice_buffer_24h a11_calibration a14_oos_buffers a7_policy_sim \
         a7b_layer_exposure a13_paper_extract; do
  echo "=== $s"
  if [ "$s" = c2_audit ]; then
    (cd ../theory_checks/c2/audit && for c in model_switch_cost_default switch_cost_crossover; do
       echo "    c2/audit/$c.py"; cap 3G "$c.py" > /dev/null; done)
  elif [[ "$BIG" == *" $s "* ]]; then
    cap 6G "$s.py"
  else
    cap 3G "$s.py"
  fi
done
echo "run_all.sh finished $(date -Is)"
