"""Shared types of the Sublet simulator (design/sim_spec.md §3.2).

Field names, order, types and defaults are fixed by the specification; only docstrings
are added here. Time conventions (rules T1-T12) are in §3.1: integer minutes from horizon
minute 0, slow slots of `slow_min` minutes, fast slots of `fast_min` minutes. Money in USD.
Dataclasses that hold arrays use eq=False. This module imports only numpy and the
standard library.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Optional, Union
import numpy as np

INF = float("inf")
BillingMode = Literal["prepaid_D", "per_slot", "commit_tau"]
InfoModel = Literal["I1", "I2"]
ScheduleMode = Literal["trace", "eager", "adaptive", "safe_site", "iid_step", "correlated"]
BenchGrid = Literal["slow", "fast", "slow_lb"]
SiteKind = Literal["layer", "protected", "synthetic"]

# ---------------------------------------------------------------- time
@dataclass(frozen=True)
class TimeGrid:
    """Slow and fast slot lengths and the horizon (rules T1, T2, T10)."""
    slow_min: int          # Δ_s, minutes per slow slot
    fast_min: int          # Δ_f, minutes per fast slot; slow_min % fast_min == 0
    T_slow: int            # horizon in slow slots
    start_mow: int = 0     # minute of week (UTC, Monday 00:00 = 0) of horizon minute 0
    @property
    def phi(self) -> int: return self.slow_min // self.fast_min
    @property
    def T_fast(self) -> int: return self.T_slow * self.phi
    @property
    def horizon_min(self) -> int: return self.T_slow * self.slow_min
    def bench_min(self, grid: BenchGrid) -> int:
        return self.fast_min if grid == "fast" else self.slow_min
    def T_bench(self, grid: BenchGrid) -> int: return self.horizon_min // self.bench_min(grid)

# ---------------------------------------------------------------- menu, LLMs, sites
@dataclass(frozen=True)
class Contract:
    """Lease contract (rule T4): guaranteed period, notice and minimum billed term."""
    id: str
    tau_slots: Optional[int]   # guaranteed period in slow slots (>= 1); None = protected
    H_min: int                 # notice in minutes (0 for protected)
    prepaid_min: int           # minimum billed term P_k in minutes (resolved, §4.2)
    klass: str                 # 'spot-like' | 'AEP-82-like' | 'GFS-like' | 'general' | 'protected'
    @property
    def protected(self) -> bool: return self.tau_slots is None
    def D_min(self, slow_min: int) -> Optional[int]:
        return None if self.protected else self.tau_slots * slow_min + self.H_min

@dataclass(frozen=True)
class LLM:
    """A served LLM: GPUs per replica, goodput, drain time and fallback cost."""
    id: str
    tier: str                  # 'S' | 'M' | 'L' (or free text for explicit entries)
    g: int                     # GPUs per replica
    w_GB: float                # weight size
    kappa_wtok_per_min: float  # goodput in weighted tokens per minute (INF: uncapacitated)
    w_in: float                # weight of an input token (output token = 1)
    T_dr_s: float              # P99 drain time in seconds
    q_usd_per_h: float         # fallback cost of one full replica load per hour (= g q_GPU)

@dataclass(frozen=True, eq=False)
class Site:
    """A site: one lender band (merged layers), a protected pool or a synthetic site."""
    id: str                    # e.g. 'a2:c05/L7-8', 'prot:europe', 'L0'
    lender: str                # lender id
    kind: SiteKind
    region: str
    group: str                 # correlation group
    capacity_gpus: float       # INF = unlimited
    menu: tuple[int, ...]      # indices into Instance.contracts offered here
    layer_lo: Optional[int]    # global index v0+v of the lowest merged layer (layer sites)
    layer_hi: Optional[int]    # global index of the highest merged layer
    local_layer_lo: Optional[int]  # v of the lowest merged layer, 1-based within the offered block
    R_explicit: Optional[np.ndarray] = None  # synthetic sites: sorted unique int64 slow slots

@dataclass(frozen=True, eq=False)
class Stranding:
    """Stranding cost parameters per LLM (rule T11)."""
    mu_kv_usd: np.ndarray      # (J,) per replica load moved, any destination
    mu_fl_usd: np.ndarray      # (J,) in-flight loss scale, multiplied by (1 - 60 h / T_dr_s)^+
    mu_fb_usd: np.ndarray      # (J,) per replica load moved to fallback (C2's mu)
    pi_usd_per_min: np.ndarray # (J,) SLO penalty rate while the fallback warms up
    W_f_min: float             # fallback warm-up time

@dataclass(eq=False)
class Clients:
    """Clients (merged borrowers of one LLM and region) with routing costs and demand."""
    llm: np.ndarray            # (n,) int64 LLM index
    region: tuple[str, ...]    # (n,)
    slo_class: tuple[str, ...] # (n,) 'strict' | 'relaxed'
    borrowers: tuple[tuple[str, ...], ...]  # (n,) ids of the merged borrowers
    delta_usd_per_h: np.ndarray  # (n, m) float64; INF = SLO-infeasible
    demand: np.ndarray         # (n, T_fast) float64, replica loads per fast slot
    @property
    def n(self) -> int: return len(self.llm)

@dataclass(eq=False)
class LenderTrace:             # private: never shown to a policy
    """Private lender state: slack series, buffer, layer block and its sites."""
    lender: str
    kind: str                  # 'maas' | 'spot' | 'synthetic' | 'protected'
    series: Optional[str]      # trace key, e.g. 'a2:c05', 'a1:H800'
    S_full: Optional[np.ndarray]   # whole 5-min slack series (GPUs)
    S: Optional[np.ndarray]    # (T_slow,) physical slack aligned to the horizon
    B_gpus: float              # buffer B_l(D_max) in GPUs
    S_lend: Optional[np.ndarray]   # (T_slow,) lendable capacity (S - B)^+
    v0: int                    # layer offset
    n_layers: int              # offered layers V_l
    layer_gpus: int            # g^lay
    D_max_lender_min: int      # window of the buffer (lender convention, §6.1)
    offset_5min: int           # alignment offset into S_full, in 5-min slots
    site_index: tuple[int, ...]    # indices of this lender's sites
    # synthetic and protected lenders (and from_core instances): series, S_full, S, S_lend None;
    # B_gpus 0.0; v0, n_layers, layer_gpus, D_max_lender_min, offset_5min 0

@dataclass(eq=False)
class Instance:
    """A complete simulator instance (built by instance.build_instance, §3.4.4)."""
    name: str
    grid: TimeGrid
    regions: tuple[str, ...]
    contracts: tuple[Contract, ...]
    llms: tuple[LLM, ...]
    sites: tuple[Site, ...]
    price: np.ndarray          # (m, K) USD per GPU-hour; INF = not offered
    lam_s: np.ndarray          # (J, m) load time in seconds
    beta_usd: np.ndarray       # (J, m) one-off charge per load
    load_scenario: tuple[str, ...]  # (m,) a11 scenario name or 'explicit'
    clients: Clients
    units_per_replica: int     # u
    stranding: Stranding
    phi_load: float            # φ: share of a full replica's load on fallback during a load (not grid.phi)
    q_gpu_usd_per_h: float
    a0_usd_per_gpu_h: float
    kappa_infinite: bool       # True: a warm replica serves any load (core emulation)
    billing: BillingMode
    lenders: tuple[LenderTrace, ...]
    config: dict               # resolved config (provenance)
    seed: int
    notes: list[str] = field(default_factory=list)   # builder log (dropped contracts and lenders, site count)
    # MS2 C4: per borrower id {'llm': j, 'C0_loads': Γ C0 / κ_j, 'peak_loads': Γ max x^sm / κ_j} (replica
    # loads after the Γ scaling; filled by the regional and series demand models, empty otherwise)
    borrower_stats: dict = field(default_factory=dict)
    @property
    def m(self) -> int: return len(self.sites)
    @property
    def J(self) -> int: return len(self.llms)
    @property
    def K(self) -> int: return len(self.contracts)
    @property
    def n(self) -> int: return self.clients.n
    def lam_ms(self) -> np.ndarray:            # (J, m) int64
        return np.round(1000.0 * self.lam_s).astype(np.int64)
    def beta_tilde_usd(self) -> np.ndarray:    # (J, m, K) core loading cost (design §1.5.3); INF if not offered
        g = np.array([x.g for x in self.llms], float)[:, None, None]
        a = self.price[None, :, :]
        ok = np.isfinite(a)
        bt = (self.beta_usd[:, :, None] + self.lam_s[:, :, None] / 3600.0
              * (g * np.where(ok, a, 0.0) + self.phi_load * g * self.q_gpu_usd_per_h))
        return np.where(ok, bt, INF)

@dataclass(eq=False)
class UnitTable:               # client units of the ORML core (design §3.2.1)
    """Client units of the ORML core (design §3.2.1), one row per unit."""
    client: np.ndarray         # (N_u,) int64
    v: np.ndarray              # (N_u,) int64, 1-based layer within the client
    active: np.ndarray         # (N_u, T_slow) bool

# ---------------------------------------------------------------- lender
@dataclass(frozen=True)
class LenderModel:
    """Lender options: schedule mode, information model, purchase and violation rules (§6)."""
    schedule: ScheduleMode = "trace"
    information: InfoModel = "I1"
    on_unavailable: Literal["sell", "refuse"] = "sell"
    violations: Literal["absorb", "reclaim"] = "absorb"
    params: dict = field(default_factory=dict)

@dataclass(eq=False)
class Schedule:
    """Announcement sets omega: per site, the sorted slow slots at which leases are announced."""
    mode: str
    R: tuple[np.ndarray, ...]  # per site: sorted unique int64 slow slots in [0, T_slow)
    realized: bool = True      # False only for an adaptive schedule before the run
    @staticmethod
    def eager(inst: "Instance") -> "Schedule":        # protected sites keep R = ∅, as in §6.6
        full = np.arange(inst.grid.T_slow, dtype=np.int64)
        empty = np.zeros(0, dtype=np.int64)
        return Schedule("eager", tuple(empty.copy() if s.kind == "protected" else full.copy()
                                       for s in inst.sites), True)

# ---------------------------------------------------------------- policy interface
@dataclass(frozen=True)
class Buy:
    site: int; contract: int; llm: int; n_replicas: int = 1; tag: str = ""
    admission: float = 1.0                 # initial admission of the new replicas, in [0, 1]
@dataclass(frozen=True)
class Release:
    lease_id: int
@dataclass(frozen=True)
class Load:
    lease_id: int; llm: int
@dataclass(frozen=True)
class Unload:
    replica_id: int
@dataclass(frozen=True)
class Drain:
    replica_id: int; at_min: int
@dataclass(frozen=True)
class SetAdmission:
    replica_id: int; value: float          # in [0, 1]
Action = Union[Buy, Release, Load, Unload, Drain, SetAdmission]

@dataclass(frozen=True)
class LeaseView:
    id: int; site: int; contract: int; gpus: int; start_slot: int; start_min: int
    prepaid_end_min: int; announce_slot: Optional[int]; death_min: Optional[int]
    replicas: tuple[int, ...]

@dataclass(frozen=True)
class ReplicaView:
    id: int; lease_id: int; llm: int
    state: Literal["loading", "warm", "dead"]
    load_start_min: int; warm_fast: int    # first fast slot in which it is warm
    admission: float; drain_min: Optional[int]
    # In SlowObs at slot t, `admission` is the value in force from fast slot t*phi (§10 S33): every
    # pending change (Drain, SetAdmission) with effective fast slot <= t*phi is reflected; later
    # ones are not (a drain scheduled for later shows only in drain_min).

@dataclass(frozen=True)
class Notice:
    lease_id: int; r_slot: int; death_min: int

@dataclass(frozen=True)
class ActionResult:
    index: int; action: Action; ok: bool
    lease_id: Optional[int]; replica_ids: tuple[int, ...]; reason: str   # '' if ok

@dataclass(eq=False)
class SlowObs:
    """What a policy observes at the start of slow slot t (rule T9, §5.2)."""
    t: int
    minute: int
    demand: np.ndarray                     # (n, phi) demand of the fast slots of slot t
    leases: dict[int, LeaseView]           # own leases alive in the first fast slot of t
    replicas: dict[int, ReplicaView]       # replicas on those leases
    notices: list[Notice]                  # I1: own leases announced at slot t
    ended: list[tuple[int, int, str]]      # (lease_id, end_min, cause): end_min <= minute, not reported before
    results: list[ActionResult]            # outcome of the previous act() call
    site_announced: Optional[np.ndarray]   # I2 only: (m,) bool, t in R_l
    served_prev: np.ndarray                # (J, m) mean served load over slot t-1
    fallback_prev: np.ndarray              # (n,) mean fallback load over slot t-1
    cost_so_far: float

@dataclass(eq=False)
class FastObs:
    """What a policy observes after fast slot f has run."""
    f: int
    served: np.ndarray                     # (J, m) served load in fast slot f
    capacity: np.ndarray                   # (J, m) admitting warm capacity in f
    fallback: np.ndarray                   # (n,) fallback load in f
    results: list[ActionResult]            # results of this slow slot's act(); only in its first fast slot

@dataclass(frozen=True, eq=False)
class PublicView:                          # everything a policy may see before the run
    grid: TimeGrid; regions: tuple[str, ...]; contracts: tuple[Contract, ...]
    llms: tuple[LLM, ...]; sites: tuple[Site, ...]   # R_explicit, layer_lo, layer_hi, local_layer_lo None;
                                                     # layer site ids replaced by '<lender>/S<i>' (§3.4.4)
    price: np.ndarray; lam_s: np.ndarray; beta_usd: np.ndarray; beta_tilde_usd: np.ndarray
    client_llm: np.ndarray; client_region: tuple[str, ...]; client_delta_usd_per_h: np.ndarray
    units_per_replica: int; stranding: Stranding; q_gpu_usd_per_h: float
    kappa_infinite: bool; billing: BillingMode; information: InfoModel

# ---------------------------------------------------------------- engine records and results
@dataclass(eq=False)
class LeaseRecord:
    """A lease as recorded by the engine (representation in §3.1)."""
    id: int; site: int; contract: int; gpus: int; start_slot: int; start_min: int
    prepaid_end_min: int; announce_slot: Optional[int]; death_min: Optional[int]
    release_min: Optional[int]; end_min: int
    end_cause: Literal["reclaim", "release", "violation", "horizon"]
    prepaid_usd: float; rent_usd: float; tag: str

@dataclass(eq=False)
class ReplicaRecord:
    id: int; lease_id: int; llm: int; load_start_min: int; warm_fast: int
    end_fast: int              # first fast slot in which it no longer exists
    beta_usd: float

@dataclass(eq=False)
class RunResult:
    """Outcome of one engine run (§5.9)."""
    name: str
    policy: str
    seed: int
    components: dict[str, float]           # §5.6 component -> USD; 'total' included
    per_slot: dict[str, np.ndarray]        # component -> (T_slow,) USD
    leases: list[LeaseRecord]
    replicas: list[ReplicaRecord]
    events: list[tuple[int, str, dict]]    # (minute, type, payload), §5.9
    schedule: Schedule                     # realized announcement sets
    violations: list[dict]
    routing: Optional[dict]                # if EngineConfig.record_routing (§5.9); float64
    metrics: dict                          # online metric sums of the engine (§5.9)
    runtime: dict
    invariant_failures: list[str]
    # MS2 C5: {'config': inst.seed, 'lender': lender seed, 'policy': policy seed or 'injected'} (set by simulate)
    seeds: dict = field(default_factory=dict)

# ---------------------------------------------------------------- offline benchmarks
@dataclass(frozen=True)
class PlannedLease:
    """One lease of an offline plan (§8.10), replayed by policies.trivial.FixedPlan."""
    site: int; contract: int; llm: int
    start_slot: int                        # slow slot of purchase
    release_slot: Optional[int] = None     # slow slot of release; None = held until death/horizon
    n: int = 1                             # replicas (lease has n * g_j GPUs)
    admission_off: tuple[tuple[int, int], ...] = ()   # fast-slot intervals [a, b) with admission 0; disjoint, non-adjacent, sorted

@dataclass(eq=False)
class SolveResult:
    """Result of an offline benchmark solve (DP, MILP or LP, §8.8)."""
    method: Literal["milp", "lp", "dp", "core_milp", "core_lp"]
    benchmark: Literal["omega", "eager"]
    grid: str
    status: int                            # 0 optimal, 1 limit reached, 2 infeasible, 3 unbounded, 4 other
    status_msg: str
    objective: Optional[float]             # incumbent (MILP) or optimum (LP, DP)
    dual_bound: Optional[float]            # MILP dual bound; = objective for LP and DP
    gap: Optional[float]                   # (objective - dual_bound) / max(1, |objective|)
    plan: Optional[list[PlannedLease]]
    components: dict[str, float]           # §5.6 component names
    size: dict                             # n_vars, n_int, n_rows, nnz (MILP/LP); n_states (DP); rss_after_build_mb
    build_s: float
    solve_s: float
    peak_rss_mb: float
