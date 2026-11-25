#!/usr/bin/env bash
# E7h: the MS5b pilot P0-P5 and the confirmation of Sublet v2 (design/sublet_v2.md §4, §5, §8.1; unit U35). Runs the
# jobs of sublet.experiments.e7h under the slot semaphore shared with MS3-MS5 (ms3_lib.sh: one 3G scope per job, at most
# 4 jobs and 2 MILP jobs on the host), one part at a time, each part with its own output folder (MS3_OUT =
# out/sublet_v2_pilot/<part> for p0, p2a, p3, p1, p2, p0r, p1r, p2r, p3r, p4, p5; out/sublet_v2/<part> for main, seeds,
# second, e3, fam, grid: jobs/, logs/, runs/, retry/, manifest.json, summary.json, tables.md, run_e7h.log).
#
#   E7H_PART="<part> [<part> ...]" sublet/experiments/run_e7h.sh [--reduced]
#
# The parts run in the order given (the pilot's order is p0 p2a p3 p1 p2 p0r p1r p2r p3r p4 p5; a decision is applied
# between steps, so run one step at a time). p0r-p3r are P2's allowance branch (design/sublet_v2.md §0, pilot log entry
# "P2, 2026-11-02"): Algorithm 1's allowance failed P2's test (3) and the alternative passed, so Sublet moved to the
# allowance min{W_k, LB'} and P0-P2 rerun for it on seeds 117-120 (with P3's Sublet runs) before p4. Per part: the gate
# (`e7h --check-start`: a pilot part refuses to start unless the pilot anchor is an ancestor of HEAD; a confirmation
# part unless design/sublet_v2_prereg.md exists at HEAD, the working tree is clean and the analysis script's sha256 is
# the recorded one; exit 2 when refused), the job list, the manifest, the pool jobs, the 'alone' jobs (the merged gap
# LPs), the MILP jobs (part e3 and p4: every MILP but the part=b00 jobs at b = 1, then those, which copy their cell's
# shared record, as run_e3.sh), the missing-run rule's rerun (§4.5: `e7h --retry-list` moves the record of every pool
# job not 'ok', or with a run that raised or failed an invariant, to retry/ and the job runs once more), the manifest
# again and the summary, then ms3_finish's done line.
# --reduced: the reduced job lists of e7h.py's docstring (MS3_E7H_REDUCED=1: development cells only, a 2-hour horizon),
# with MS3_MILP_LIMIT 30 s unless set; for smoke runs under a scratch MS3_ROOT, never a result. Environment as
# ms3_lib.sh (MS3_WORKERS, MS3_RESUME, MS3_ROOT, MS3_MILP_LIMIT, ...; MS3_OUT is set per part here), plus, for tests and
# smoke runs only, E7H_ONLY=<extended regex>: only the jobs whose list line matches run (the summary lists the others as
# missing).
set -u
for arg in "$@"; do
  case "$arg" in
    --reduced) export MS3_E7H_REDUCED=1; export MS3_MILP_LIMIT="${MS3_MILP_LIMIT:-30}" ;;
    *) echo "usage: E7H_PART=<part> $0 [--reduced]" >&2; exit 2 ;;
  esac
done
E7H_PARTS="${E7H_PART:-}"
E7H_PARTS="${E7H_PARTS//,/ }"
if [ -z "${E7H_PARTS// /}" ]; then
  echo "[run_e7h] E7H_PART must name the part(s) to run: p0 p2a p3 p1 p2 p0r p1r p2r p3r p4 p5 main seeds second e3" \
    "fam grid" >&2
  exit 2
fi
for part in $E7H_PARTS; do
  case "$part" in
    p0 | p2a | p3 | p1 | p2 | p0r | p1r | p2r | p3r | p4 | p5 | main | seeds | second | e3 | fam | grid) ;;
    *) echo "[run_e7h] unknown part '$part'" >&2; exit 2 ;;
  esac
done
E7H_ONLY="${E7H_ONLY:-}"
if [ -n "$E7H_ONLY" ]; then
  printf '' | grep -Eq -- "$E7H_ONLY" 2> /dev/null
  [ $? -eq 2 ] && { echo "[run_e7h] E7H_ONLY is not a valid extended regex: '$E7H_ONLY'" >&2; exit 2; }
fi
source "$(dirname "$0")/ms3_lib.sh"
B00_RE='^milp e3:milp:b=1:u=[0-9]+:mu=[0-9.]+:c=[0-9]+:part=b00$'

e7h_check_start() {   # 0 iff the part's gate lets it start (e7h --check-start in a 3G scope; its lines to the log)
  local -a MS3_PRE
  _ms3_prefix
  "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --check-start 2>&1 | tee -a "$MS3_LOG"
  return "${PIPESTATUS[0]}"
}

e7h_only() {          # keep the list lines that match E7H_ONLY (tests and smoke runs)
  [ -n "$E7H_ONLY" ] || return 0
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_all.txt"
  grep -E -- "$E7H_ONLY" "$MS3_OUT/jobs_list_all.txt" > "$MS3_OUT/jobs_list.txt"
  _ms3_log "E7H_ONLY='$E7H_ONLY': $(wc -l < "$MS3_OUT/jobs_list.txt") of $(wc -l < "$MS3_OUT/jobs_list_all.txt") jobs"
}

e7h_pass() {          # e7h_pass KIND REGEX [-v]: run the jobs of KIND whose list lines match REGEX (with -v: do not)
  local kind="$1" re="$2" inv="${3:-}"
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_full.txt"
  if [ "$inv" = "-v" ]; then
    grep -v -E "$re" "$MS3_OUT/jobs_list_full.txt" > "$MS3_OUT/jobs_list.txt"
  else
    grep -E "$re" "$MS3_OUT/jobs_list_full.txt" > "$MS3_OUT/jobs_list.txt"
  fi
  ms3_run_jobs "$kind"
  mv "$MS3_OUT/jobs_list_full.txt" "$MS3_OUT/jobs_list.txt"
}

e7h_retry() {         # the missing-run rule's rerun (§4.5): once per pool job
  local -a MS3_PRE
  _ms3_prefix
  if ! "${MS3_PRE[@]}" "$MS3_PY" -m "$MS3_MODULE" --retry-list --out "$MS3_OUT" > "$MS3_OUT/jobs_retry.txt" \
      2>> "$MS3_LOG"; then
    _ms3_log "could not list the jobs to rerun"
    return 0
  fi
  if [ -n "$E7H_ONLY" ]; then
    grep -E -- "$E7H_ONLY" "$MS3_OUT/jobs_retry.txt" > "$MS3_OUT/jobs_retry_only.txt" || true
    mv "$MS3_OUT/jobs_retry_only.txt" "$MS3_OUT/jobs_retry.txt"
  fi
  _ms3_log "rerun once (§4.5): $(grep -c '^pool ' "$MS3_OUT/jobs_retry.txt") pool job(s)"
  [ -s "$MS3_OUT/jobs_retry.txt" ] || return 0
  mv "$MS3_OUT/jobs_list.txt" "$MS3_OUT/jobs_list_full.txt"
  cp "$MS3_OUT/jobs_retry.txt" "$MS3_OUT/jobs_list.txt"
  ms3_run_jobs pool
  mv "$MS3_OUT/jobs_list_full.txt" "$MS3_OUT/jobs_list.txt"
}

for part in $E7H_PARTS; do
  export E7H_PART="$part"
  case "$part" in
    p*) MS3_OUT="$MS3_ROOT/out/sublet_v2_pilot/$part" ;;
    *) MS3_OUT="$MS3_ROOT/out/sublet_v2/$part" ;;
  esac
  ms3_init e7h
  _ms3_log "part $part"
  if ! e7h_check_start; then
    _ms3_log "refused: part $part does not start (design/sublet_v2.md §4.3, §5)"
    exit 2
  fi
  ms3_list
  e7h_only
  ms3_manifest
  ms3_run_jobs pool
  ms3_run_jobs alone
  e7h_pass milp "$B00_RE" -v
  e7h_pass milp "$B00_RE"
  e7h_retry
  ms3_manifest
  ms3_summary
  ms3_finish
done
