#!/usr/bin/env python3
"""Watchdog of the MS7 e7r jobs (registration.md §6 deviation of 2026-11-09): every e7r job process that has run
longer than FACTOR times its registered estimate (est_s in its part's manifest.json, from
ms7_baselines.EST_RUN_S) is stopped with SIGTERM by PID, so that ms3_lib.sh records it 'failed' (exit 143).
Runs outside the clone; one line per stop (tab-separated, also JSON) in the log given as the first argument."""
import json
import os
import re
import signal
import subprocess
import sys
import time

FACTOR = 10.0
POLL_S = 30
CLONE = "/work/ms7_runs"
LOG = sys.argv[1]
RX = re.compile(r"-m sublet\.experiments\.e7r --job (\S+) --out (\S+)")
_est = {}


def est_s(out: str, jid: str):
    key = (out, jid)
    if key not in _est:
        try:
            m = json.load(open(os.path.join(out, "manifest.json")))
            for j in m.get("jobs") or []:
                _est[(out, j["id"])] = float(j["est_s"])
        except (OSError, ValueError, KeyError):
            return None
    return _est.get(key)


def log(rec: dict) -> None:
    with open(LOG, "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


stopped = {}
log({"event": "start", "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "factor": FACTOR, "clone": CLONE})
while True:
    ps = subprocess.run(["ps", "-eo", "pid=,etimes=,args="], capture_output=True, text=True).stdout
    for line in ps.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3 or "python" not in parts[2].split()[0]:
            continue
        m = RX.search(parts[2])
        if not m or not m.group(2).startswith(CLONE):
            continue
        pid, el = int(parts[0]), int(parts[1])
        jid, out = m.group(1), m.group(2)
        e = est_s(out, jid)
        if e is None or el <= FACTOR * e:
            continue
        if pid in stopped:
            if time.time() - stopped[pid] > 120:
                log({"event": "still_alive", "pid": pid, "job": jid, "elapsed_s": el})
                stopped[pid] = time.time()
            continue
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        stopped[pid] = time.time()
        log({"event": "stop", "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "pid": pid, "job": jid, "out": out,
             "elapsed_s": el, "est_s": e, "limit_s": FACTOR * e, "signal": "SIGTERM"})
    time.sleep(POLL_S)
