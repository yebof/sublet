#!/usr/bin/env bash
# Regenerate the input tree tests/fixtures_figs_ms4/inputs/ of the MS4 figure, float and claims tests
# (design/sim_spec_ms4.md §0 item 7, §10; README in inputs/) from reduced runs of the MS4 drivers.
#
#   code/sim/tests/fixtures_figs_ms4/refresh_inputs.sh SCRATCH [--only EXP ...] [--no-run] [--no-copy]
#
# SCRATCH    a folder outside the repository (created if absent). Each experiment runs in its own fresh root
#            SCRATCH/<exp>/ (MS3_ROOT; refused if it exists), whose out/e11/summary.json is a copy of this
#            repository's code/sim/out/e11/summary.json, the stand-in that the slot semaphore needs
#            (ms3_common.max_workers), with MS3_WORKERS=1, in this order:
#              e3  sublet/experiments/run_e3.sh --reduced --gate, then run_e3.sh --reduced
#              e4  run_e4.sh --reduced      (MS3_MILP_LIMIT 10 s unless set)
#              e5  run_e5.sh --reduced
#              e7  run_e7.sh --reduced      (the four parts gap, stress, main, allow and table3.json)
#              e8  run_e8.sh --reduced      (reads the raw Azure 2024 and Mooncake traces under /mnt/data/datasets)
#            about 50 min in all on one worker; each script's console goes to SCRATCH/<exp>.console and its wall
#            time to SCRATCH/refresh.log.
# --only     run and copy only these experiments (e3, e4, e5, e7, e8; default all five)
# --no-run   copy from the roots SCRATCH/<exp>/ of an earlier run
# --no-copy  run only (inspect the roots before copying)
#
# The copy replaces inputs/code/sim/out/<exp>/ of each experiment with the files that the MS4 figure scripts,
# Table III's writer (figs/table3_e7.py) and the claims report (experiments/ms4_claims.py) read, under the names the
# drivers write them (no runs/, logs/ or tables.md):
#   e3/       summary.json, gate.json, manifest.json, jobs/*.json
#   e4/       summary.json, manifest.json, jobs/*.json, lb/eager/panel=P/c=C/{lp,lp_core,milp}.json
#   e5/       summary.json, manifest.json, jobs/*.json
#   e7/       table3.json; <part>/summary.json, <part>/manifest.json, <part>/jobs/*.json for main, stress, gap, allow
#   e8/       summary.json, manifest.json, jobs/*.json
# and then checks the tree (every JSON file parses, every summary, gate.json and table3.json has meta.reduced true,
# every listed job of each manifest has a record, and every record is 'ok' or, for a MILP job, wall_limit or
# oom_at_3G, whose LB is the LP under Q39's rule). It exits nonzero if a run script, a copy or a check fails.
# README.md is written by hand: update its commit line after a refresh. Run from anywhere; the run scripts start
# their own 3G scopes, and the check runs in one.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # code/sim/tests/fixtures_figs_ms4
SIM="$(cd "$HERE/../.." && pwd)"                            # code/sim
EXP_DIR="$SIM/sublet/experiments"
DEST="$HERE/inputs/code/sim/out"
PY="${MS3_PY:-$HOME/venv/bin/python}"
ALL=(e3 e4 e5 e7 e8)

usage() { echo "usage: $0 SCRATCH [--only EXP ...] [--no-run] [--no-copy]" >&2; exit 2; }
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
for e in "${ONLY[@]}"; do
  case " ${ALL[*]} " in *" $e "*) ;; *) echo "unknown experiment '$e' (${ALL[*]})" >&2; exit 2 ;; esac
done
mkdir -p "$SCRATCH"
SCRATCH="$(cd "$SCRATCH" && pwd)"
case "$SCRATCH/" in "$(cd "$SIM/../.." && pwd)/"*) echo "SCRATCH must lie outside the repository" >&2; exit 2 ;; esac
LOG="$SCRATCH/refresh.log"
STANDIN="$SIM/out/e11/summary.json"
log() { echo "[refresh_inputs] $*" | tee -a "$LOG"; }

run_script() {        # run_script EXP ARGS...: one run script under MS3_ROOT=SCRATCH/EXP, timed
  local exp="$1" t0 rc; shift
  t0=$SECONDS
  MS3_ROOT="$SCRATCH/$exp" MS3_WORKERS=1 bash "$EXP_DIR/run_$exp.sh" "$@" >> "$SCRATCH/$exp.console" 2>&1
  rc=$?
  log "$exp: run_$exp.sh $* exit $rc, $((SECONDS - t0)) s wall"
  return $rc
}

if [ "$RUN" = "1" ]; then
  [ -s "$STANDIN" ] || { log "no $STANDIN (the stand-in E11 summary)"; exit 1; }
  for exp in "${ONLY[@]}"; do
    if [ -e "$SCRATCH/$exp" ]; then log "$SCRATCH/$exp exists: use a fresh SCRATCH or remove it"; exit 1; fi
    mkdir -p "$SCRATCH/$exp/out/e11"
    cp "$STANDIN" "$SCRATCH/$exp/out/e11/summary.json"
    log "$exp: root $SCRATCH/$exp, start $(date -Is), commit $(git -C "$SIM" rev-parse HEAD)"
    if [ "$exp" = "e3" ]; then
      run_script e3 --reduced --gate || exit 1
    fi
    run_script "$exp" --reduced || exit 1
  done
fi

[ "$COPY" = "1" ] || exit 0

copy_folder() {       # copy_folder SRC DST: summary.json, gate.json, table3.json, manifest.json and jobs/*.json
  local src="$1" dst="$2" f
  mkdir -p "$dst"
  for f in summary.json gate.json manifest.json; do
    [ -f "$src/$f" ] && cp -p "$src/$f" "$dst/$f"
  done
  if [ -d "$src/jobs" ]; then
    mkdir -p "$dst/jobs"
    cp -p "$src"/jobs/*.json "$dst/jobs/"
  fi
}

for exp in "${ONLY[@]}"; do
  src="$SCRATCH/$exp/out/$exp"
  [ -d "$src" ] || { log "no $src: run first"; exit 1; }
  rm -rf "${DEST:?}/$exp"
  case "$exp" in
    e7)
      mkdir -p "$DEST/e7"
      cp -p "$src/table3.json" "$DEST/e7/table3.json" || exit 1
      for part in main stress gap allow; do copy_folder "$src/$part" "$DEST/e7/$part"; done ;;
    e4)
      copy_folder "$src" "$DEST/e4"
      (cd "$src" && find lb/eager -name '*.json' -print0 | xargs -0 -r cp -p --parents -t "$DEST/e4/") || exit 1 ;;
    *)
      copy_folder "$src" "$DEST/$exp" ;;
  esac
  log "$exp: copied to $DEST/$exp ($(find "$DEST/$exp" -type f | wc -l) files, $(du -sk "$DEST/$exp" | cut -f1) KB)"
done

# the check (in a 3G scope): every JSON file parses; every summary, gate.json and table3.json is reduced; every job
# listed in a manifest has a record, 'ok' unless Q39's rule applies; nothing of runs/ or logs/
(cd "$SIM" && systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 \
   PYTHONDONTWRITEBYTECODE=1 "$PY" - "$DEST" "${ONLY[@]}" <<'EOF'
import json, sys
from pathlib import Path
dest, exps = Path(sys.argv[1]), sys.argv[2:]
bad = []
for exp in exps:
    top = dest / exp
    for p in sorted(top.rglob("*")):
        if p.is_dir():
            if p.name in ("runs", "logs"):
                bad.append(f"{p}: a {p.name}/ folder")
            continue
        try:
            d = json.loads(p.read_text())
        except ValueError as e:
            bad.append(f"{p}: {e}")
            continue
        if p.name in ("summary.json", "gate.json", "table3.json"):
            if not (isinstance(d, dict) and isinstance(d.get("meta"), dict) and d["meta"].get("reduced") is True):
                bad.append(f"{p}: meta.reduced is not true")
        if p.name == "manifest.json":
            kind = {j["id"]: j["kind"] for j in d.get("jobs", [])}
            rec = {}
            for q in (p.parent / "jobs").glob("*.json"):
                r = json.loads(q.read_text())
                rec[r.get("job")] = r.get("status")
            miss = [j for j in kind if j not in rec]
            # a job record that is not 'ok', except a MILP job whose output is a lower bound (E3's MILPs, E4's
            # OPT_eager; not E4's P-hat day plans) and whose LB is then its LP (Q39's rule, MS3 spec §2.5;
            # ms4_claims.LB_MILP_PREFIXES)
            not_ok = [j for j, s in rec.items() if s != "ok" and not (
                kind.get(j) == "milp" and str(j).startswith(("e3:milp:", "e4:eager:")) and s in
                ("wall_limit", "oom_at_3G"))]
            by = {}
            for s in rec.values():
                by[s] = by.get(s, 0) + 1
            print(f"check: {p.parent.relative_to(dest)}: {len(kind)} listed jobs, records by status {by}")
            if miss:
                bad.append(f"{p}: {len(miss)} listed job(s) without a record, e.g. {miss[0]}")
            if not_ok:
                bad.append(f"{p}: {len(not_ok)} record(s) not 'ok', e.g. {not_ok[0]} ({rec[not_ok[0]]})")
for b in bad:
    print("check:", b)
print(f"check: {'fail' if bad else 'pass'} ({', '.join(exps)})")
sys.exit(1 if bad else 0)
EOF
) 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}
log "tree $DEST: $(find "$DEST" -type f | wc -l) files, $(du -sk "$DEST" | cut -f1) KB"
exit "$rc"
