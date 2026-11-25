#!/usr/bin/env bash
# Regenerate the input tree tests/fixtures_figs_ms5b/inputs/ of the MS5b figure, float and claims tests
# (design/sublet_v2.md §11, W13; README in inputs/) from reduced runs of the six confirmation parts of e7h.py and the
# analysis script on them.
#
#   code/sim/tests/fixtures_figs_ms5b/refresh_inputs.sh SCRATCH [--only PART ...] [--no-run] [--no-copy]
#
# SCRATCH    a folder outside the repository (created if absent). Each confirmation part runs in its own fresh root
#            SCRATCH/<part>/ (MS3_ROOT; refused if it exists), whose out/e11/summary.json is a copy of this
#            repository's code/sim/out/e11/summary.json, the stand-in that the slot semaphore needs
#            (ms3_common.max_workers), with MS3_WORKERS=1 unless set:
#              E7H_PART=<part> MS3_ROOT=SCRATCH/<part> sublet/experiments/run_e7h.sh --reduced
#            for the parts main, seeds, second, e3, fam and grid (development cells only, a 2-hour horizon for the
#            week runs; e7h.py's docstring). A reduced run records the confirmation gate in its summary and run files
#            without enforcing it, so the parts run from a working tree that is not clean. PARTS_AT_ONCE parts run at
#            a time (default 1); each root has its own slot semaphore, so at most PARTS_AT_ONCE x MS3_WORKERS jobs
#            run at once (each in its 3G scope). About 38 min serially at MS3_WORKERS=2. Each part's console goes to
#            SCRATCH/<part>.console and its wall time to SCRATCH/refresh.log.
#            Then SCRATCH/merged/out/sublet_v2/<part> is a symbolic link to each part's folder of SCRATCH, and
#              python -m sublet.experiments.ms5b_analysis --root SCRATCH/merged
#            writes SCRATCH/merged/out/sublet_v2/analysis.json and analysis.md (in a 3G scope).
# --only     run and copy only these parts (main, seeds, second, e3, fam, grid; default all six); the analysis runs
#            on every part found in SCRATCH, and its outputs are copied in every case
# --no-run   copy from the roots SCRATCH/<part>/ of an earlier run (a root may be a symbolic link to one)
# --no-copy  run only (inspect the roots before copying)
#
# The copy replaces inputs/code/sim/out/sublet_v2/<part>/ with the files that the MS5b figure, float and claims
# scripts read, under the names the driver writes them: summary.json, manifest.json, jobs/*.json, lb/ (the bound files
# of parts e3 and grid, versioned like the summaries), tables.md (when at most TABLES_MAX_KB, default 200) and runs/
# with its subfolders (every part's runs/ when all of them together are at most RUNS_MAX_KB, default 3072; otherwise
# main's and second's only, which hold the cost components, the total accounting, BL0b and the own capacity of
# design/sublet_v2.md §11 W10); and inputs/code/sim/out/sublet_v2/ with analysis.json and analysis.md. No logs/,
# retry/, job lists or run logs. Then it checks the tree: every JSON file parses; every part's
# summary has meta.reduced true and its own part name; every job listed in a manifest has an 'ok' record; every
# run file parses and records the confirmation gate as not enforced; analysis.json holds H1-H6 and H2b. It exits
# nonzero if a run script, the analysis, a copy or a check fails. README.md is written by hand: update its commit
# line after a refresh, then refresh the fixture extracts (refresh_extracts.py). Run from anywhere; the run scripts
# start their own 3G scopes, and the analysis and the check run in one.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # code/sim/tests/fixtures_figs_ms5b
SIM="$(cd "$HERE/../.." && pwd)"                            # code/sim
REPO="$(cd "$SIM/../.." && pwd)"
EXP_DIR="$SIM/sublet/experiments"
DEST="$HERE/inputs"
PY="${MS3_PY:-$HOME/venv/bin/python}"
PARTS_AT_ONCE="${PARTS_AT_ONCE:-1}"
TABLES_MAX_KB="${TABLES_MAX_KB:-200}"
RUNS_MAX_KB="${RUNS_MAX_KB:-3072}"
ALL=(main seeds second e3 fam grid)
RUNS_FALLBACK=(main second)
SCOPE=(systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1)

usage() { echo "usage: $0 SCRATCH [--only PART ...] [--no-run] [--no-copy]" >&2; exit 2; }
[ $# -ge 1 ] || usage
SCRATCH="$1"; shift
RUN=1; COPY=1; ONLY=()
while [ $# -gt 0 ]; do
  case "$1" in
    --no-run) RUN=0 ;;
    --no-copy) COPY=0 ;;
    --only) shift
            while [ $# -gt 0 ] && [ "${1#--}" = "$1" ]; do ONLY+=("$1"); shift; done
            continue ;;
    *) usage ;;
  esac
  shift
done
[ ${#ONLY[@]} -gt 0 ] || ONLY=("${ALL[@]}")
for p in "${ONLY[@]}"; do
  case " ${ALL[*]} " in *" $p "*) ;; *) echo "unknown part '$p' (${ALL[*]})" >&2; exit 2 ;; esac
done
case "$PARTS_AT_ONCE" in ''|*[!0-9]*|0) echo "PARTS_AT_ONCE must be a positive integer" >&2; exit 2 ;; esac
mkdir -p "$SCRATCH"
SCRATCH="$(cd "$SCRATCH" && pwd)"
case "$SCRATCH/" in "$REPO/"*) echo "SCRATCH must lie outside the repository" >&2; exit 2 ;; esac
LOG="$SCRATCH/refresh.log"
STANDIN="$SIM/out/e11/summary.json"
log() { echo "[refresh_inputs ms5b] $*" | tee -a "$LOG"; }

run_part() {          # run_part PART: run_e7h.sh --reduced for one part under MS3_ROOT=SCRATCH/PART, timed
  local part="$1" t0 rc
  t0=$SECONDS
  E7H_PART="$part" MS3_ROOT="$SCRATCH/$part" MS3_WORKERS="${MS3_WORKERS:-1}" bash "$EXP_DIR/run_e7h.sh" --reduced \
    >> "$SCRATCH/$part.console" 2>&1
  rc=$?
  log "$part: E7H_PART=$part run_e7h.sh --reduced exit $rc, $((SECONDS - t0)) s wall"
  return $rc
}

if [ "$RUN" = "1" ]; then
  [ -s "$STANDIN" ] || { log "no $STANDIN (the stand-in E11 summary)"; exit 1; }
  for part in "${ONLY[@]}"; do
    if [ -e "$SCRATCH/$part" ]; then log "$SCRATCH/$part exists: use a fresh SCRATCH or remove it"; exit 1; fi
  done
  pids=(); names=(); failed=0
  for part in "${ONLY[@]}"; do
    mkdir -p "$SCRATCH/$part/out/e11"
    cp "$STANDIN" "$SCRATCH/$part/out/e11/summary.json"
    log "$part: root $SCRATCH/$part, start $(date -Is), commit $(git -C "$SIM" rev-parse HEAD)"
    run_part "$part" &
    pids+=("$!"); names+=("$part")
    if [ "${#pids[@]}" -ge "$PARTS_AT_ONCE" ]; then
      wait "${pids[0]}" || { log "${names[0]}: failed"; failed=1; }
      pids=("${pids[@]:1}"); names=("${names[@]:1}")
    fi
  done
  for i in "${!pids[@]}"; do
    wait "${pids[$i]}" || { log "${names[$i]}: failed"; failed=1; }
  done
  [ "$failed" = "0" ] || exit 1
fi

# the merged tree and the analysis: SCRATCH/merged/out/sublet_v2/<part> -> SCRATCH/<part>/out/sublet_v2/<part>
MERGED="$SCRATCH/merged"
rm -rf "$MERGED"
mkdir -p "$MERGED/out/sublet_v2"
found=()
for part in "${ALL[@]}"; do
  src="$SCRATCH/$part/out/sublet_v2/$part"
  if [ -f "$src/summary.json" ]; then
    ln -s "$(cd "$src" && pwd)" "$MERGED/out/sublet_v2/$part"
    found+=("$part")
  fi
done
log "analysis on the parts ${found[*]:-(none)}"
(cd "$SIM" && "${SCOPE[@]}" "$PY" -m sublet.experiments.ms5b_analysis --root "$MERGED") 2>&1 | tee -a "$LOG"
[ "${PIPESTATUS[0]}" = "0" ] || { log "the analysis failed"; exit 1; }

[ "$COPY" = "1" ] || exit 0

OUT="$DEST/code/sim/out/sublet_v2"
runs_kb=0
for part in "${ALL[@]}"; do
  d="$SCRATCH/$part/out/sublet_v2/$part/runs"
  [ -d "$d" ] && runs_kb=$((runs_kb + $(du -sk "$d" | cut -f1)))
done
if [ "$runs_kb" -le "$RUNS_MAX_KB" ]; then RUNS_OF=("${ALL[@]}"); else RUNS_OF=("${RUNS_FALLBACK[@]}"); fi
log "runs/ of every part found: $runs_kb KB (limit $RUNS_MAX_KB KB): copying the runs/ of ${RUNS_OF[*]}"

copy_part() {         # copy_part PART: the files listed above, from SCRATCH/PART/out/sublet_v2/PART
  local part="$1" src="$SCRATCH/$1/out/sublet_v2/$1" dst="$OUT/$1" f
  [ -f "$src/summary.json" ] || { log "no $src/summary.json: run first"; return 1; }
  rm -rf "${dst:?}"
  mkdir -p "$dst"
  for f in summary.json manifest.json; do
    [ -f "$src/$f" ] && cp -p "$src/$f" "$dst/$f"
  done
  if [ -f "$src/tables.md" ] && [ "$(du -sk "$src/tables.md" | cut -f1)" -le "$TABLES_MAX_KB" ]; then
    cp -p "$src/tables.md" "$dst/tables.md"
  fi
  if [ -d "$src/jobs" ]; then
    mkdir -p "$dst/jobs"
    cp -p "$src"/jobs/*.json "$dst/jobs/"
  fi
  [ -d "$src/lb" ] && cp -rp "$src/lb" "$dst/lb"
  case " ${RUNS_OF[*]} " in
    *" $part "*) [ -d "$src/runs" ] && cp -rp "$src/runs" "$dst/runs" ;;
  esac
  log "$part: copied to $dst ($(find "$dst" -type f | wc -l) files, $(du -sk "$dst" | cut -f1) KB)"
}

for part in "${ONLY[@]}"; do copy_part "$part" || exit 1; done
mkdir -p "$OUT"
for f in analysis.json analysis.md; do
  cp -p "$MERGED/out/sublet_v2/$f" "$OUT/$f" || { log "no $MERGED/out/sublet_v2/$f"; exit 1; }
done

# the check (in a 3G scope): every JSON parses; every part summary is reduced and names its part; every job listed in
# a manifest has an 'ok' record; every run file records the confirmation gate as not enforced; the analysis holds
# every hypothesis
(cd "$SIM" && "${SCOPE[@]}" "$PY" - "$DEST" <<'EOF'
import json, sys
from pathlib import Path
dest = Path(sys.argv[1])
out = dest / "code/sim/out/sublet_v2"
bad = []
docs = {}
for p in sorted(dest.rglob("*.json")):
    try:
        docs[p] = json.loads(p.read_text())
    except ValueError as e:
        bad.append(f"{p}: {e}")
for p, d in docs.items():
    rel = p.relative_to(out).as_posix() if out in p.parents else ""
    part = rel.split("/", 1)[0]
    if p.name == "summary.json" and p.parent.parent == out:
        meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
        if meta.get("reduced") is not True:
            bad.append(f"{p}: meta.reduced is not true")
        if meta.get("part") != part:
            bad.append(f"{p}: meta.part {meta.get('part')!r} is not {part!r}")
        g = meta.get("confirmation_gate") or {}
        print(f"check: {part}: {meta.get('n_runs')} runs, {meta.get('n_missing')} missing, {meta.get('jobs_ok')} of "
              f"{meta.get('jobs')} jobs with an output; confirmation gate ok {g.get('ok')} (recorded): "
              f"{g.get('reason')}")
    if p.name == "manifest.json":
        listed = [j["id"] for j in d.get("jobs", [])]
        rec = {}
        for q in (p.parent / "jobs").glob("*.json"):
            r = json.loads(q.read_text())
            rec[r.get("job")] = r.get("status")
        miss = [j for j in listed if j not in rec]
        not_ok = [j for j in listed if j in rec and rec[j] != "ok"]
        print(f"check: {p.parent.relative_to(dest)}: {len(listed)} listed jobs, {len(rec)} records")
        if miss:
            bad.append(f"{p}: {len(miss)} listed job(s) without a record, e.g. {miss[0]}")
        if not_ok:
            bad.append(f"{p}: {len(not_ok)} record(s) not 'ok', e.g. {not_ok[0]} ({rec[not_ok[0]]})")
    if "runs" in p.relative_to(dest).parts:
        g = (d.get("meta") or {}).get("gate") if isinstance(d.get("meta"), dict) else None
        if not (isinstance(g, dict) and g.get("kind") == "confirmation" and g.get("enforced") is False):
            bad.append(f"{p}: meta.gate is not a confirmation gate recorded as not enforced: {g}")
an = docs.get(out / "analysis.json")
if not isinstance(an, dict):
    bad.append(f"{out / 'analysis.json'}: missing")
else:
    hs = ("H1", "H2", "H2b", "H3", "H4", "H5", "H6")
    gone = [h for h in hs if not isinstance(an.get(h), dict)]
    if gone:
        bad.append(f"analysis.json: no {gone}")
    print("check: analysis " + ", ".join(f"{h} {(an.get(h) or {}).get('pass')}" for h in hs))
n_runs = sum(1 for p in docs if "runs" in p.relative_to(dest).parts)
print(f"check: {n_runs} run files")
for b in bad:
    print("check:", b)
print(f"check: {'fail' if bad else 'pass'}")
sys.exit(1 if bad else 0)
EOF
) 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}
log "tree $DEST: $(find "$DEST" -type f | wc -l) files, $(du -sk "$DEST" | cut -f1) KB"
exit "$rc"
