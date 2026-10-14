"""Evaluation driver and GO / NO-GO gates per movement bin.

``evaluate`` builds the paired error table (``dtssl.eval.metrics``), computes the dense
median curves with moving-block-bootstrap CIs, the non-overlapping paired inference
(Wilcoxon + rank-biserial) and applies the verdict gates of ``config/metrics.json``:

    INDETERMINADO (omega placeholder)   misto/rot bins when theta["w"] is a placeholder
    SEM PODER (N=k)                     fewer than n_min_independent non-overlapping windows
    GO / NO-GO                          all criteria over h >= h_ref: direction, increasing gap,
                                        Wilcoxon p < alpha, effect >= effect_size_min, boot CI > 0

Random streams: one generator per (scope, curve), derived deterministically from
``bootstrap.seed`` (``dtssl.eval.stats.bootstrap_rng``). Medians, p-values, effect sizes
and the direction/increase criteria are independent of the streams; bootstrap CIs may
differ in the last digits from the 2026-08 runs (which used one shared generator).
"""
from __future__ import annotations

import numpy as np

from dtssl.eval.metrics import BIN_ORDER, bin_distribution, build_error_table, load_metrics_config
from dtssl.eval.stats import bootstrap_rng, moving_block_bootstrap, percentile_ci, rank_biserial, wilcoxon_less
from dtssl.models.params import load_twin_params

__all__ = ["evaluate", "verdict_bin", "SCOPES", "VERDICT_GO", "VERDICT_NO_GO",
           "VERDICT_INDETERMINATE", "VERDICT_NO_POWER"]

SCOPES = ("all",) + BIN_ORDER
CURVES = ("epos_twin", "epos_def", "eang_twin", "eang_def", "gap_epos")

VERDICT_GO = "GO"
VERDICT_NO_GO = "NO-GO"
VERDICT_INDETERMINATE = "INDETERMINADO (omega placeholder)"
VERDICT_NO_POWER = "SEM PODER"


# =========================================================================
def evaluate(twin_rollouts, default_rollouts, *, params=None, mcfg=None,
             robot_radius: float | None = None) -> dict:
    """Curves (dense), inference (non-overlapping + bootstrap) and verdict per bin.

    Returns ``{"table", "scopes", "verdicts", "bin_distribution", "mcfg", "params"}``.
    """
    params = params or load_twin_params()
    mcfg = mcfg or load_metrics_config()
    table = build_error_table(twin_rollouts, default_rollouts, params=params, mcfg=mcfg,
                              robot_radius=robot_radius)
    H = table.horizons
    nb = mcfg["bootstrap"]["n_boot"]; ci = mcfg["bootstrap"]["ci"]
    seed = mcfg["bootstrap"]["seed"]
    L = table.block_windows

    scopes = {}
    for si, scope in enumerate(SCOPES):
        rows = np.flatnonzero(table.mask(scope))
        indep_rows = np.flatnonzero(table.mask(scope) & table.indep)
        res = {"n_total": rows.size, "n_indep": indep_rows.size, "horizons": H,
               "horizons_s": H * table.ts}
        if rows.size == 0:
            scopes[scope] = res
            continue
        ept, epd = table.epos_twin, table.epos_def
        eat, ead = table.eang_twin, table.eang_def
        # --- curves (dense) ---
        res["epos_twin_med"] = np.median(ept[rows], 0)
        res["epos_def_med"] = np.median(epd[rows], 0)
        res["eang_twin_med"] = np.median(eat[rows], 0)
        res["eang_def_med"] = np.median(ead[rows], 0)
        res["gap_epos"] = res["epos_def_med"] - res["epos_twin_med"]
        # --- CI bands (moving-block bootstrap on the dense set), one rng per curve ---
        W = rows.size
        fns = {
            "epos_twin": lambda ix, a=ept: np.median(a[ix], 0),
            "epos_def": lambda ix, a=epd: np.median(a[ix], 0),
            "eang_twin": lambda ix, a=eat: np.median(a[ix], 0),
            "eang_def": lambda ix, a=ead: np.median(a[ix], 0),
            "gap_epos": lambda ix, a=ept, b=epd: np.median(b[ix], 0) - np.median(a[ix], 0),
        }
        for ci_idx, curve in enumerate(CURVES):
            rng = bootstrap_rng(seed, si, ci_idx)
            res[f"{curve}_ci"] = percentile_ci(
                moving_block_bootstrap(rows, table.seg_id, L, W, nb, rng, fns[curve]), ci)
        # --- inference (non-overlapping) ---
        p = np.ones(H.size); eff = np.zeros(H.size)
        if indep_rows.size >= 2:
            for k in range(H.size):
                p[k] = wilcoxon_less(ept[indep_rows, k], epd[indep_rows, k])
                eff[k] = rank_biserial(epd[indep_rows, k], ept[indep_rows, k])
        res["p_wilcoxon"] = p
        res["effect"] = eff
        # divergence: significant Wilcoxon but bootstrap CI of the gap includes 0
        sig = p < mcfg["verdict"]["alpha"]
        boot_excl0 = res["gap_epos_ci"][:, 0] > 0
        res["divergence"] = bool(np.any(sig & ~boot_excl0))
        scopes[scope] = res

    verdicts = {b: verdict_bin(b, scopes[b], params, mcfg) for b in BIN_ORDER}
    return {"table": table, "scopes": scopes, "verdicts": verdicts,
            "bin_distribution": bin_distribution(table), "mcfg": mcfg, "params": params}


# =========================================================================
def verdict_bin(bin_name: str, res: dict, params, mcfg) -> dict:
    """Apply the gates of ``mcfg["verdict"]`` to the scope result ``res`` of one bin."""
    h = np.asarray(res["horizons"]); h_ref = mcfg["verdict"]["h_ref"]
    n_min = mcfg["verdict"]["n_min_independent"]
    alpha = mcfg["verdict"]["alpha"]; eff_min = mcfg["verdict"]["effect_size_min"]
    out = {"bin": bin_name, "n_indep": res.get("n_indep", 0), "n_total": res.get("n_total", 0)}
    ref_mask = h >= h_ref
    if res.get("n_total", 0) and "gap_epos" in res:
        kref = int(np.flatnonzero(ref_mask)[0])
        out.update(gap_at_href=float(res["gap_epos"][kref]),
                   p_at_href=float(res["p_wilcoxon"][kref]),
                   effect_at_href=float(res["effect"][kref]))

    # PLACEHOLDER GATE (omega): misto and rot are indeterminate
    if params["w"].placeholder and bin_name in ("misto", "rot"):
        out["verdict"] = VERDICT_INDETERMINATE
        return out
    # POPULATION GATE
    if out["n_indep"] < n_min:
        out["verdict"] = f"{VERDICT_NO_POWER} (N={out['n_indep']})"
        return out
    # GO CRITERIA (over horizons >= h_ref)
    gap = res["gap_epos"][ref_mask]
    p = res["p_wilcoxon"][ref_mask]
    eff = res["effect"][ref_mask]
    boot_lo = res["gap_epos_ci"][ref_mask, 0]
    c_dir = bool(np.all(gap > 0))                                   # twin < default
    c_incr = bool(gap[-1] > gap[0] + 1e-9) and bool(np.all(np.diff(gap) > -1e-3))
    c_sig = bool(np.all(p < alpha))
    c_eff = bool(np.all(eff >= eff_min))
    c_boot = bool(np.all(boot_lo > 0))
    go = c_dir and c_incr and c_sig and c_eff and c_boot
    out["criteria"] = dict(direction=c_dir, increasing=c_incr, wilcoxon=c_sig,
                           effect=c_eff, bootstrap=c_boot)
    out["divergence"] = bool(res.get("divergence", False))
    out["verdict"] = VERDICT_GO if go else VERDICT_NO_GO
    return out


_verdict_bin = verdict_bin   # legacy private name
