#!/usr/bin/env bash
# Regenerate the input tree tests/fixtures_figs_ms5/inputs/ of the MS5 figure tests (design/sim_spec_ms5.md §0
# item 7, §10; README in inputs/) from reduced runs of the MS5 drivers and from versioned analysis outputs.
#
#   code/sim/tests/fixtures_figs_ms5/refresh_inputs.sh SCRATCH [--only EXP ...] [--no-run] [--no-copy]
#
# SCRATCH    a folder outside the repository (created if absent). Each experiment runs in its own fresh root
#            SCRATCH/<exp>/ (MS3_ROOT; refused if it exists), whose out/e11/summary.json is a copy of this
#            repository's code/sim/out/e11/summary.json, the stand-in that the slot semaphore needs
#            (ms3_common.max_workers), with MS3_WORKERS=1 unless set, in this order:
#              s1     sublet/experiments/run_s1.sh --reduced   (parts sweep and q28; about 15 min on one worker)
#              e9     sublet/experiments/run_e9.sh --reduced   (every job alone; about 25 min)
#              slack  no run: the versioned code/analysis/out/a1_lender_spotgpu.json, the first SLACK_SLOTS slots
#                     (default 4032, two weeks of 5-min slots) of each pool of code/analysis/out/a1_slack_series.npz,
#                     written as an npz with fixed zip timestamps, so that the tree and its sha256 are reproducible,
#                     and a trimmed code/analysis/out/a9b_notice_buffer_24h.json with the keys sf_slack reads: its
#                     meta.slot_min and, per a1 pool, the source and n_slots, set to the slice's length (and a note)
#            each script's console goes to SCRATCH/<exp>.console and its wall time to SCRATCH/refresh.log.
# --only     run and copy only these experiments (s1, e9, slack; default all three)
# --no-run   copy from the roots SCRATCH/<exp>/ of an earlier run (a root may be a symbolic link to one)
# --no-copy  run only (inspect the roots before copying)
#
# The copy replaces inputs/code/sim/out/<folder>/ with the files that the MS5 figure scripts (and the claims report's
# tests) read, under the names the drivers write them (no runs/, logs/, tables.md, job lists or run logs):
#   s1/sweep/, s1/q28/   summary.json, manifest.json, jobs/*.json
#   e9/                  summary.json, manifest.json, jobs/*.json
#   e7/main/             summary.json, a copy of this repository's versioned E7 summary, which S1's mu row and
#                        sf_s1's s1_points.tex read (the reduced sweep summary records its sha256, checked below)
#   code/analysis/out/   a1_lender_spotgpu.json (a copy), a1_slack_series.npz (the slice above) and
#                        a9b_notice_buffer_24h.json (trimmed, above)
# and then checks the tree (every JSON file parses, every S1 and E9 summary has meta.reduced true, every listed job of
# each manifest has an 'ok' record, the E7 copy has the sha256 that the sweep summary records, and the npz slice
# holds the pools of the JSON). It exits nonzero if a run script, a copy or a check fails. README.md is written by
# hand: update its commit line after a refresh, then refresh the fixture extracts (refresh_extracts.py). Run from
# anywhere; the run scripts start their own 3G scopes, and the slice and the check run in one.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # code/sim/tests/fixtures_figs_ms5
SIM="$(cd "$HERE/../.." && pwd)"                            # code/sim
REPO="$(cd "$SIM/../.." && pwd)"
EXP_DIR="$SIM/sublet/experiments"
DEST="$HERE/inputs"
PY="${MS3_PY:-$HOME/venv/bin/python}"
SLACK_SLOTS="${SLACK_SLOTS:-4032}"
ALL=(s1 e9 slack)
SCOPE=(systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 env OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1)

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
case "$SCRATCH/" in "$REPO/"*) echo "SCRATCH must lie outside the repository" >&2; exit 2 ;; esac
LOG="$SCRATCH/refresh.log"
STANDIN="$SIM/out/e11/summary.json"
log() { echo "[refresh_inputs ms5] $*" | tee -a "$LOG"; }

run_script() {        # run_script EXP ARGS...: one run script under MS3_ROOT=SCRATCH/EXP, timed
  local exp="$1" t0 rc; shift
  t0=$SECONDS
  MS3_ROOT="$SCRATCH/$exp" MS3_WORKERS="${MS3_WORKERS:-1}" bash "$EXP_DIR/run_$exp.sh" "$@" \
    >> "$SCRATCH/$exp.console" 2>&1
  rc=$?
  log "$exp: run_$exp.sh $* exit $rc, $((SECONDS - t0)) s wall"
  return $rc
}

if [ "$RUN" = "1" ]; then
  [ -s "$STANDIN" ] || { log "no $STANDIN (the stand-in E11 summary)"; exit 1; }
  for exp in "${ONLY[@]}"; do
    [ "$exp" = "slack" ] && continue
    if [ -e "$SCRATCH/$exp" ]; then log "$SCRATCH/$exp exists: use a fresh SCRATCH or remove it"; exit 1; fi
    mkdir -p "$SCRATCH/$exp/out/e11"
    cp "$STANDIN" "$SCRATCH/$exp/out/e11/summary.json"
    log "$exp: root $SCRATCH/$exp, start $(date -Is), commit $(git -C "$SIM" rev-parse HEAD)"
    run_script "$exp" --reduced || exit 1
  done
fi

[ "$COPY" = "1" ] || exit 0

copy_folder() {       # copy_folder SRC DST: summary.json, manifest.json and jobs/*.json
  local src="$1" dst="$2" f
  [ -f "$src/summary.json" ] || { log "no $src/summary.json: run first"; return 1; }
  rm -rf "${dst:?}"
  mkdir -p "$dst"
  for f in summary.json manifest.json; do
    [ -f "$src/$f" ] && cp -p "$src/$f" "$dst/$f"
  done
  if [ -d "$src/jobs" ]; then
    mkdir -p "$dst/jobs"
    cp -p "$src"/jobs/*.json "$dst/jobs/"
  fi
}

OUT="$DEST/code/sim/out"
for exp in "${ONLY[@]}"; do
  case "$exp" in
    s1)
      for part in sweep q28; do copy_folder "$SCRATCH/s1/out/s1/$part" "$OUT/s1/$part" || exit 1; done
      mkdir -p "$OUT/e7/main"
      cp -p "$SIM/out/e7/main/summary.json" "$OUT/e7/main/summary.json" || exit 1
      log "s1: copied to $OUT/s1 ($(find "$OUT/s1" -type f | wc -l) files) and the E7 main summary" ;;
    e9)
      copy_folder "$SCRATCH/e9/out/e9" "$OUT/e9" || exit 1
      log "e9: copied to $OUT/e9 ($(find "$OUT/e9" -type f | wc -l) files)" ;;
    slack)
      mkdir -p "$DEST/code/analysis/out"
      cp -p "$REPO/code/analysis/out/a1_lender_spotgpu.json" "$DEST/code/analysis/out/a1_lender_spotgpu.json" || exit 1
      (cd "$SIM" && "${SCOPE[@]}" "$PY" - "$REPO/code/analysis/out/a1_slack_series.npz" \
         "$DEST/code/analysis/out/a1_slack_series.npz" "$SLACK_SLOTS" <<'EOF'
import io, sys, zipfile
import numpy as np
src, dst, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
with np.load(src) as z:
    pools = {k: np.asarray(z[k], dtype=float)[:n] for k in z.files}
with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zf:     # fixed timestamps: reproducible bytes
    for k, v in pools.items():
        buf = io.BytesIO()
        np.lib.format.write_array(buf, np.ascontiguousarray(v), allow_pickle=False)
        zf.writestr(zipfile.ZipInfo(f"{k}.npy", date_time=(1980, 1, 1, 0, 0, 0)), buf.getvalue(),
                    compress_type=zipfile.ZIP_DEFLATED)
print(f"slack: {dst}: the first {n} slots of {len(pools)} pools ({', '.join(pools)})")
EOF
      ) 2>&1 | tee -a "$LOG"
      [ "${PIPESTATUS[0]}" = "0" ] || exit 1
      (cd "$SIM" && "${SCOPE[@]}" "$PY" - "$REPO/code/analysis/out/a9b_notice_buffer_24h.json" \
         "$DEST/code/analysis/out/a9b_notice_buffer_24h.json" "$SLACK_SLOTS" <<'EOF'
import json, sys
src, dst, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
d = json.load(open(src))
out = {"meta": {"slot_min": d["meta"]["slot_min"],
                "note": "trimmed fixture copy for sf_slack (tests/fixtures_figs_ms5/refresh_inputs.sh): meta.slot_min "
                        "and, per a1 pool, source and n_slots, set to the length of this tree's a1_slack_series.npz "
                        "slice; not the analysis output"},
       "lenders": {k: {"source": v["source"], "n_slots": n} for k, v in d["lenders"].items() if k.startswith("a1:")}}
with open(dst, "w") as f:
    f.write(json.dumps(out, indent=1) + "\n")
print(f"slack: {dst}: meta.slot_min {out['meta']['slot_min']}, {len(out['lenders'])} a1 pools with n_slots {n}")
EOF
      ) 2>&1 | tee -a "$LOG"
      [ "${PIPESTATUS[0]}" = "0" ] || exit 1 ;;
  esac
done

# the check (in a 3G scope): every JSON file parses; every S1 and E9 summary is reduced; every job listed in a manifest
# has an 'ok' record; the E7 copy is the file the sweep summary names; the npz slice holds the JSON's pools
(cd "$SIM" && "${SCOPE[@]}" "$PY" - "$DEST" <<'EOF'
import hashlib, json, sys
from pathlib import Path
import numpy as np
dest = Path(sys.argv[1])
out = dest / "code/sim/out"
bad = []
for p in sorted(dest.rglob("*.json")):
    try:
        d = json.loads(p.read_text())
    except ValueError as e:
        bad.append(f"{p}: {e}")
        continue
    rel = p.relative_to(out).as_posix() if out in p.parents else ""
    if p.name == "summary.json" and rel.startswith(("s1/", "e9/")):
        if not (isinstance(d.get("meta"), dict) and d["meta"].get("reduced") is True):
            bad.append(f"{p}: meta.reduced is not true")
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
sweep = out / "s1/sweep/summary.json"
if sweep.is_file():
    e7 = json.loads(sweep.read_text())["meta"].get("e7_summary") or {}
    f = out / "e7/main/summary.json"
    got = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
    if got != e7.get("sha256"):
        bad.append(f"{f}: sha256 {got} is not the sweep summary's meta.e7_summary.sha256 {e7.get('sha256')}")
npz, js = dest / "code/analysis/out/a1_slack_series.npz", dest / "code/analysis/out/a1_lender_spotgpu.json"
if npz.is_file() and js.is_file():
    with np.load(npz) as z:
        pools = list(z.files)
    want = [k for k in json.loads(js.read_text()) if not k.startswith("_")]
    if sorted(pools) != sorted(want):
        bad.append(f"{npz}: pools {pools}, {js.name} {want}")
for b in bad:
    print("check:", b)
print(f"check: {'fail' if bad else 'pass'}")
sys.exit(1 if bad else 0)
EOF
) 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}
log "tree $DEST: $(find "$DEST" -type f | wc -l) files, $(du -sk "$DEST" | cut -f1) KB"
exit "$rc"
