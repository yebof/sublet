"""a13: the Section II numbers that are medians or ranges over clusters, pools and lease sizes, each under one key.

Design: design/ms6_spec.md §6 II and unit D0 (inventory design/ms6/inventory_sec2_sec3.md §3.2, §3.3, §8 item 1,
Q8). The paper's value registry (paper/values/lending.json) needs one file and key per number; the per-cluster
outputs of a2 and a9 give the MaaS rows of design Table 1.3 only as medians over their 20 cluster entries, and the
ranges of rows L2-L5 and L7 as minima and maxima over lease sizes, leads and pools. This step computes them from the
versioned outputs, reads no raw trace, and writes out/a13_section2.json. Cheap (a few MB of JSON, under a second).

Inputs (out/): a1_lender_spotgpu.json (spot GPU pools), a2_lender_maas.json (MaaS clusters), a9_notice_buffer.json
(notice buffers per lender). Medians are statistics.median (the mean of the two middle values for an even count, as
numpy.median, which the design's recomputations used). Pool sets: row L2 uses the spot pools A100, H800 and
GPU-series-2 (the set of design Table 1.3 rows L2 and L8; A10 and series-1 share machines and are left out, and
A800's windows would change L2's range); rows L3 and L7 use A100, H800, A800 and GPU-series-2 (Fig. 2(a)). L3 used
the three pools of L2 until review D5 (finding N6): A800's reclaims (1.20 to 1.94 per day) lie inside the range of
the other three, so the four pools give the same minimum and maximum and the paper drops the "3 of the 4" qualifier.

Run: ~/venv/bin/python a13_paper_extract.py (from code/analysis/; run_all.sh runs it last).
"""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SIZES = ("p10", "p25", "p50")
LEADS_L5 = ("15", "30", "60", "120")          # "15-120 min ahead" (design Table 1.3 row L5)
SPOT_L2_L3 = ("A100-SXM4-80GB", "H800", "GPU-series-2")
SPOT_L7 = ("A100-SXM4-80GB", "H800", "A800-SXM4-80GB", "GPU-series-2")
WINDOWS_L7 = ("5", "15", "30", "60", "120", "240")


def load(name):
    with open(OUT / name, encoding="utf-8") as fh:
        return json.load(fh)


def sha256(name):
    return hashlib.sha256((OUT / name).read_bytes()).hexdigest()


def rng(values):
    v = list(values)
    return {"min": min(v), "max": max(v), "n": len(v)}


def main() -> int:
    a1 = load("a1_lender_spotgpu.json")
    a2 = load("a2_lender_maas.json")
    a9 = load("a9_notice_buffer.json")
    clusters = sorted(k for k in a2 if k.startswith("cluster_"))
    assert len(clusters) == 20, len(clusters)
    C = [a2[k] for k in clusters]
    med = statistics.median

    # L1: diurnal peak/trough of the online allocation and of the GPUs in use; a2's biased SM field
    used = [c["online_used_diurnal"]["peak_to_trough"] for c in C]
    used_nz = [u for u in used if u > 0]
    L1 = {
        "maas_alloc_peak_to_trough_median": med(c["online_alloc_diurnal"]["peak_to_trough"] for c in C),
        "maas_used_peak_to_trough_median_nonzero": med(used_nz),
        "n_used_nonzero": len(used_nz),
        "maas_sm_util_of_alloc_median": med(c["online_sm_util_of_alloc"] for c in C),
        "n_clusters": len(C),
    }

    # L2: share of lendable time in windows >= 60 and >= 360 min; median window (quantile index 2)
    L2m = {}
    for s in SIZES:
        L2m[s] = {
            "share_ge_60_median": med(c["leases"][s]["window"]["share_of_available_time_in_windows_ge"]["60"] for c in C),
            "share_ge_360_median": med(c["leases"][s]["window"]["share_of_available_time_in_windows_ge"]["360"] for c in C),
            "window_p50_min_median": med(c["leases"][s]["window"]["window_min_quantiles_p10_25_50_75_90"][2] for c in C),
        }
    sw = [a1[p]["leases"][s]["window"] for p in SPOT_L2_L3 for s in SIZES]
    L2 = {
        "maas": L2m,
        "maas_range": {k: rng(L2m[s][k] for s in SIZES) for k in L2m["p10"]},
        "spot": {
            "pools": list(SPOT_L2_L3),
            "share_ge_60": rng(w["share_of_available_time_in_windows_ge"]["60"] for w in sw),
            "share_ge_360": rng(w["share_of_available_time_in_windows_ge"]["360"] for w in sw),
            "window_p50_min": rng(w["window_min_quantiles_p10_25_50_75_90"][2] for w in sw),
        },
    }

    # L3: reclaims per day
    L3m = {s: med(c["leases"][s]["window"]["reclaims_per_day"] for c in C) for s in SIZES}
    L3 = {
        "maas_median": L3m,
        "maas_range": rng(L3m.values()),
        "spot": {"pools": list(SPOT_L7), **rng(a1[p]["leases"][s]["window"]["reclaims_per_day"]
                                                for p in SPOT_L7 for s in SIZES)},
    }

    # L4: length-biased residual life of a lease started at a random lendable slot (P10 and median, minutes)
    L4m = {s: {"residual_p10_min_median": med(c["leases"][s]["residual"]["residual_min_quantiles_p10_25_50_75_90"][0]
                                                for c in C),
               "residual_p50_min_median": med(c["leases"][s]["residual"]["residual_min_quantiles_p10_25_50_75_90"][2]
                                                for c in C)} for s in SIZES}
    L4 = {"maas": L4m, "maas_range": {k: rng(L4m[s][k] for s in SIZES) for k in L4m["p10"]}}

    # L5: daily-cycle predictor with level correction, recall and precision 15-120 min ahead
    L5m = {s: {ld: {"recall_median": med(c["leases"][s]["predictability"][ld]["seasonal_level"]["recall"] for c in C),
                    "precision_median": med(c["leases"][s]["predictability"][ld]["seasonal_level"]["precision"]
                                            for c in C)}
               for ld in LEADS_L5} for s in SIZES}
    L5 = {
        "leads_min": [int(x) for x in LEADS_L5],
        "maas": L5m,
        "maas_range": {k: rng(L5m[s][ld][k + "_median"] for s in SIZES for ld in LEADS_L5)
                       for k in ("recall", "precision")},
    }

    # L7: P99 notice buffer as a share of mean lendable capacity (a9)
    maas_keys = sorted(k for k in a9 if k.startswith("a2:"))
    assert len(maas_keys) == 20, len(maas_keys)
    L7 = {"maas_p99_median": {}, "maas_p99_max": {}, "spot_pools": list(SPOT_L7), "spot_p99_range": {}}
    for h in WINDOWS_L7:
        vals = {k.split(":", 1)[1]: a9[k][h]["p99"] for k in maas_keys}
        worst = max(vals, key=vals.get)
        L7["maas_p99_median"][h] = med(vals.values())
        L7["maas_p99_max"][h] = {"value": vals[worst], "cluster": worst}
        L7["spot_p99_range"][h] = rng(a9["a1:" + p][h]["p99"] for p in SPOT_L7)

    inputs = ("a1_lender_spotgpu.json", "a2_lender_maas.json", "a9_notice_buffer.json")
    doc = {
        "_meta": {
            "script": "code/analysis/a13_paper_extract.py",
            "purpose": "Section II numbers that are medians or ranges over clusters, pools, sizes and leads "
                       "(design/ms6_spec.md §6 II; design/ms6/inventory_sec2_sec3.md Q8)",
            "inputs_sha256": {f"code/analysis/out/{n}": sha256(n) for n in inputs},
            "median": "statistics.median (mean of the two middle values for an even count)",
            "units": "shares in [0, 1] (or of mean lendable capacity for L7), minutes for windows and residuals, "
                     "reclaims per day for L3",
        },
        "L1": L1, "L2": L2, "L3": L3, "L4": L4, "L5": L5, "L7": L7,
    }
    (OUT / "a13_section2.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")

    # The design's rounded values (design Table 1.3; inventory_sec2_sec3 §3.2-§3.3), as a check of the recomputation
    checks = [
        ("L1 alloc peak/trough", L1["maas_alloc_peak_to_trough_median"], 1.03, 2),
        ("L1 used peak/trough", L1["maas_used_peak_to_trough_median_nonzero"], 2.09, 2),
        ("L1 a2 SM field", L1["maas_sm_util_of_alloc_median"], 0.177, 3),
        ("L2 MaaS >=60 min", L2["maas_range"]["share_ge_60_median"]["min"], 0.94, 2),
        ("L2 MaaS >=60 max", L2["maas_range"]["share_ge_60_median"]["max"], 0.98, 2),
        ("L2 MaaS >=6 h min", L2["maas_range"]["share_ge_360_median"]["min"], 0.81, 2),
        ("L2 MaaS >=6 h max", L2["maas_range"]["share_ge_360_median"]["max"], 0.89, 2),
        ("L2 MaaS window min", L2["maas_range"]["window_p50_min_median"]["min"], 27.5, 1),
        ("L2 MaaS window max", L2["maas_range"]["window_p50_min_median"]["max"], 47.5, 1),
        ("L2 spot >=60 min", L2["spot"]["share_ge_60"]["min"], 0.95, 2),
        ("L2 spot >=60 max", L2["spot"]["share_ge_60"]["max"], 0.99, 2),
        ("L2 spot >=6 h min", L2["spot"]["share_ge_360"]["min"], 0.84, 2),
        ("L2 spot >=6 h max", L2["spot"]["share_ge_360"]["max"], 0.98, 2),
        ("L2 spot window min", L2["spot"]["window_p50_min"]["min"], 15, 0),
        ("L2 spot window max", L2["spot"]["window_p50_min"]["max"], 25, 0),
        ("L3 MaaS min", L3["maas_range"]["min"], 2.1, 1),
        ("L3 MaaS max", L3["maas_range"]["max"], 3.6, 1),
        ("L3 spot min", L3["spot"]["min"], 1.2, 1),
        ("L3 spot max", L3["spot"]["max"], 3.5, 1),
        ("L4 P10 min", L4["maas_range"]["residual_p10_min_median"]["min"], 20, 0),
        ("L4 P10 max", L4["maas_range"]["residual_p10_min_median"]["max"], 67.5, 1),
        ("L4 median min", L4["maas_range"]["residual_p50_min_median"]["min"], 265, 0),
        ("L4 median max", L4["maas_range"]["residual_p50_min_median"]["max"], 672.5, 1),
        ("L5 recall min", L5["maas_range"]["recall"]["min"], 0.27, 2),
        ("L5 recall max", L5["maas_range"]["recall"]["max"], 0.48, 2),
        ("L5 precision min", L5["maas_range"]["precision"]["min"], 0.11, 2),
        ("L5 precision max", L5["maas_range"]["precision"]["max"], 0.28, 2),
        ("L7 MaaS 5 min", L7["maas_p99_median"]["5"], 0.004, 3),
        ("L7 MaaS 30 min", L7["maas_p99_median"]["30"], 0.013, 3),
        ("L7 MaaS 240 min", L7["maas_p99_median"]["240"], 0.031, 3),
        ("L7 MaaS worst 240 min", L7["maas_p99_max"]["240"]["value"], 0.237, 3),
        ("L7 spot 5 min min", L7["spot_p99_range"]["5"]["min"], 0.09, 2),
        ("L7 spot 5 min max", L7["spot_p99_range"]["5"]["max"], 0.53, 2),
        ("L7 spot 30 min min", L7["spot_p99_range"]["30"]["min"], 0.33, 2),
        ("L7 spot 30 min max", L7["spot_p99_range"]["30"]["max"], 0.83, 2),
        ("L7 spot 240 min min", L7["spot_p99_range"]["240"]["min"], 0.71, 2),
        ("L7 spot 240 min max", L7["spot_p99_range"]["240"]["max"], 1.66, 2),
    ]
    bad = 0
    for name, got, want, nd in checks:
        ok = round(got, nd) == round(want, nd)
        bad += not ok
        print(f"{'ok  ' if ok else 'DIFF'} {name}: {got!r} (design {want})")
    print(f"a13: wrote {OUT / 'a13_section2.json'}; {len(checks) - bad} of {len(checks)} design values reproduced")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
