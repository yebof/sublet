"""Instance builder, client units, the policy's public view and the core export
(design/sim_spec.md §3.4.4, §4.3, §6.1-§6.2).

`build_instance(cfg)` resolves the config (`config.load_config`) and computes, in the order of
§4.3: grid, contracts and LLMs; lenders and sites (offered contracts, buffer, lendable slack,
layers and their merging); prices; trace alignment; load times; demand and clients; routing
costs; stranding parameters. Every random value was drawn by `load_config`, so the builder
itself draws nothing (explicit on/off demand uses its own `default_rng(seed)`).
`to_core` and `from_core` translate to and from `code/theory_checks/c3/core.py` (rule T12).

MS2 additions (design/sim_spec_ms2.md §2.4): `active_units` (C1); the derived instances
`restrict_clients`, `with_demand` and `restrict_horizon` (C2); `borrowers.merge` of the series
model (C3); `Instance.borrower_stats` from the regional and series models (C4).

MS3 addition (design/sim_spec_ms3.md §2.3, C10): with `costs.beta_jl_usd` an object {LLM id: USD},
`beta_usd[j, :]` is LLM j's fee and beta_tilde_ref_j (so mu_j = r_mu beta_tilde_ref_j) uses it.

MS4 addition (design/sim_spec_ms4.md §2.3, C24): with `borrowers.normalize` "mean" (series model),
`_series_model` divides each borrower's overflow (replica loads per minute, before Gamma) by its mean over
the horizon, so every borrower with overflow has mean 1 and the borrowers carry equal shares of the
demand, merged or not; Gamma is then solved on the sum as before. A borrower without overflow keeps
zero (its client, if alone, is dropped with the builder's note). Its borrower_stats entry records the
factor `normalize_factor` (None without overflow), and C0_loads and peak_loads are scaled by it.

MS7 addition (design/ms7/plan.md §3 X2, design/ms7/feasibility/oos.md §3 and §4 item 2; change C55), for the
out-of-sample folds: with a lender's calib_slots [lo, hi), `_trace_lender` takes the buffer curve, b, B = b x the
mean slack, the lease size v_top (the quantile of the lendable slack), the menu pruning of §10 S35 and the IR prices
from S_full[lo:hi] and replays the whole series at the offset as before (S, S_lend = (S_full - B)^+ and the owed
series of lender.py read the full series, so a held-out horizon's lead-in reads real past slack). `_regional` takes
the keys p_o_week, demand_fit and gamma (its docstring). Without them every step, every draw and every array is the
MS1-MS6 builder's, so every frozen instance and its hash are unchanged.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional, Union

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from . import calib, paths, reclaim
from .config import ConfigError, MIN_PER_WEEK, load_config
from .traces import borrowers as tb
from .traces import catalog as tc
from .traces import lenders as tl
from .types import (INF, LLM, Clients, Contract, Instance, InfoModel, LenderTrace, PublicView, Schedule, Site,
                    Stranding, TimeGrid, UnitTable)

SLACK_SLOT_MIN = calib.SLACK_SLOT_MIN


class InstanceError(ValueError):
    """Invalid instance."""


# ---------------------------------------------------------------- step 1: contracts and LLMs
def _contract(c: dict, slow: int, billing: str) -> Contract:
    if c["tau_min"] is None:
        return Contract(c["id"], None, 0, int(c["prepaid_min"]), c["klass"])
    tau, H = c["tau_min"], c["H_min"]
    P = {"prepaid_D": tau + H, "per_slot": 0, "commit_tau": tau}[billing]
    return Contract(c["id"], tau // slow, H, P, c["klass"])


def _llm(x: dict, q_gpu: float) -> LLM:
    if x["catalog"] == "explicit":
        g, w, tier = x["g"], x["w_GB"], x["tier"]
        kap = INF if x["kappa_wtok_per_min"] == "inf" else x["kappa_wtok_per_min"]
        w_in, T_dr = x["w_in"], x["T_dr_s"]
    else:
        e = tc.entry(x["catalog"], x["entry"])
        g, w, tier = e["g"], e["w_GB"], x["tier"]
        kap, w_in, T_dr = calib.kappa_wtok_per_min(tier), calib.w_in(tier), calib.T_dr_s(tier)
    return LLM(x["id"], tier, int(g), float(w), float(kap) * x["kappa_mult"], float(w_in), float(T_dr),
               g * q_gpu)


# ---------------------------------------------------------------- step 2: lenders and sites
@dataclass
class _LenderSites:
    """Sites and prices of one lender before they are put into the instance arrays."""
    trace: LenderTrace
    sites: list[Site]
    price: dict[int, float]       # contract index -> USD/GPU-h (same at every site of the lender)
    scenario: str
    lam: Union[None, float, dict]


def _protected_lenders(cfg: dict) -> list[dict]:
    p = cfg["protected_per_region"]
    if not p["enabled"]:
        return []
    return [{"id": f"prot:{o}", "kind": "protected", "series": None, "series_values": None, "region": o,
             "group": f"prot:{o}", "menu": p["menu"], "offset": 0, "load_scenario": p["load_scenario"],
             "lam_s": None, "capacity_gpus": p["capacity_gpus"], "prices": {}, "R": None, "R_rate": None}
            for o in cfg["regions"]["list"]]


def _price_of(e: dict, k: int, c: Contract, cfg: dict, b_of: dict) -> float:
    pr = cfg["prices"]
    if c.protected:
        return float(e["prices"].get(c.id, pr["a_protected_usd_per_gpu_h"]))
    if e["kind"] == "synthetic":
        return float(e["prices"][c.id])
    mode = pr["revocable_price"]
    if mode == "ir":
        return pr["a0_usd_per_gpu_h"] * calib._ir(b_of[k])
    if mode == "a0":
        return pr["a0_usd_per_gpu_h"]
    if mode == "multiplier":
        return pr["a0_usd_per_gpu_h"] * pr["multipliers"][c.id]
    return float(e["prices"][c.id])   # explicit


def _trace_lender(e: dict, cfg: dict, grid: TimeGrid, contracts: tuple[Contract, ...], notes: list[str],
                  merge: bool) -> Optional[_LenderSites]:
    lid, slow = e["id"], grid.slow_min
    S_full = tl.slack(e["series"]) if e["series"] is not None else np.asarray(e["series_values"], np.float64)
    # MS7 C55: the calibration window [lo, hi) of calib_slots (absent: the whole series, the MS1-MS6 builder)
    cs = e.get("calib_slots")
    S_cal = S_full if cs is None else S_full[int(cs[0]):int(cs[1])]
    q = cfg["prices"]["buffer_quantile"]
    cidx = {c.id: k for k, c in enumerate(contracts)}
    menu = sorted(cidx[k] for k in e["menu"])
    rev = [k for k in menu if not contracts[k].protected]
    prot = [k for k in menu if contracts[k].protected]
    D_l = {k: calib.D_lender_min(contracts[k].D_min(slow), slow) for k in rev}
    b_of, curve = {}, None
    if rev:
        try:
            curve = calib.buffer_curve(S_cal, max(D_l.values()))
        except ValueError as err:
            raise ConfigError(f"lender {lid}: {err}" + ("" if cs is None else f" (calib_slots {list(cs)})")) \
                from None
        b_of = {k: curve["env"][D_l[k]][q] for k in rev}
    off_rev = [k for k in rev if b_of[k] < 1]
    gone = [contracts[k].id for k in rev if b_of[k] >= 1]
    if gone:
        notes.append(f"lender {lid}: contracts {gone} removed from the menu (buffer b >= 1 at {q})")
    g_lay, V = e["layer_gpus"], e["n_layers"]

    def lendable(ks):
        """(D_max, b, B, S_lend over the whole series, v_top) for the offered revocable contracts ks; b, B = b x mean
        slack and the quantile of v_top on the calibration window (C55; the whole series without calib_slots)."""
        D = max(D_l[k] for k in ks) if ks else 0
        bb = float(curve["env"][D][q]) if ks else 0.0
        BB = bb * float(S_cal.mean())
        S_l = np.maximum(S_full - BB, 0.0)
        S_lc = S_l if cs is None else np.maximum(S_cal - BB, 0.0)
        return D, bb, BB, S_l, int(math.floor(np.percentile(S_lc, e["lease_size_quantile"]) / g_lay))

    D_max, b, B, S_lend_full, v_top = lendable(off_rev)
    # §10 S35: while v_top = 0, drop the offered contracts with the longest lender window D_max and
    # recompute the buffer, S_lend and v_top (a long window can leave nothing to lend at the quantile)
    while v_top == 0 and off_rev:
        cut = [k for k in off_rev if D_l[k] == D_max]
        off_rev = [k for k in off_rev if D_l[k] < D_max]
        notes.append(f"lender {lid}: contracts {[contracts[k].id for k in cut]} removed from the menu "
                     f"(v_top = 0 at D_max {D_max} min, quantile P{e['lease_size_quantile']}; §10 S35)")
        if not off_rev and not prot:
            break
        D_max, b, B, S_lend_full, v_top = lendable(off_rev)
    offered = sorted(off_rev + prot)
    if not offered:
        notes.append(f"lender {lid}: no offered contract, no site")
        return None
    if v_top == 0:
        notes.append(f"lender {lid}: v_top = 0 at quantile P{e['lease_size_quantile']} of the lendable slack, no site")
        return None
    v0, n_off = max(0, v_top - V), min(V, v_top)
    N = len(S_full)
    off = int(e["offset"]) % N
    idx = (off + (np.arange(grid.T_slow, dtype=np.int64) * slow) // SLACK_SLOT_MIN) % N
    S_h, S_lend_h = S_full[idx], S_lend_full[idx]
    R = [reclaim.layer_R(S_lend_h, (v0 + v) * g_lay) for v in range(1, n_off + 1)]
    blocks, lo = [], 1
    for v in range(2, n_off + 2):   # runs of consecutive layers with identical R
        if v == n_off + 1 or not merge or not np.array_equal(R[v - 1], R[v - 2]):
            blocks.append((lo, v - 1))
            lo = v
    sites = [Site(id=f"{lid}/L{v0 + a}-{v0 + z}", lender=lid, kind="layer", region=e["region"], group=e["group"],
                  capacity_gpus=float((z - a + 1) * g_lay), menu=tuple(offered), layer_lo=v0 + a, layer_hi=v0 + z,
                  local_layer_lo=a) for a, z in blocks]
    kind = tl.lender_kind(e["series"]) if e["series"] is not None else "spot"
    tr = LenderTrace(lender=lid, kind=kind, series=e["series"], S_full=S_full, S=S_h, B_gpus=B, S_lend=S_lend_h,
                     v0=v0, n_layers=n_off, layer_gpus=g_lay, D_max_lender_min=D_max, offset_5min=off, site_index=())
    price = {k: _price_of(e, k, contracts[k], cfg, b_of) for k in offered}
    notes.append(f"lender {lid}: D_max {D_max} min, buffer {B:.3f} GPUs (b = {b:.6f}), v_top {v_top}, v0 {v0}, "
                 f"{n_off} offered layers in {len(sites)} site(s)"
                 + ("" if cs is None else f"; calibrated on slots [{int(cs[0])}, {int(cs[1])}) (calib_slots, C55)"))
    return _LenderSites(tr, sites, price, e["load_scenario"], e["lam_s"])


def _single_site_lender(e: dict, cfg: dict, contracts: tuple[Contract, ...]) -> _LenderSites:
    cidx = {c.id: k for k, c in enumerate(contracts)}
    menu = tuple(sorted(cidx[k] for k in e["menu"]))
    cap = INF if e["capacity_gpus"] is None else float(e["capacity_gpus"])
    Rx = np.unique(np.asarray(e["R"], dtype=np.int64)) if e["kind"] == "synthetic" else None
    site = Site(id=e["id"], lender=e["id"], kind=e["kind"], region=e["region"], group=e["group"], capacity_gpus=cap,
                menu=menu, layer_lo=None, layer_hi=None, local_layer_lo=None, R_explicit=Rx)
    tr = LenderTrace(lender=e["id"], kind=e["kind"], series=None, S_full=None, S=None, B_gpus=0.0, S_lend=None,
                     v0=0, n_layers=0, layer_gpus=0, D_max_lender_min=0, offset_5min=0, site_index=())
    price = {k: _price_of(e, k, contracts[k], cfg, {}) for k in menu}
    return _LenderSites(tr, [site], price, e["load_scenario"], e["lam_s"])


# ---------------------------------------------------------------- step 7: demand
def _trailing_mean(x_ext: np.ndarray, w: int) -> np.ndarray:
    """Mean over the last w minutes; x_ext has w - 1 lead-in minutes before horizon minute 0."""
    return sliding_window_view(x_ext, w).mean(axis=1)


def _fast_mean(y: np.ndarray, fast: int) -> np.ndarray:
    return y.reshape(-1, fast).mean(axis=1)


def _overflow(x_ext: np.ndarray, b: dict, kappa: float) -> tuple[np.ndarray, float, float]:
    """Steps (d): trailing mean x^sm, own capacity C0 at the quantile, overflow in replica loads.
    Returns (overflow, C0, max x^sm), C0 and the peak in weighted tokens per minute (MS2 C4)."""
    xs = _trailing_mean(x_ext, b["smoothing_min"])
    C0 = np.percentile(xs, b["own_capacity_quantile"])
    return np.maximum(xs - C0, 0.0) / kappa, float(C0), float(xs.max())


def _stats(llm: int, C0: float, peak: float, gam: float, kappa: float) -> dict:
    """borrower_stats entry (MS2 C4): own capacity and peak in replica loads after the Gamma scaling."""
    return {"llm": int(llm), "C0_loads": gam * C0 / kappa, "peak_loads": gam * peak / kappa}


def _slo_lookup(m: Optional[dict], region: str, tier: str, default: str) -> str:
    if m:
        for k in (f"{region}:{tier}", region, tier):
            if k in m:
                return m[k]
    return default


def _gamma(ys: list[np.ndarray], gs: list[int], supply: float, tightness: float) -> float:
    if supply <= 0:
        raise ConfigError("borrowers: the market tightness needs layer sites (supply 0)")
    peak = float(np.max(sum(g * y for g, y in zip(gs, ys)))) if ys else 0.0
    if peak <= 0:
        raise ConfigError("borrowers: no overflow above the own capacity, so Gamma is undefined")
    return tightness * supply / peak


def _fit_overflow(x_ext: np.ndarray, x_fit: np.ndarray, b: dict, kappa: float) -> tuple:
    """C55 (borrowers.demand_fit): own capacity C0 at the quantile of the fit-period series' trailing mean, the
    evaluated overflow above it in replica loads, and the fit period's overflow (for Gamma without borrowers.gamma).
    Returns (overflow, C0, max(max x^sm, C0), fit overflow): the third is the borrower_stats peak, so that BL0b's
    peak - C0 is never negative for a borrower whose evaluated demand stays below the fitted C0."""
    y_fit, C0, _peak_fit = _overflow(x_fit, b, kappa)
    xs = _trailing_mean(x_ext, b["smoothing_min"])
    return np.maximum(xs - C0, 0.0) / kappa, float(C0), max(float(xs.max()), float(C0)), y_fit


def _regional(cfg: dict, grid: TimeGrid, llms: tuple[LLM, ...], supply: float, notes: list[str]):
    """The regional borrowers (design §5.3.3-§5.3.4). MS7 C55 (config.py's docstring): borrowers.p_o_week replaces
    the evaluated demand's profile by one calendar week's (traces.borrowers.wildchat_week); borrowers.demand_fit
    takes C0 (and, without gamma, Gamma's peak) from the fit-period demand share x p_o x xi of its sources, p_o of
    wildchat_model, over its own minutes (hw from its start_minute_of_week, with the same smoothing lead-in);
    borrowers.gamma pins Gamma. With demand_fit or gamma each borrower_stats entry also records 'gamma' and
    'C0_from' ('demand_fit' or 'horizon'). Without these keys every step is the MS1-MS6 builder's."""
    b, regs = cfg["borrowers"], cfg["regions"]["list"]
    p_o, r_oj = tb.wildchat(b["wildchat_model"])
    p_ev = p_o if b.get("p_o_week") is None else tb.wildchat_week(b["p_o_week"])     # C55
    fit, pinned = b.get("demand_fit"), b.get("gamma")
    tot = sum(r_oj[o].get(t, 0.0) for o in regs for t in ("M", "L"))
    sS = b["s_S"]
    rp = {o: {"M": (1 - sS) * r_oj[o].get("M", 0.0) / tot, "L": (1 - sS) * r_oj[o].get("L", 0.0) / tot,
              "S": sS * (r_oj[o].get("M", 0.0) + r_oj[o].get("L", 0.0)) / tot} for o in regs}
    sm, T_min = b["smoothing_min"], grid.horizon_min
    i = np.arange(-(sm - 1), T_min, dtype=np.int64)
    hw = ((grid.start_mow + i) // 60) % 168
    if fit is not None:
        i_f = np.arange(-(sm - 1), fit["horizon_min"], dtype=np.int64)
        hw_f = ((fit["start_minute_of_week"] + i_f) // 60) % 168
    cand = []   # (region, LLM index, overflow per minute, C0, peak of the smoothed series)
    fits = []   # C55: the fit period's overflow per candidate (demand_fit)
    for o in regs:
        src = b["xi_sources"][o]
        ser = tb.load_series(src["series"])
        N = len(ser.out)
        if fit is not None:
            fsrc = fit["xi_sources"][o]
            fser = tb.load_series(fsrc["series"])
            N_f = len(fser.out)
        for j, x in enumerate(llms):
            share = rp[o].get(x.tier, 0.0)
            if share <= 0:
                continue
            xi_h = tb.xi(tb.weighted(ser, x.w_in))[(src["offset_min"] + i) % N]
            if fit is None:
                cand.append((o, j, *_overflow(share * p_ev[o][hw] * xi_h, b, x.kappa_wtok_per_min)))
                continue
            xi_f = tb.xi(tb.weighted(fser, x.w_in))[(fsrc["offset_min"] + i_f) % N_f]
            y, C0, peak, y_f = _fit_overflow(share * p_ev[o][hw] * xi_h, share * p_o[o][hw_f] * xi_f, b,
                                             x.kappa_wtok_per_min)
            cand.append((o, j, y, C0, peak))
            fits.append(y_f)
    gs = [llms[j].g for _, j, _, _, _ in cand]
    if pinned is not None:
        gam, how = float(pinned), "borrowers.gamma, pinned"
    elif fit is not None:
        gam, how = _gamma(fits, gs, supply, b["market_tightness"]), "fit on borrowers.demand_fit"
    else:
        gam = _gamma([y for _, _, y, _, _ in cand], gs, supply, b["market_tightness"])
    if fit is None and pinned is None:
        notes.append(f"regional demand: Gamma = {gam:.6g} (tightness {b['market_tightness']}, supply {supply:g} GPUs)")
    else:
        notes.append(f"regional demand: Gamma = {gam:.6g} ({how}; tightness {b['market_tightness']}, supply "
                     f"{supply:g} GPUs; C0 from {'borrowers.demand_fit' if fit is not None else 'the horizon'})")
    out, stats = [], {}
    for o, j, y, C0, peak in cand:
        stats[f"wildchat:{o}:{llms[j].tier}"] = _stats(j, C0, peak, gam, llms[j].kappa_wtok_per_min)
        if fit is not None or pinned is not None:
            stats[f"wildchat:{o}:{llms[j].tier}"].update(gamma=gam, C0_from="horizon" if fit is None else "demand_fit")
        d = _fast_mean(gam * y, grid.fast_min)
        if d.max() <= 0:
            notes.append(f"client wildchat:{o}:{llms[j].tier} has no overflow and is dropped")
            continue
        slo = _slo_lookup(b["slo_class"], o, llms[j].tier, cfg["regions"]["default_slo_class"])
        out.append((j, o, slo, (f"wildchat:{o}:{llms[j].tier}",), d))
    return out, stats


def _series_model(cfg: dict, grid: TimeGrid, llms: tuple[LLM, ...], supply: float, notes: list[str]):
    b = cfg["borrowers"]
    sm, T_min = b["smoothing_min"], grid.horizon_min
    i = np.arange(-(sm - 1), T_min, dtype=np.int64)
    by_tier = {x.tier: j for j, x in enumerate(llms)}
    merge = b.get("merge", True)     # MS2 C3: false keeps one client per borrower
    norm = b.get("normalize", "none") == "mean"     # MS4 C24
    groups: dict[tuple, list] = {}
    own: dict[str, tuple] = {}       # borrower id -> (LLM, C0, peak of the smoothed series)
    factor: dict[str, Optional[float]] = {}     # MS4 C24: borrower id -> 1 / mean overflow (None: no overflow)
    for x in b["list"]:
        j = by_tier[x["tier"]]
        ser = tb.load_series(x["series"])
        w = tb.weighted(ser, llms[j].w_in)
        start = (x["week_index"] or 0) * MIN_PER_WEEK
        y, C0, peak = _overflow(w[(start + i) % len(w)], b, llms[j].kappa_wtok_per_min)
        if norm:
            m = float(y.mean())
            factor[x["id"]] = 1.0 / m if m > 0 else None
            if m > 0:
                y = y / m
        own[x["id"]] = (j, C0, peak)
        key = (x["tier"], x["region"], x["slo_class"]) + (() if merge else (x["id"],))
        groups.setdefault(key, [j, [], np.zeros(T_min)])
        groups[key][1].append(x["id"])
        groups[key][2] += y
    keys = list(groups)
    gam = _gamma([groups[k][2] for k in keys], [llms[groups[k][0]].g for k in keys], supply, b["market_tightness"])
    notes.append(f"series demand: Gamma = {gam:.6g} (tightness {b['market_tightness']}, supply {supply:g} GPUs)")
    stats = {bid: _stats(j, C0, peak, gam, llms[j].kappa_wtok_per_min) for bid, (j, C0, peak) in own.items()}
    if norm:
        for bid, f in factor.items():
            stats[bid]["normalize_factor"] = f
            if f is not None:
                stats[bid]["C0_loads"] *= f
                stats[bid]["peak_loads"] *= f
        notes.append(f"series demand normalized (borrowers.normalize 'mean'): every borrower's overflow scaled to "
                     f"mean 1; borrowers without overflow: {[bid for bid, f in factor.items() if f is None]}")
    out = []
    for key in keys:
        tier, reg, slo = key[:3]
        j, ids, y = groups[key]
        d = _fast_mean(gam * y, grid.fast_min)
        if d.max() <= 0:
            notes.append(f"client {ids} has no overflow and is dropped")
            continue
        out.append((j, reg, slo, tuple(ids), d))
    return out, stats


def onoff_demand(T_fast: int, fast_min: int, on_mean_min: float, off_mean_min: float, level: float,
                 seed: int) -> np.ndarray:
    """On/off demand per fast slot: the series starts off; off and on periods alternate, each of
    rng.geometric(1 / mean) fast slots (mean in fast slots), drawn off then on, rng = default_rng(seed)."""
    rng = np.random.default_rng(seed)
    p_on, p_off = fast_min / on_mean_min, fast_min / off_mean_min
    d = np.zeros(T_fast)
    f = 0
    while f < T_fast:
        f += int(rng.geometric(p_off))
        n_on = int(rng.geometric(p_on))
        d[f:f + n_on] = level
        f += n_on
    return d


def _explicit(cfg: dict, grid: TimeGrid, llms: tuple[LLM, ...]):
    jid = {x.id: j for j, x in enumerate(llms)}
    out = []
    for c in cfg["borrowers"]["clients"]:
        dd = c["demand"]
        if dd["kind"] == "array":
            d = np.asarray(dd["values"], dtype=np.float64)
        else:
            d = onoff_demand(grid.T_fast, grid.fast_min, dd["on_mean_min"], dd["off_mean_min"], dd["level"],
                             dd["seed"])
        out.append((jid[c["llm"]], c["region"], c["slo_class"], tuple(c["borrowers"]), d))
    return out


def _one_site_per_lender(sites, idx) -> list[int]:
    """The first of the sites `idx` of each lender: lambda_ref is the median over lenders, one value
    each (§10 S2), so that merging layer sites cannot change it. All sites of a lender share its load
    scenario, so any of them gives the lender's lambda."""
    seen, out = set(), []
    for l in idx:
        if sites[l].lender not in seen:
            seen.add(sites[l].lender)
            out.append(l)
    return out


# ---------------------------------------------------------------- builder
def _fee_per_llm(b, llms: tuple[LLM, ...]) -> np.ndarray:
    """(J,) transfer fee in USD per load: one number for every LLM, or the resolved {LLM id: USD} of C10
    (load_config checked that it names every LLM and no other id)."""
    if isinstance(b, dict):
        miss = [x.id for x in llms if x.id not in b]
        if miss:
            raise ConfigError(f"costs.beta_jl_usd: no fee for LLM(s) {miss}")
        return np.array([float(b[x.id]) for x in llms], dtype=np.float64)
    return np.full(len(llms), float(b), dtype=np.float64)


def build_instance(cfg: Union[str, Path, dict]) -> Instance:
    """Build an Instance from a config (§4.3); calls validate()."""
    cfg = load_config(cfg)
    notes: list[str] = []
    t = cfg["time"]
    slow, fast = t["slow_slot_min"], t["fast_slot_min"]
    grid = TimeGrid(slow, fast, t["horizon_min"] // slow, t["start_minute_of_week"])
    pr = cfg["prices"]
    contracts = tuple(_contract(c, slow, cfg["billing"]) for c in cfg["contracts"])
    llms = tuple(_llm(x, pr["q_gpu_usd_per_gpu_h"]) for x in cfg["llms"])
    merge = cfg["lender_model"]["merge_identical_layers"]

    parts: list[_LenderSites] = []
    for e in cfg["lenders"] + _protected_lenders(cfg):
        ls = _trace_lender(e, cfg, grid, contracts, notes, merge) if e["kind"] == "trace" \
            else _single_site_lender(e, cfg, contracts)
        if ls is not None:
            parts.append(ls)
    n_trace = sum(e["kind"] == "trace" for e in cfg["lenders"])
    if n_trace:
        n_with = sum(ls.trace.S_full is not None for ls in parts)
        notes.append(f"{n_with} of {n_trace} trace lenders have at least one site")
    sites, lenders = [], []
    price_rows, scen, lam_cols = [], [], []
    J, K = len(llms), len(contracts)
    for ls in parts:
        first = len(sites)
        for s in ls.sites:
            sites.append(s)
            row = np.full(K, INF)
            for k, a in ls.price.items():
                row[k] = a
            price_rows.append(row)
            scen.append("explicit" if ls.scenario == "explicit" else ls.scenario)
            if ls.scenario == "explicit":
                lam = ls.lam
                col = [float(lam[x.id]) if isinstance(lam, dict) else float(lam) for x in llms]
            else:
                col = [calib.load_time_s(x.w_GB, x.g, ls.scenario) for x in llms]
            lam_cols.append(col)
        lenders.append(replace(ls.trace, site_index=tuple(range(first, len(sites)))))
    if not sites:
        raise ConfigError("the config gives no site (every lender was dropped)")
    m = len(sites)
    price = np.vstack(price_rows)
    lam_s = np.asarray(lam_cols, dtype=np.float64).T.reshape(J, m)
    costs = cfg["costs"]
    fee = _fee_per_llm(costs["beta_jl_usd"], llms)
    beta_usd = np.repeat(fee[:, None], m, axis=1)
    if isinstance(costs["beta_jl_usd"], dict):
        notes.append("transfer fee per LLM (USD per load): "
                     + ", ".join(f"{x.id} {fee[j]:.6g}" for j, x in enumerate(llms)))
    notes.append(f"{m} sites: " + ", ".join(s.id for s in sites))

    # demand and clients
    supply = float(sum(s.capacity_gpus for s in sites if s.kind == "layer"))
    model = cfg["borrowers"]["model"]
    bstats: dict = {}
    if model == "regional":
        cl, bstats = _regional(cfg, grid, llms, supply, notes)
    elif model == "series":
        cl, bstats = _series_model(cfg, grid, llms, supply, notes)
    else:
        cl = _explicit(cfg, grid, llms)
    if not cl:
        raise ConfigError("borrowers: no client with positive demand")
    n = len(cl)
    c_llm = np.array([c[0] for c in cl], dtype=np.int64)
    c_reg = tuple(c[1] for c in cl)
    c_slo = tuple(c[2] for c in cl)
    demand = np.vstack([c[4] for c in cl]).astype(np.float64)

    # routing costs (§4.3 step 8)
    adj = {frozenset(p) for p in cfg["regions"]["adjacency"]}
    ratio = cfg["regions"]["relaxed_routing_cost_over_q"]
    delta = np.full((n, m), INF)
    for c in range(n):
        q_j = llms[c_llm[c]].q_usd_per_h
        for l, s in enumerate(sites):
            if s.region == c_reg[c]:
                delta[c, l] = 0.0
            elif c_slo[c] == "relaxed" and frozenset((s.region, c_reg[c])) in adj:
                delta[c, l] = ratio * q_j
    clients = Clients(llm=c_llm, region=c_reg, slo_class=c_slo, borrowers=tuple(c[3] for c in cl),
                      delta_usd_per_h=delta, demand=demand)

    # stranding (§4.3 step 9)
    st = cfg["stranding"]
    rev_sites = [l for l, s in enumerate(sites) if any(not contracts[k].protected for k in s.menu)]
    if st["beta_tilde_ref"]["load_time"] == "site":
        # one revocable lender (§10 S2 revised): its layer sites share its load times, so the value
        # does not depend on merge_identical_layers
        rev_lenders = _one_site_per_lender(sites, rev_sites)
        if len(rev_lenders) != 1:
            raise ConfigError(f"stranding.beta_tilde_ref.load_time 'site' needs exactly one revocable lender, "
                              f"got {len(rev_lenders)}")
        lam_ref = lam_s[:, rev_lenders[0]]
    else:   # 'median_site': the median over the revocable lenders, one value each (§10 S2 revised)
        lam_ref = np.median(lam_s[:, _one_site_per_lender(sites, rev_sites if rev_sites else range(m))], axis=1)
    a0, q_gpu, phi = pr["a0_usd_per_gpu_h"], pr["q_gpu_usd_per_gpu_h"], costs["phi"]
    bt_ref = np.array([calib.beta_tilde_usd(float(fee[j]), float(lam_ref[j]), x.g, a0, q_gpu, phi)
                       for j, x in enumerate(llms)])
    r_mu, kv = st["mu_over_beta_tilde"], st["kv_share"]
    stranding = Stranding(mu_kv_usd=kv * r_mu * bt_ref, mu_fl_usd=st["mu_fl_over_beta_tilde"] * bt_ref,
                          mu_fb_usd=(1 - kv) * r_mu * bt_ref,
                          pi_usd_per_min=np.array([st["pi_over_q"] * x.q_usd_per_h / 60 for x in llms]),
                          W_f_min=float(st["W_f_min"]))
    notes.append(f"{n} clients; beta_tilde_ref = {np.round(bt_ref, 6).tolist()} USD")

    inst = Instance(name=cfg["name"], grid=grid, regions=tuple(cfg["regions"]["list"]), contracts=contracts,
                    llms=llms, sites=tuple(sites), price=price, lam_s=lam_s, beta_usd=beta_usd,
                    load_scenario=tuple(scen), clients=clients, units_per_replica=cfg["units"]["per_replica"],
                    stranding=stranding, phi_load=phi, q_gpu_usd_per_h=q_gpu, a0_usd_per_gpu_h=a0,
                    kappa_infinite=costs["kappa_infinite"], billing=cfg["billing"], lenders=tuple(lenders),
                    config=cfg, seed=cfg["seed"], notes=notes, borrower_stats=bstats)
    validate(inst)
    return inst


# ---------------------------------------------------------------- validation
def validate(inst: Instance) -> None:
    """Raise InstanceError listing every violated rule of §3.4.4."""
    err = []
    g = inst.grid
    m, J, K, n = inst.m, inst.J, inst.K, inst.n
    if g.fast_min < 1 or g.slow_min < 1 or g.slow_min % g.fast_min:
        err.append(f"slow_min {g.slow_min} is not a multiple of fast_min {g.fast_min}")
    if g.T_slow < 1:
        err.append("T_slow < 1")
    for c in inst.contracts:
        if not c.protected and c.tau_slots < 1:
            err.append(f"contract {c.id}: tau_slots {c.tau_slots} < 1")
        if c.H_min < 0:
            err.append(f"contract {c.id}: H_min < 0")
        if c.prepaid_min < 0:
            err.append(f"contract {c.id}: prepaid_min < 0")
    shapes = {"price": (inst.price, (m, K)), "lam_s": (inst.lam_s, (J, m)), "beta_usd": (inst.beta_usd, (J, m)),
              "clients.delta_usd_per_h": (inst.clients.delta_usd_per_h, (n, m)),
              "clients.demand": (inst.clients.demand, (n, g.T_fast))}
    for name, (a, shp) in shapes.items():
        if np.shape(a) != shp:
            err.append(f"{name} has shape {np.shape(a)}, expected {shp}")
    if len(inst.load_scenario) != m:
        err.append("load_scenario has the wrong length")
    for name in ("mu_kv_usd", "mu_fl_usd", "mu_fb_usd", "pi_usd_per_min"):
        if np.shape(getattr(inst.stranding, name)) != (J,):
            err.append(f"stranding.{name} has the wrong shape")
    if err:
        raise InstanceError("; ".join(err))
    for l, s in enumerate(inst.sites):
        fin = np.isfinite(inst.price[l])
        if set(np.flatnonzero(fin).tolist()) != set(s.menu):
            err.append(f"site {s.id}: menu {s.menu} differs from its finite prices {np.flatnonzero(fin).tolist()}")
        if np.any(inst.price[l][fin] <= 0) or np.any(np.isnan(inst.price[l])):
            err.append(f"site {s.id}: an offered price is not positive")
        if not s.menu:
            err.append(f"site {s.id}: empty menu")
        if not s.capacity_gpus > 0:
            err.append(f"site {s.id}: capacity {s.capacity_gpus} is not positive")
        if s.kind == "protected" and any(not inst.contracts[k].protected for k in s.menu):
            err.append(f"site {s.id}: revocable contract on a protected site")
        if s.R_explicit is not None:
            R = np.asarray(s.R_explicit)
            if R.ndim != 1 or (len(R) and (np.any(np.diff(R) <= 0) or R[0] < 0 or R[-1] >= g.T_slow)):
                err.append(f"site {s.id}: R_explicit is not sorted, unique and in [0, T_slow)")
    d = inst.clients.demand
    if not np.all(np.isfinite(d)) or np.any(d < 0):
        err.append("demand is not finite and non-negative")
    dl = inst.clients.delta_usd_per_h
    if np.any(np.isnan(dl)) or np.any(dl < 0) or np.any(np.isneginf(dl)):
        err.append("delta must be >= 0 or INF")
    if np.any(np.isnan(inst.lam_s)) or np.any(inst.lam_s < 0):
        err.append("lam_s must be >= 0")
    if n and (inst.clients.llm.min() < 0 or inst.clients.llm.max() >= J):
        err.append("client LLM index out of range")
    if inst.units_per_replica < 1:
        err.append("units_per_replica < 1")
    if err:
        raise InstanceError("; ".join(err))


# ---------------------------------------------------------------- units and public view
def units(inst: Instance) -> UnitTable:
    """Client units (c, v), v = 1..V_c with V_c = max(1, ceil(u max_f d_c(f))); active[t] iff the
    maximum of d_c over the fast slots of slow slot t exceeds (v - 1) / u (design §3.2.1, §5.2.3)."""
    g, u = inst.grid, inst.units_per_replica
    D = inst.clients.demand.reshape(inst.n, g.T_slow, g.phi).max(axis=2)
    cl, vv, act = [], [], []
    for c in range(inst.n):
        V = max(1, math.ceil(u * float(D[c].max())))
        cl.append(np.full(V, c, dtype=np.int64))
        vv.append(np.arange(1, V + 1, dtype=np.int64))
        act.append(D[c][None, :] > (np.arange(V) / u)[:, None])
    if not cl:
        return UnitTable(np.zeros(0, np.int64), np.zeros(0, np.int64), np.zeros((0, g.T_slow), bool))
    return UnitTable(np.concatenate(cl), np.concatenate(vv), np.vstack(act))


def active_units(D: np.ndarray, u: int) -> np.ndarray:
    """Active units per client for the slot maxima D (any shape, e.g. (n,)): the number of i >= 0
    with i / u < D (float division i / u and strict comparison, as units()); 0 where D <= 0
    (MS2 C1, M57). units(inst) also caps the count at V_c = max(1, ceil(u max_t D_c(t))), a horizon
    maximum that a policy does not know; for u a power of two the cap never binds and the two agree
    exactly. For other u they can differ by one unit where u D lies within float error of an integer."""
    D = np.asarray(D, dtype=np.float64)
    u = int(u)
    out = np.zeros(D.shape, dtype=np.int64)
    pos = D > 0
    if not pos.any():
        return out
    d = D[pos]
    k = np.ceil(d * u).astype(np.int64)
    # correct ceil(u D) for float error, so that k = #{i >= 0 : i / u < D} exactly
    while True:
        up = (k / u) < d
        if not up.any():
            break
        k[up] += 1
    while True:
        down = (k > 0) & ((k - 1) / u >= d)
        if not down.any():
            break
        k[down] -= 1
    out[pos] = k
    return out


# ---------------------------------------------------------------- derived instances (MS2 C2)
def _derived(inst: Instance, key: str, value) -> dict:
    """inst.config with the derivation recorded under 'derived' (a derived instance is not rebuilt
    from its config): restrict_clients composes client indices, restrict_horizon start slots."""
    cfg = dict(inst.config)
    der = dict(cfg.get("derived") or {})
    if key == "restrict_clients" and key in der:
        value = [der[key][i] for i in value]
    elif key == "restrict_horizon" and key in der:
        value = [der[key][0] + value[0], value[1]]
    der[key] = value
    cfg["derived"] = der
    return cfg


def restrict_clients(inst: Instance, clients) -> Instance:
    """The instance with only the listed clients, in the given order: same grid, sites, lenders,
    prices, stranding and Gamma-scaled demand rows; borrower_stats restricted to their borrowers;
    config['derived'] = {'restrict_clients': list} (indices into the original instance). Raises
    InstanceError for an empty, repeated or out-of-range selection."""
    idx = [int(c) for c in clients]
    if not idx:
        raise InstanceError("restrict_clients: no client selected")
    if len(set(idx)) != len(idx) or min(idx) < 0 or max(idx) >= inst.n:
        raise InstanceError(f"restrict_clients: clients {idx} are repeated or outside [0, {inst.n})")
    cl = inst.clients
    ix = np.asarray(idx, dtype=np.int64)
    sub = Clients(llm=np.asarray(cl.llm, dtype=np.int64)[ix].copy(), region=tuple(cl.region[i] for i in idx),
                  slo_class=tuple(cl.slo_class[i] for i in idx), borrowers=tuple(cl.borrowers[i] for i in idx),
                  delta_usd_per_h=np.asarray(cl.delta_usd_per_h, dtype=np.float64)[ix].copy(),
                  demand=np.asarray(cl.demand, dtype=np.float64)[ix].copy())
    keep = {b for i in idx for b in cl.borrowers[i]}
    stats = {b: dict(v) for b, v in inst.borrower_stats.items() if b in keep}
    out = replace(inst, clients=sub, borrower_stats=stats, config=_derived(inst, "restrict_clients", idx),
                  notes=list(inst.notes) + [f"restrict_clients {idx}"])
    validate(out)
    return out


def with_demand(inst: Instance, demand: np.ndarray) -> Instance:
    """The instance with clients.demand replaced by `demand` (n, T_fast), finite and >= 0;
    config['derived']['with_demand'] = sha256 of the array (float64 bytes)."""
    d = np.array(demand, dtype=np.float64, copy=True)
    if d.shape != (inst.n, inst.grid.T_fast):
        raise InstanceError(f"with_demand: shape {d.shape}, expected {(inst.n, inst.grid.T_fast)}")
    if not np.all(np.isfinite(d)) or np.any(d < 0):
        raise InstanceError("with_demand: demand is not finite and non-negative")
    out = replace(inst, clients=replace(inst.clients, demand=d),
                  config=_derived(inst, "with_demand", hashlib.sha256(d.tobytes()).hexdigest()),
                  notes=list(inst.notes) + ["with_demand"])
    validate(out)
    return out


def restrict_horizon(inst: Instance, t0_slow: int, T_slow: int) -> Instance:
    """Slow slots [t0, t0 + T) of inst as a new horizon starting at 0: demand, lender series S and
    S_lend and every explicit R sliced and shifted; start_mow advanced by t0 * slow_min (mod 10080);
    each trace lender's offset_5min advanced by t0 * slow_min / 5 (mod len(S_full)), so that
    owed_series and buffer violations use the same slack minutes as on inst. Contracts, prices and
    borrower_stats are unchanged; config['derived'] = {'restrict_horizon': [t0, T]}. InstanceError
    unless 0 <= t0, T >= 1, t0 + T <= inst.grid.T_slow and t0 * slow_min is a multiple of 5."""
    t0, T = int(t0_slow), int(T_slow)
    g = inst.grid
    if t0 < 0 or T < 1 or t0 + T > g.T_slow:
        raise InstanceError(f"restrict_horizon: slots [{t0}, {t0 + T}) are not inside [0, {g.T_slow})")
    if (t0 * g.slow_min) % SLACK_SLOT_MIN:
        raise InstanceError(f"restrict_horizon: t0 * slow_min = {t0 * g.slow_min} is not a multiple of "
                            f"{SLACK_SLOT_MIN} (the slack series' slot)")
    grid = TimeGrid(g.slow_min, g.fast_min, T, (g.start_mow + t0 * g.slow_min) % MIN_PER_WEEK)
    sites = []
    for s in inst.sites:
        if s.R_explicit is not None:
            R = np.asarray(s.R_explicit, dtype=np.int64)
            s = replace(s, R_explicit=(R[(R >= t0) & (R < t0 + T)] - t0).astype(np.int64))
        sites.append(s)
    lenders = []
    for lt in inst.lenders:
        kw = {}
        if lt.S is not None:
            kw["S"] = np.asarray(lt.S)[t0:t0 + T].copy()
        if lt.S_lend is not None:
            kw["S_lend"] = np.asarray(lt.S_lend)[t0:t0 + T].copy()
        if lt.S_full is not None and len(lt.S_full):
            kw["offset_5min"] = (int(lt.offset_5min) + t0 * g.slow_min // SLACK_SLOT_MIN) % len(lt.S_full)
        lenders.append(replace(lt, **kw))
    phi = g.phi
    clients = replace(inst.clients, demand=np.asarray(inst.clients.demand)[:, t0 * phi:(t0 + T) * phi].copy())
    out = replace(inst, grid=grid, sites=tuple(sites), lenders=tuple(lenders), clients=clients,
                  config=_derived(inst, "restrict_horizon", [t0, T]),
                  notes=list(inst.notes) + [f"restrict_horizon [{t0}, {t0 + T})"])
    validate(out)
    return out


def _ro(a: np.ndarray) -> np.ndarray:
    a = np.array(a, copy=True)
    a.setflags(write=False)
    return a


def public_view(inst: Instance, information: InfoModel) -> PublicView:
    """Everything a policy may see before the run (§5.2): no announcement sets, layer indices or
    slack. Layer site ids become '<lender>/S<i>' (i = rank of the site within its lender by
    increasing local_layer_lo); arrays are read-only copies."""
    if information not in ("I1", "I2"):
        raise ValueError(f"unknown information model {information!r}")
    rank: dict[int, int] = {}
    for lt in inst.lenders:
        lay = sorted((l for l in lt.site_index if inst.sites[l].kind == "layer"),
                     key=lambda l: inst.sites[l].local_layer_lo)
        for i, l in enumerate(lay):
            rank[l] = i
    sites = tuple(replace(s, id=f"{s.lender}/S{rank[l]}" if s.kind == "layer" else s.id, layer_lo=None,
                          layer_hi=None, local_layer_lo=None, R_explicit=None) for l, s in enumerate(inst.sites))
    st = inst.stranding
    strand = Stranding(_ro(st.mu_kv_usd), _ro(st.mu_fl_usd), _ro(st.mu_fb_usd), _ro(st.pi_usd_per_min), st.W_f_min)
    return PublicView(grid=inst.grid, regions=inst.regions, contracts=inst.contracts, llms=inst.llms, sites=sites,
                      price=_ro(inst.price), lam_s=_ro(inst.lam_s), beta_usd=_ro(inst.beta_usd),
                      beta_tilde_usd=_ro(inst.beta_tilde_usd()), client_llm=_ro(inst.clients.llm),
                      client_region=inst.clients.region, client_delta_usd_per_h=_ro(inst.clients.delta_usd_per_h),
                      units_per_replica=inst.units_per_replica, stranding=strand,
                      q_gpu_usd_per_h=inst.q_gpu_usd_per_h, kappa_infinite=inst.kappa_infinite,
                      billing=inst.billing, information=information)


# ---------------------------------------------------------------- core export and import
@dataclass(eq=False)
class CoreExport:
    core: object                 # core.Instance (from paths.import_core())
    omega: list[np.ndarray]      # per core site, sorted int64
    unit_map: UnitTable          # core client i = unit i
    big_m_price: Optional[float]
    exact: bool                  # True iff the export is exact (conditions of §3.4.4)
    notes: list[str] = field(default_factory=list)


def from_core(core_inst, omega, slot_min: int = 60) -> tuple[Instance, Schedule]:
    """Core emulation of a core.Instance with announcement sets omega (§3.4.4); one slot of slot_min
    minutes per core slot. Raises InstanceError if some tau_k == 0 (rule T4 needs tau >= 1 slot)."""
    I = core_inst
    tau, H = np.asarray(I.tau), np.asarray(I.H)
    if np.any(tau == 0):
        raise InstanceError("from_core: a contract with tau = 0 has no engine counterpart (rule T4 needs tau >= 1 slot)")
    if np.any(tau < 0) or np.any(H < 0):
        raise InstanceError("from_core: negative tau or H")
    T, m, K = int(I.T), int(I.a.shape[0]), len(tau)
    J, n = len(I.g), len(I.cl_llm)
    grid = TimeGrid(slot_min, slot_min, T, 0)
    contracts = tuple(Contract(f"k{k}", int(tau[k]), int(H[k]) * slot_min, int(tau[k] + H[k]) * slot_min,
                               calib.contract_klass(int(tau[k]) * slot_min, int(H[k]) * slot_min, slot_min))
                      for k in range(K))
    sites, lenders, R = [], [], []
    for l in range(m):
        o = np.asarray(omega[l], dtype=np.int64)
        Rl = np.unique(o[(o >= 0) & (o < T)])
        R.append(Rl)
        sites.append(Site(id=f"L{l}", lender=f"L{l}", kind="synthetic", region="r0", group=f"g{l}",
                          capacity_gpus=INF, menu=tuple(range(K)), layer_lo=None, layer_hi=None,
                          local_layer_lo=None, R_explicit=Rl.copy()))
        lenders.append(LenderTrace(lender=f"L{l}", kind="synthetic", series=None, S_full=None, S=None, B_gpus=0.0,
                                   S_lend=None, v0=0, n_layers=0, layer_gpus=0, D_max_lender_min=0, offset_5min=0,
                                   site_index=(l,)))
    q_h = float(I.q) * 60 / slot_min
    llms = tuple(LLM(f"j{j}", "M", int(I.g[j]), 0.0, INF, 0.0, 0.0, q_h) for j in range(J))
    owner = getattr(I, "owner", None)
    bor = tuple((str(owner[c]),) if owner is not None else ("b0",) for c in range(n))
    clients = Clients(llm=np.asarray(I.cl_llm, dtype=np.int64).copy(), region=("r0",) * n, slo_class=("strict",) * n,
                      borrowers=bor, delta_usd_per_h=np.asarray(I.delta, dtype=np.float64) * 60 / slot_min,
                      demand=np.asarray(I.active).astype(np.float64))
    z = np.zeros(J)
    inst = Instance(name="from_core", grid=grid, regions=("r0",), contracts=contracts, llms=llms, sites=tuple(sites),
                    price=np.asarray(I.a, dtype=np.float64) * 60 / slot_min, lam_s=np.zeros((J, m)),
                    beta_usd=np.asarray(I.beta, dtype=np.float64).copy(), load_scenario=("explicit",) * m,
                    clients=clients, units_per_replica=1,
                    stranding=Stranding(z.copy(), z.copy(), z.copy(), z.copy(), 0.0), phi_load=0.0,
                    q_gpu_usd_per_h=0.0, a0_usd_per_gpu_h=0.0, kappa_infinite=True, billing="prepaid_D",
                    lenders=tuple(lenders), config={"from_core": {"slot_min": slot_min}}, seed=0, notes=[])
    validate(inst)
    return inst, Schedule("trace", tuple(r.copy() for r in R), True)


def _owners(inst: Instance, ut: UnitTable, notes: list[str]) -> Optional[np.ndarray]:
    bor = inst.clients.borrowers
    if all(b == ("b0",) for b in bor):
        return None
    if any(len(b) > 1 for b in bor):
        notes.append("clients that merge several borrowers export their first borrower as owner")
    first = [b[0] for b in bor]
    if all(x.isascii() and x.isdecimal() for x in first):
        own_c = np.array([int(x) for x in first], dtype=np.int64)
    else:
        ids = sorted(set(first))
        own_c = np.array([ids.index(x) for x in first], dtype=np.int64)
        notes.append(f"owner = index of the first borrower id in {ids}")
    return own_c[ut.client]


def to_core(inst: Instance, sched: Schedule, *, not_offered: str = "raise", beta_price: str = "a0") -> CoreExport:
    """Export to core.Instance with rule T12: core slot = slow slot, clients = units(inst) (§3.4.4).

    A pair (site, contract) that is not offered raises InstanceError (not_offered='raise') or gets the
    price M of big_m_price (not_offered='big_m'), so that no optimal core solution uses it. A big_m export
    is for core.opt_omega, core.opt_eager and solve_core only: pd.FracPD opens columns whatever their price.
    beta[j, l] is the loading cost beta_tilde at price a0 (beta_price='a0') or at the cheapest offered
    price of site l ('min_offered'). `exact` and `notes` say whether the export is exact."""
    if not_offered not in ("raise", "big_m"):
        raise ValueError(f"not_offered must be 'raise' or 'big_m', got {not_offered!r}")
    if beta_price not in ("a0", "min_offered"):
        raise ValueError(f"beta_price must be 'a0' or 'min_offered', got {beta_price!r}")
    core = paths.import_core()
    notes: list[str] = []
    g = inst.grid
    T, slow, u = g.T_slow, g.slow_min, inst.units_per_replica
    m, J = inst.m, inst.J
    if len(sched.R) != m:
        raise InstanceError(f"schedule has {len(sched.R)} sites, the instance {m}")
    tau = np.array([T if c.protected else c.tau_slots for c in inst.contracts], dtype=np.int64)
    H = np.array([0 if c.protected else c.H_min // slow for c in inst.contracts], dtype=np.int64)
    ut = units(inst)
    q_units = np.array([x.q_usd_per_h * slow / (60 * u) for x in inst.llms])
    if np.any(np.abs(q_units - q_units[0]) > 1e-12 * max(1.0, abs(q_units[0]))):
        raise InstanceError(f"to_core: the per-unit fallback cost differs across LLMs: {q_units.tolist()}")
    q = float(q_units[0])
    gj = np.array([x.g for x in inst.llms], dtype=np.int64)
    a = inst.price * slow / 60
    off = ~np.isfinite(inst.price)
    big_m = None
    if off.any():
        if not_offered == "raise":
            pairs = [(inst.sites[l].id, inst.contracts[k].id) for l, k in zip(*np.nonzero(off))]
            raise InstanceError(f"to_core: contracts not offered at {pairs[:6]}{'...' if len(pairs) > 6 else ''}; "
                                "use not_offered='big_m' (for opt_omega, opt_eager and solve_core only)")
        n_el = int(ut.active.sum())
        big_m = 2.0 * (q * n_el + 1.0) * 60.0 / (int(gj.min()) * slow)
        a = np.where(off, big_m * slow / 60, a)
        notes.append(f"{int(off.sum())} non-offered (site, contract) pairs priced at M = {big_m:.6g} USD/GPU-h")
    beta = np.zeros((J, m))
    for l in range(m):
        if beta_price == "a0":
            ref = inst.a0_usd_per_gpu_h
        else:
            ref = float(np.min(inst.price[l][np.isfinite(inst.price[l])]))
        for j, x in enumerate(inst.llms):
            beta[j, l] = calib.beta_tilde_usd(float(inst.beta_usd[j, l]), float(inst.lam_s[j, l]), x.g, ref,
                                              inst.q_gpu_usd_per_h, inst.phi_load)
    core_inst = core.Instance(T=T, tau=tau, H=H, a=a, beta=beta, g=gj, q=q,
                              cl_llm=inst.clients.llm[ut.client].astype(np.int64),
                              delta=inst.clients.delta_usd_per_h[ut.client] * slow / (60 * u),
                              active=ut.active.copy(), owner=_owners(inst, ut, notes))
    omega = [np.asarray(sched.R[l], dtype=np.int64).copy() for l in range(m)]

    st, d = inst.stranding, inst.clients.demand
    checks = {
        "kappa_infinite": inst.kappa_infinite,
        "all lam_s == 0": bool(np.all(inst.lam_s == 0)),
        "all stranding parameters 0": bool(all(np.all(getattr(st, x) == 0) for x in
                                               ("mu_kv_usd", "mu_fl_usd", "mu_fb_usd", "pi_usd_per_min"))
                                           and st.W_f_min == 0),
        "billing prepaid_D": inst.billing == "prepaid_D",
        "all capacities INF": all(s.capacity_gpus == INF for s in inst.sites),
        "fast_min == slow_min": g.fast_min == g.slow_min,
        "every H_min a multiple of slow_min": all(c.H_min % slow == 0 for c in inst.contracts if not c.protected),
        "every protected prepaid_min == horizon_min": all(c.prepaid_min == g.horizon_min
                                                          for c in inst.contracts if c.protected),
        "u == 1 and demand in {0, 1}": u == 1 and bool(np.all((d == 0) | (d == 1))),
        "full menus or big_m": (not off.any()) or not_offered == "big_m",
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        notes.append("export not exact: " + "; ".join(failed))
    return CoreExport(core=core_inst, omega=omega, unit_map=ut, big_m_price=big_m, exact=not failed, notes=notes)
