"""Calibrate reclaim-cost parameters (mu_A, mu_O, T_dr) and setup cost B from request traces.

Data-driven parts: request context/output lengths (Mooncake, Azure 2024), prefix reuse (Mooncake hash_ids).
Hardware numbers are ASSUMPTIONS (listed in ASSUME) and are swept, not measured.
"""
import json
import os

import numpy as np
import pandas as pd

from common import DATA, save_json

ASSUME = {
    "kv_bytes_per_token": {"llama3-8b": 2 * 32 * 8 * 128 * 2, "llama3-70b": 2 * 80 * 8 * 128 * 2,
                           "llama3.1-405b": 2 * 126 * 8 * 128 * 2},  # fp16, GQA 8 KV heads
    "weights_gb": {"llama3-8b": 16, "llama3-70b": 140, "llama3.1-405b": 810},
    "tpot_s": {"llama3-8b": 0.015, "llama3-70b": 0.035, "llama3.1-405b": 0.06},
    "prefill_tok_per_s_per_replica": {"llama3-8b": 40000, "llama3-70b": 12000, "llama3.1-405b": 4000},
    "concurrent_seqs_per_replica": 128,
    "replica_hbm_GB": {"llama3-8b": 80, "llama3-70b": 640, "llama3.1-405b": 1280},  # 1x / 8x / 16x H100-80G
    "wan_gbps": [1, 10, 25],
    "weight_load_gbps_GBps": [2, 10],  # remote object store vs local NVMe cache, GB/s
    "engine_init_s": 60,
}
BLOCK = 512  # Mooncake hash_id block size in tokens

out = {"assumptions": ASSUME}

# --- Mooncake: context length and prefix reuse ---
mc = {}
for name in ("conversation", "toolagent", "synthetic"):
    rows = [json.loads(l) for l in open(f"{DATA}/mooncake/{name}_trace.jsonl")]
    inp = np.array([r["input_length"] for r in rows])
    outp = np.array([r["output_length"] for r in rows])
    seen, hit, total = set(), 0, 0
    for r in rows:
        for h in r["hash_ids"]:
            total += 1
            hit += h in seen
            seen.add(h)
    mc[name] = {"n": len(rows), "input_p50_90_99": np.percentile(inp, [50, 90, 99]).tolist(),
                "output_p50_90_99": np.percentile(outp, [50, 90, 99]).tolist(),
                "prefix_block_hit_ratio_infinite_cache": hit / total,
                "unique_prefix_tokens_GB_llama70b": len(seen) * BLOCK * ASSUME["kv_bytes_per_token"]["llama3-70b"] / 1e9}
out["mooncake"] = mc

# --- in-flight state at the moment of reclaim (length-biased sampling of active requests) ---
src = None
for f in (f"{DATA}/azure-llm-2024/AzureLLMInferenceTrace_conv_1week.csv",
          f"{DATA}/azure-llm-2024/AzureLLMInferenceTrace_code_1week.csv"):
    if os.path.exists(f + ".done"):
        src = f
        break
if src:
    df = pd.read_csv(src, usecols=["ContextTokens", "GeneratedTokens"], nrows=2_000_000)
    ctx, gen = df.ContextTokens.values, np.maximum(df.GeneratedTokens.values, 1)
else:  # fall back to Mooncake conversation
    rows = [json.loads(l) for l in open(f"{DATA}/mooncake/conversation_trace.jsonl")]
    ctx = np.array([r["input_length"] for r in rows]); gen = np.maximum([r["output_length"] for r in rows], 1)
out["inflight_source"] = os.path.basename(src) if src else "mooncake_conversation"

rng = np.random.default_rng(0)
# an active request is sampled with probability proportional to its decode duration (= gen tokens)
i = rng.choice(len(gen), size=200000, p=gen / gen.sum())
done = (rng.random(len(i)) * gen[i]).astype(int)  # tokens already generated
remain = gen[i] - done
kv_tokens = ctx[i] + done

cal = {}
for m in ASSUME["weights_gb"]:
    bpt = ASSUME["kv_bytes_per_token"][m]
    n = ASSUME["concurrent_seqs_per_replica"]
    drain_s = remain * ASSUME["tpot_s"][m]                  # finish in place (needs notice >= drain)
    kv_cap = 0.9 * ASSUME["replica_hbm_GB"][m] - ASSUME["weights_gb"][m]
    kv_gb_replica = min(n * kv_tokens.mean() * bpt / 1e9, kv_cap)  # state to move if migrating everything
    mig = {str(g): kv_gb_replica * 8 / g for g in ASSUME["wan_gbps"]}  # seconds over WAN
    recompute_s = kv_gb_replica * 1e9 / bpt / ASSUME["prefill_tok_per_s_per_replica"][m]
    setup = {str(b): ASSUME["weights_gb"][m] / b + ASSUME["engine_init_s"] for b in ASSUME["weight_load_gbps_GBps"]}
    cal[m] = {
        "drain_time_s_p50_90_99": np.percentile(drain_s, [50, 90, 99]).tolist(),
        "T_dr_s (p99 drain)": float(np.percentile(drain_s, 99)),
        "kv_GB_inflight_per_replica": kv_gb_replica,
        "kv_migration_s_by_wan_gbps": mig,
        "recompute_s_per_replica": recompute_s,
        "setup_s_by_load_GBps": setup,
        # reclaim cost with no notice, in replica-seconds of service lost: min(migrate@10G, recompute)
        "mu_noNotice_over_Bsetup": min(mig["10"], recompute_s) / setup["2"],
    }
out["calibration"] = cal
save_json("a5_reclaim_cost_calibration.json", out)
for m, c in cal.items():
    print(m, {k: (round(v, 1) if isinstance(v, float) else v) for k, v in c.items() if not isinstance(v, (dict, list))})
