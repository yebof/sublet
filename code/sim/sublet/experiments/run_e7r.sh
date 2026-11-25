#!/usr/bin/env bash
# E7r: baselines and stress regimes of MS7 (design/ms7/plan.md X4, X5, D6; change C54). Runs the jobs of
# sublet.experiments.e7r under the slot semaphore shared with MS3-MS5b (ms3_lib.sh: one 3G scope per job, at most 4 jobs
# on the host), one part at a time, each part with its own output folder MS3_OUT = out/e7r/<part> (jobs/, logs/, runs/,
# retry/, manifest.json, summary.json, tables.md, run_e7r.log).
#
#   E7R_PART="<part> [<part> ...]" sublet/experiments/run_e7r.sh [--reduced]
#
# Parts in this order: tune (weeks 113-116; then e7r_select.py writes tune/selection.json), confirm (weeks 121-124)
# and eval (weeks 301-316; then e7r_analysis.py writes out/e7r/analysis.json and analysis.md). confirm and eval read
# tune's selection, so run tune first. Per part: the gate (`e7r --check-start`: design/ms7/registration.md at HEAD, a
# clean tree, the registered sha256 of e7r_select.py and e7r_analysis.py, and for confirm and eval the selection; exit
# 2 when refused), the job list, the manifest, the pool jobs, the missing-run rule's rerun (`e7r --retry-list`, once
# per pool job), the manifest again, the summary, the part's script (tune: e7r_select.py; eval: e7r_analysis.py) in a
# 3G scope, then ms3_finish's done line.
# --reduced: the reduced job lists of e7r.py's docstring (MS7_E7R_REDUCED=1: the development cell bench_e7f 101 with
# a 2-hour horizon; the gate is recorded, not enforced), for smoke runs under a scratch MS3_ROOT, never a result.
# Environment as ms3_lib.sh (MS3_WORKERS, MS3_RESUME, MS3_ROOT, ...; MS3_OUT is set per part here), plus, for tests
# and smoke runs only, E7R_ONLY=<extended regex>: only the jobs whose list line matches run (the summary lists the
# others as missing), and E7R_FROZEN=<folder>: the confirmation's folder that e7r_analysis.py reads (default
# <MS3_ROOT>/out/sublet_v2).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS7_E7R_REDUCED=1 ;;
    *) echo "usage: E7R_PART=<part> $0 [--reduced]" >&2; exit 2 ;;
  esac
done
E7R_PARTS="${E7R_PART:-}"
E7R_PARTS="${E7R_PARTS//,/ }"
if [ -z "${E7R_PARTS// /}" ]; then
  echo "[run_e7r] E7R_PART must name the part(s) to run: tune confirm eval" >&2
  exit 2
fi
for part in $E7R_PARTS; do
  case "$part" in
    tune | confirm | eval) ;;
    *) echo "[run_e7r] unknown part '$part'" >&2; exit 2 ;;
  esac
done
E7R_ONLY="${E7R_ONLY:-}"
if [ -n "$E7R_ONLY" ]; then
  printf '' | grep -Eq -- "$E7R_ONLY" 2> /dev/null
  [ $? -eq 2 ] && { echo "[run_e7r] E7R_ONLY is not a valid extended regex: '$E7R_ONLY'" >&2; exit 2; }
fi
source "$(dirname "$0")/ms3_lib.sh"

e7r_check_start() {   # 0 iff the part's gate lets it start (e7r --check-start in a 3G scope; its lines to the log)
  local -a MS3_PRE
  _ms3_prefix
  "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --check-start 2>&1 | tee -a "$MS3_LOG"
  return "${PIPESTATUS[0]}"
}

e7r_only() {          # keep the list lines that match E7R_ONLY (tests and smoke runs)
  [ -n "$E7R_ONLY" ] || return 0
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_all.txt"
  grep -E -- "$E7R_ONLY" "$MS3_OUT/jobs_list_all.txt" > "$MS3_OUT/jobs_list.txt"
  _ms3_log "E7R_ONLY='$E7R_ONLY': $(wc -l < "$MS3_OUT/jobs_list.txt") of $(wc -l < "$MS3_OUT/jobs_list_all.txt") jobs"
}

e7r_retry() {         # the missing-run rule's rerun: once per pool job
  local -a MS3_PRE
  _ms3_prefix
  if ! "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --retry-list --out "$MS3_OUT" > "$MS3_OUT/jobs_retry.txt" \
      2>> "$MS3_LOG"; then
    _ms3_log "could not list the jobs to rerun"
    return 0
  fi
  if [ -n "$E7R_ONLY" ]; then
    grep -E -- "$E7R_ONLY" "$MS3_OUT/jobs_retry.txt" > "$MS3_OUT/jobs_retry_only.txt" || true
    mv "$MS3_OUT/jobs_retry_only.txt" "$MS3_OUT/jobs_retry.txt"
  fi
  _ms3_log "rerun once: $(grep -c '^pool ' "$MS3_OUT/jobs_retry.txt") pool job(s)"
  [ -s "$MS3_OUT/jobs_retry.txt" ] || return 0
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_full.txt"
  cp "$MS3_OUT/jobs_retry.txt" "$MS3_OUT/jobs_list.txt"
  ms3_run_jobs pool
  mv "$MS3_OUT/jobs_list_full.txt" "$MS3_OUT/jobs_list.txt"
}

e7r_script() {        # e7r_script MODULE [ARGS...]: a part's script in a 3G scope, its output to the run log
  local -a MS3_PRE
  _ms3_prefix
  local mod="$1" rc
  shift
  "${MS3_PRE[@]}" "$MS3_PY" -m "$mod" --root "$MS3_ROOT" "$@" 2>&1 | tee -a "$MS3_LOG"
  rc="${PIPESTATUS[0]}"
  [ "$rc" -eq 0 ] || { _ms3_log "$mod failed (exit $rc)"; return 1; }
}

for part in $E7R_PARTS; do
  export E7R_PART="$part"
  MS3_OUT="$MS3_ROOT/out/e7r/$part"
  ms3_init e7r
  _ms3_log "part $part"
  if ! e7r_check_start; then
    _ms3_log "refused: part $part does not start (design/ms7/plan.md D6)"
    exit 2
  fi
  ms3_list
  e7r_only
  ms3_manifest
  ms3_run_jobs pool
  e7r_retry
  ms3_manifest
  ms3_summary
  case "$part" in
    tune) e7r_script sublet.experiments.e7r_select || exit 1 ;;
    eval)
      if [ -n "${E7R_FROZEN:-}" ]; then
        e7r_script sublet.experiments.e7r_analysis --frozen "$E7R_FROZEN" || exit 1
      else
        e7r_script sublet.experiments.e7r_analysis || exit 1
      fi ;;
  esac
  ms3_finish
done
