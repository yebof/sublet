# Sublet: Online LLM Replica Placement over Revocable GPU Leases

Code, tests and results for the paper "Sublet: Online LLM Replica Placement over Revocable GPU Leases".

LLM inference providers can lend idle GPUs under lease contracts $(\tau, H, \text{price})$: a guaranteed period $\tau$, after which the lender may reclaim the GPU with notice $H$. A platform that acts for many borrowers decides online which contracts to buy, where to keep warm replicas of open-weight LLMs, how much redundancy to hold, how to route requests and how to react to reclaim notices. Sublet is an online algorithm for this problem with worst-case guarantees against adversarial lenders. This repository holds the trace-driven simulator, the numerical checks of the theory, the trace analysis that calibrates the simulator, and the summary outputs of every experiment in the paper.

## Layout

| Path | Contents |
|---|---|
| `code/sim/` | The simulator, Python package `sublet`: engine, lender model, ledger and metrics (`sublet/`), the online algorithms including Sublet's guard (`sublet/algos/`), baselines (`sublet/baselines/`), offline bounds (`sublet/opt/`), the request-level replay (`sublet/replay/`), trace loaders, the experiment drivers and their frozen analysis scripts (`sublet/experiments/`), figure and table scripts (`figs/`), an independent audit of the guard (`audit/`), configs, memory benchmarks and the pytest suite (`tests/`). |
| `code/sim/out/` | Summary outputs of every experiment: per-experiment `summary.json`, the frozen analyses `analysis.json` and `analysis.md`, manifests, tables, claims reports and copy checks, and the figure extracts (`figs/`). |
| `code/theory_checks/` | Numerical checks of the competitive-ratio results: brute-force games, linear programs and exact-arithmetic checks, each folder with its own `run_all.sh` and outputs in `out/`. |
| `code/analysis/` | Trace analysis (`a1`–`a14`) that derives the simulator's inputs and calibration (lender slack, demand profiles, notice buffers, load times, prices), with derived outputs in `out/`. `run_all.sh` runs every step. |
| `code/data/` | `download_datasets.sh`, which fetches the public traces. |
| `design/` | The registrations of the confirmation and of the further runs (see below). |

## Requirements

- Python 3.12 with numpy 2.4, scipy 1.17, pandas 3.0, pyarrow 24, matplotlib 3.10, pytest 9 and PyMuPDF 1.27 (`requirements.txt`).
- A CPU machine; no GPU is needed. The experiments ran on one 12-thread server with 31 GB of memory; each job was capped at 3 GB (`systemd-run --user --scope -p MemoryMax=3G ...`).
- About 54 GB of disk for the raw traces.

## Data

The raw traces are not redistributed here; several have no redistribution license. `code/data/download_datasets.sh` fetches them into `/mnt/data/datasets` (the path is set in `code/analysis/common.py`). The traces and the papers that released them:

- Alibaba cluster-trace-v2026-maas (Zheng et al., "Model-as-a-Service in the Wild: Characterizing Production LLM Inference Clusters at Scale," USENIX ATC 2026).
- Alibaba cluster-trace-v2026-spot-gpu (Duan et al., "GFS: A Preemption-aware Scheduling Framework for GPU Clusters with Predictive Spot Instance Management," ASPLOS 2026).
- Alibaba cluster-trace-gpu-v2026 (Li et al., "Heterogeneity at Hyperscale: Characterization and Scheduling of Large Production AI Clusters at Alibaba," OSDI 2026) and cluster-trace-gpu-v2023 (Weng et al., "Beware of Fragmentation: Scheduling GPU-Sharing Workloads with Fragmentation Gradient Descent," USENIX ATC 2023).
- Azure LLM inference traces 2023 (Patel et al., "Splitwise," ISCA 2024) and 2024 (Stojkovic et al., "DynamoLLM," HPCA 2025).
- BurstGPT (Wang et al., KDD 2025).
- Mooncake FAST'25 traces (Qin et al., FAST 2025).
- WildChat-4.8M (Zhao et al., "WildChat," ICLR 2024).
- SkyPilot spot-traces (Wu et al., "Can't Be Late," NSDI 2024).

The derived inputs that the simulator reads are included in `code/analysis/out/`, so the simulator, the experiments and the quick suite run without the raw traces. Tests that read the raw traces carry the marker `needs_raw`.

## Running

The simulator runs from `code/sim`:

```bash
cd code/sim
# quick suite (about 1.7 h on one core)
python -m pytest -q -m "not needs_raw and not needs_ms2_checks and not needs_ms3_out and not needs_ms4_out and not needs_ms5_out and not needs_ms5b_out"
# trace analysis (needs the raw traces)
bash ../analysis/run_all.sh
# theory checks
bash ../theory_checks/c3/run_all.sh
```

Each experiment has a driver `sublet/experiments/<exp>.py` and a run script `run_<exp>.sh`; most drivers take `--reduced` for a short smoke run. The run scripts launch every job in its own memory-capped scope and write `code/sim/out/<exp>/`. The per-run files (`runs/`), the job records and the logs are not included in this repository. The figure scripts in `code/sim/figs/` redraw every figure from its JSON extract in `code/sim/out/figs/` (`--from-extract`).

Some tests and the frozen rebuild compare against the manuscript sources, which are not part of this repository; `code/sim/conftest.py` skips those tests here and lists them, with the reason, in `code/sim/tests/public_release_skips.json`.

## Registered analyses

The confirmation experiment and the further runs were registered before they ran. Each registration fixes the hypotheses or readings, the cells and the SHA-256 of the analysis script, and the drivers refuse to start unless the script on disk matches it:

- `design/sublet_v2_prereg.md`: the confirmation (hypotheses H1–H6 and H2b), analysis `code/sim/sublet/experiments/ms5b_analysis.py`;
- `design/ms7/registration.md`: the further runs X1–X5;
- `design/ms8/registration.md`: the runs X6 and X7.

These are public copies with process notes removed; every registered rule, parameter, cell and hash is unchanged. The `git_revision` and commit hashes recorded in the results refer to the authors' development repository, where the registrations were merged before the runs. Because the drivers' gates check that history, rerunning a registered part in a clone of this repository stops at its gate; the unregistered drivers and every `--reduced` run work as usual.

## Notes on the released results

- Local paths in the released files were replaced: run directories by `/work/...`, the Python environment by `/opt/venv`, the host name by `host`. The files changed are listed in `PUBLIC_RELEASE.md`; for those files the SHA-256 values recorded elsewhere in the results no longer match.
- Development measurements, prototypes and the pilot outputs are not included.

## License

MIT; see `LICENSE`. The traces keep their own licenses and terms of use.
