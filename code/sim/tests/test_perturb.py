"""Tests of E4's perturbation generators and q-eta, sublet/drivers/perturb.py (design/sim_spec_ms4.md §6.4, §6.8,
§10 row test_e4.py, test_perturb.py; M11, M12).

- The 13 prediction keys of §6.4 in order, their labels (information classes) and that each is a valid job-id part.
- Each generator against hand values on small arrays: the previous-day base with day 0 empty, phase with a zero head
  and no wrap, amplitude, deletion at the day's P90, injection of 3 bursts of 30 min at the day's P99 with the window
  starts of np.random.default_rng((c, d)), empty and the oracle; the parameter checks.
- q eta_d on hand masks: active units of the slot maxima (instance.active_units) weighted by q_{j_c} / u Δs / 60, per
  day and summed, with phi > 1 (slot maxima of the fast slots) and the core form q Δs / 60 |sigma triangle
  sigma-hat| for u = 1 and 0/1 demand; the exact prediction has eta 0.
"""
from types import SimpleNamespace

import numpy as np
import pytest

from sublet.drivers import perturb
from sublet.experiments import ms3_common as mc

KEYS = ("prev", "phase15", "phase30", "phase60", "phase120", "amp0.5", "amp0.75", "amp1.25", "amp1.5", "del_p90",
        "inj3x30", "empty", "exact")


def test_keys_labels_and_id_parts():
    assert tuple(perturb.PREDICTIONS) == KEYS
    assert perturb.LABELS["prev"] == "previous-day" and perturb.LABELS["exact"] == "exact"
    assert perturb.LABELS["phase15"] == "perturbation:phase:15"
    assert perturb.LABELS["amp0.75"] == "perturbation:amplitude:0.75"
    assert perturb.LABELS["del_p90"] == "perturbation:burst_delete:P90"
    assert perturb.LABELS["inj3x30"] == "perturbation:burst_inject:3x30min-P99"
    assert perturb.LABELS["empty"] == "perturbation:empty" and perturb.LABELS[perturb.NONE_KEY] == "none"
    assert len(set(perturb.LABELS.values())) == len(perturb.LABELS) == 14
    for k in KEYS + (perturb.NONE_KEY,):
        assert mc.parse_job_id(mc.job_id("e4", "x", pred=k))[2] == {"pred": k}
    with pytest.raises(ValueError):
        perturb.spec("phase45")


def _demand():
    """3 days of 6 fast slots (Δf = 5 min) for one client."""
    return np.array([[1, 2, 3, 4, 5, 6, 6, 5, 4, 3, 2, 1, 0, 1, 0, 2, 0, 3]], dtype=float)


def _pred(key, c=1):
    return perturb.prediction(_demand(), key, day_fast=6, fast_min=5, c=c)


def test_previous_day_phase_amplitude_empty_exact_by_hand():
    d = _demand()
    z = [0.0] * 6
    assert _pred("prev").tolist() == [z + [1, 2, 3, 4, 5, 6] + [6, 5, 4, 3, 2, 1]]
    # phase 15 min = 3 fast slots: the day's prediction shifted right, the first 3 slots 0, nothing wraps
    assert _pred("phase15").tolist() == [z + [0, 0, 0, 1, 2, 3] + [0, 0, 0, 6, 5, 4]]
    assert _pred("phase30").tolist() == [z * 3]                     # 6 slots: the whole day
    assert _pred("phase120").tolist() == [z * 3]
    assert _pred("amp0.5").tolist() == [z + [0.5, 1, 1.5, 2, 2.5, 3] + [3, 2.5, 2, 1.5, 1, 0.5]]
    assert _pred("amp1.25").tolist() == [z + [1.25 * x for x in (1, 2, 3, 4, 5, 6)]
                                         + [1.25 * x for x in (6, 5, 4, 3, 2, 1)]]
    assert _pred("empty").tolist() == [z * 3]
    assert _pred("exact").tolist() == [z + d[0, 6:].tolist()]       # the realized days 1 and 2; day 0 has none
    # the last day may be shorter than a day
    p = perturb.prediction(d[:, :15], "phase15", day_fast=6, fast_min=5, c=1)
    assert p.tolist() == [z + [0, 0, 0, 1, 2, 3] + [0, 0, 0]]


def test_burst_delete_at_the_days_p90():
    w = np.arange(1.0, 11.0)[None, :]                               # P90 (linear interpolation) = 9.1
    out = perturb.perturb_day(w, "burst_delete", 90, fast_min=5)
    assert out.tolist() == [[1, 2, 3, 4, 5, 6, 7, 8, 9, 9.1]]
    two = np.vstack([w, 2 * w])                                     # per client
    assert perturb.perturb_day(two, "burst_delete", 90, fast_min=5)[1, -1] == pytest.approx(18.2)
    flat = np.zeros((1, 6))
    assert perturb.perturb_day(flat, "burst_delete", 90, fast_min=5).tolist() == [[0.0] * 6]


def test_burst_inject_three_windows_at_the_days_p99():
    w = np.arange(24.0)[None, :]                                    # a 2-h day of 5-min slots; P99 = 22.77
    starts = perturb.inject_starts(1, 1, 24, 3, 6)
    assert starts.tolist() == [9, 6, 6]                             # default_rng((1, 1)).integers(0, 19, size=3)
    assert starts.tolist() == np.random.default_rng((1, 1)).integers(0, 19, size=3).tolist()
    out = perturb.perturb_day(w, "burst_inject", (3, 30, 99), fast_min=5, c=1, d=1)
    exp = w.copy()
    exp[0, 6:15] = 22.77                                            # windows [9, 15), [6, 12), [6, 12)
    assert np.allclose(out, exp, rtol=0, atol=1e-12)
    # the same draws for every call (every policy and seed), other draws at another (c, d)
    assert np.array_equal(out, perturb.perturb_day(w, "burst_inject", (3, 30, 99), fast_min=5, c=1, d=1))
    assert perturb.inject_starts(2, 3, 24, 3, 6).tolist() == [18, 6, 4]
    # through prediction(): day d of alignment c uses default_rng((c, d)) on the previous day's values
    d = np.tile(np.arange(24.0), 3)[None, :]
    p = perturb.prediction(d, "inj3x30", day_fast=24, fast_min=5, c=2)
    for day in (1, 2):
        exp = d[:, :24].copy()
        for s0 in perturb.inject_starts(2, day, 24, 3, 6):
            exp[0, s0:s0 + 6] = np.maximum(exp[0, s0:s0 + 6], np.percentile(d[0, :24], 99))
        assert np.allclose(p[:, day * 24:(day + 1) * 24], exp, rtol=0, atol=1e-12)
    assert not p[:, :24].any()
    # a day shorter than a window: one window over the whole day
    assert perturb.inject_starts(1, 1, 4, 3, 6).tolist() == [0, 0, 0]


def test_parameter_checks():
    w = np.ones((1, 6))
    with pytest.raises(ValueError):
        perturb.perturb_day(w, "phase", 7, fast_min=5)               # not a multiple of Δf
    with pytest.raises(ValueError):
        perturb.perturb_day(w, "amplitude", -1.0, fast_min=5)
    with pytest.raises(ValueError):
        perturb.perturb_day(w, "burst_inject", (3, 30, 99), fast_min=5)   # needs (c, d)
    with pytest.raises(ValueError):
        perturb.perturb_day(w, "exact", None, fast_min=5)            # needs the realized day
    with pytest.raises(ValueError):
        perturb.perturb_day(w, "flood", None, fast_min=5)
    with pytest.raises(ValueError):
        perturb.prediction(_demand(), "phase45", day_fast=6, fast_min=5, c=1)


def _stub(T_slow, phi, u, q, llm):
    g = SimpleNamespace(slow_min=5 * phi, fast_min=5, phi=phi, T_slow=T_slow, T_fast=T_slow * phi)
    return SimpleNamespace(grid=g, n=len(llm), units_per_replica=u,
                           llms=[SimpleNamespace(q_usd_per_h=float(x)) for x in q],
                           clients=SimpleNamespace(llm=np.asarray(llm, dtype=np.int64)))


def test_eta_q_on_hand_masks():
    inst = _stub(4, 1, 2, (8.0, 4.0), (0, 1))
    real = np.array([[0.5, 1.0, 0.0, 0.25], [0.0, 1.5, 1.5, 0.5]])
    pred = np.array([[1.0, 1.0, 0.5, 0.0], [0.0, 0.0, 1.5, 1.0]])
    # active units ceil(2 D): client 0 [1, 2, 0, 1] vs [2, 2, 1, 0] (3 unit-slots apart), client 1 [0, 3, 3, 1] vs
    # [0, 0, 3, 2] (4); weights q / u Δs / 60 = 8 / 2 / 12 = 1/3 and 4 / 2 / 12 = 1/6
    assert perturb.eta_q(inst, real, pred, 0, day_slots=4) == pytest.approx(3 / 3 + 4 / 6, rel=1e-12)
    d0 = perturb.eta_q(inst, real, pred, 0, day_slots=2)            # slots 0-1: 1 and 3 unit-slots apart
    d1 = perturb.eta_q(inst, real, pred, 1, day_slots=2)            # slots 2-3: 2 and 1
    assert d0 == pytest.approx(1 / 3 + 3 / 6, rel=1e-12) and d1 == pytest.approx(2 / 3 + 1 / 6, rel=1e-12)
    assert perturb.eta_q_days(inst, real, pred, 2) == pytest.approx([d0, d1], rel=1e-12)
    assert perturb.eta_q(inst, real, real, 0, day_slots=4) == 0.0
    with pytest.raises(ValueError):
        perturb.eta_q(inst, real, pred, 2, day_slots=2)
    # phi = 2: the slot maxima of the fast slots (Δs = 10 min)
    inst2 = _stub(2, 2, 2, (6.0,), (0,))
    real2 = np.array([[0.2, 0.6, 1.0, 0.0]])                         # slot maxima 0.6, 1.0 -> units 2, 2
    pred2 = np.array([[0.0, 0.4, 0.0, 0.3]])                         # 0.4, 0.3 -> units 1, 1
    assert perturb.eta_q(inst2, real2, pred2, 0, day_slots=2) == pytest.approx(6.0 / 2 * 10 / 60 * 2, rel=1e-12)
    # u = 1, 0/1 demand: the core form q Δs / 60 |sigma triangle sigma-hat| (repro_c5_la.py's
    # (I.active ^ Ip.active).sum())
    inst3 = _stub(6, 1, 1, (12.0,), (0,))
    a = np.array([[1, 0, 1, 1, 0, 0]], dtype=float)
    b = np.array([[1, 1, 0, 1, 0, 1]], dtype=float)
    assert perturb.eta_q(inst3, a, b, 0, day_slots=6) == pytest.approx(12.0 * 5 / 60 * int((a != b).sum()))


def test_pred_sha256_changes_with_the_prediction():
    a, b = _pred("prev"), _pred("amp1.5")
    assert perturb.pred_sha256(a) == perturb.pred_sha256(a.copy()) != perturb.pred_sha256(b)
