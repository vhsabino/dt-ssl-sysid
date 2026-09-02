"""Hold-out fit figure for vx/vy (measured vs simulated P1D) — item (c) of 2026-07-31.

Read-only reproduction of the ``identify_trans_dof.m`` pipeline (``load_uy_trans``),
nothing is re-identified:

* grid ``t = t0:Ts:t1`` (t0 = max start, t1 = min end of commands/processed_robots),
  Ts = 1/60 (``matlab_colon``, same semantics as MATLAB); parquet + ``timestamp_event``;
* ``u = interp1(t_cmd, move_x|y, t, 'previous', 0)``;
* vision position mm -> m, linear interpolation; theta unwrapped before interpolating;
* Savitzky-Golay win=7 order=2 on px, py (as ``sgolayfilt``); vel = gradient/Ts;
  world -> body rotation by theta;
* promoted P1D (config/twin_params.json) simulated with
  ``common.simulate_fopdt(align="plant", upsample=20)``: fine grid Ts/20, delay
  by 'previous' shift, ZOH-exact lag, gain K — the same recurrence as
  ``AnalyticFOPDTPlant`` on the fine grid (fractional Td resolved to Ts/20);
* lag initial condition estimated by least squares (mirrors the estimated
  'InitialCondition' default of MATLAB ``compare``); fit also reported with zero IC;
* fit NRMSE = 100*(1 - ||y-yhat|| / ||y-mean(y)||) (``compare`` formula).

Hold-out events identical to sysid_vxvy_v2 (seed 42; confirmed bit-for-bit in
results/reidentificacao_20260724.md, PART A). PUBLICATION GATE: if any
|fit_py - fit_MATLAB| > 5 pp the figure is NOT copied to latex/figures/.

Legacy: scripts/fig_fit_holdout_vxvy.py -> results/fit_holdout_vxvy_20260731_024049.csv,
results/figs/fit_holdout_vxvy_20260731_024049.{png,pdf}.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

from dtssl.analysis import common as C
from dtssl.data.loader import event_dir
from dtssl.data.resample import interp_previous, matlab_colon

NAME = "fig_fit_holdout_vxvy"
KIND = "fig"
CLAIM = "Hold-out fit figure of vx/vy (Python reproduces MATLAB fits within 0.05 pp; not in the paper)"
REQUIRES = ("data",)

SG_WIN, SG_ORDER = 7, 2
UPSAMPLE = 20            # fine grid for the fractional delay + ZOH-exact lag
TOL_PP = 5.0             # divergence gate (percentage points)

# (dof, label, event, MATLAB reference fit — results/reidentificacao_20260724.md)
EVENTS = [
    ("vx", "front_to_back", "front_to_back_01_01", 86.7),
    ("vy", "side_to_side", "side_to_side_01_05", 86.8),
    ("vy", "side_to_side", "side_to_side_01_06", 86.3),
    ("vy", "side_to_side", "side_to_side_01_07", 87.3),
    ("vy", "side_to_side", "side_to_side_02_03", 88.1),
]


def load_uy(ctx: C.Ctx, label: str, event: str, dof: str, ts: float):
    """Read-only port of ``load_uy_trans`` (identify_trans_dof.m)."""
    d = event_dir(label, event, ctx.dataset, ctx.data_root)
    Cm = pd.read_parquet(d / "commands.parquet")
    rid = int(Cm["robot_id"].mode().iloc[0])
    Cm = Cm[Cm["robot_id"].astype("int64") == rid].sort_values("timestamp_event", kind="stable")
    R = pd.read_parquet(d / "processed_robots.parquet")
    R = R[(R["team"] == ctx.team) & (R["robot_id"].astype("int64") == rid)]
    R = R.sort_values("timestamp_event", kind="stable")
    tc = Cm["timestamp_event"].to_numpy(float)
    tr = R["timestamp_event"].to_numpy(float)
    t0, t1 = max(tc[0], tr[0]), min(tc[-1], tr[-1])
    t = matlab_colon(t0, t1, ts)
    cmdcol = "move_x" if dof == "vx" else "move_y"
    u = interp_previous(tc, Cm[cmdcol].to_numpy(float), t, 0.0)
    px = np.interp(t, tr, R["position_x"].to_numpy(float) / 1000.0)
    py = np.interp(t, tr, R["position_y"].to_numpy(float) / 1000.0)
    th = np.interp(t, tr, np.unwrap(R["position_w"].to_numpy(float)))
    win = min(SG_WIN, 2 * ((len(t) - 1) // 2) + 1)
    if win > SG_ORDER:
        px = savgol_filter(px, win, SG_ORDER)
        py = savgol_filter(py, win, SG_ORDER)
    vxw = np.gradient(px) / ts
    vyw = np.gradient(py) / ts
    y = np.cos(th) * vxw + np.sin(th) * vyw if dof == "vx" else -np.sin(th) * vxw + np.cos(th) * vyw
    m = ~(np.isnan(u) | np.isnan(y))
    return t[m] - t[m][0], u[m], y[m]


def compute(ctx: C.Ctx, events=EVENTS, upsample: int = UPSAMPLE) -> dict:
    ts = ctx.ts
    rows, panels = [], []
    for dof, label, event, fit_ref in events:
        p = ctx.params[dof]
        K, tau, Td = p.K, p.tau, p.Td
        t, u, y = load_uy(ctx, label, event, dof, ts)
        y0hat = C.simulate_fopdt(u, ts, K, tau, Td, ic=0.0, align="plant", upsample=upsample)
        b = K * np.exp(-t / tau)                       # response to the lag IC (pre-gain units)
        r = y - y0hat
        x0 = float(np.dot(r, b) / np.dot(b, b))        # least-squares IC (compare() default)
        yhat = y0hat + x0 * b
        f_est, f_zero = C.fit_percent(y, yhat), C.fit_percent(y, y0hat)
        rows.append(dict(dof=dof, event=event, K=K, tau=tau, Td=Td, n=len(t), x0=x0,
                         fit_est=f_est, fit_zero=f_zero, fit_ref=fit_ref, delta=f_est - fit_ref))
        panels.append((dof, event, t, y, yhat, f_est, fit_ref))
    ok = all(abs(r["delta"]) <= TOL_PP for r in rows)
    return dict(rows=rows, panels=panels, gate_ok=ok)


def write_csv(ctx: C.Ctx, rows) -> Path:
    csvp = ctx.out_path("fit_holdout_vxvy", "csv")
    with open(csvp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dof", "evento", "K", "tau_s", "Td_s", "n_amostras", "x0_lag_estimado",
                    "fit_py_ic_estimada_pct", "fit_py_ic_zero_pct", "fit_matlab_ref_pct", "delta_pp"])
        for r in rows:
            w.writerow([r["dof"], r["event"], f"{r['K']:.6f}", f"{r['tau']:.6f}", f"{r['Td']:.6f}",
                        r["n"], f"{r['x0']:.6f}", f"{r['fit_est']:.2f}", f"{r['fit_zero']:.2f}",
                        f"{r['fit_ref']:.1f}", f"{r['delta']:+.2f}"])
    return csvp


def figure(ctx: C.Ctx, panels) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
                         "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7})
    fig, axes = plt.subplots(len(panels), 1, figsize=(3.5, 7.6), sharex=False)
    axes = np.atleast_1d(axes)
    for ax, (dof, event, t, y, yhat, f_est, fit_ref) in zip(axes, panels):
        ax.plot(t, y, "-", color="0.55", lw=1.0, label="measured")
        ax.plot(t, yhat, "--", color="black", lw=1.2, label="simulated P1D")
        ax.set_ylabel(f"$v_{{{dof[1]}}}$ (m/s)")
        ax.set_title(f"{dof}: {event} — fit {f_est:.1f}%", loc="left", fontsize=8)
        ax.grid(alpha=0.3, lw=0.4)
        ax.margins(x=0.01)
    axes[0].legend(loc="best", frameon=True, framealpha=0.9)
    axes[-1].set_xlabel("t (s)")
    fig.tight_layout(h_pad=0.7)
    base = ctx.figs / f"fit_holdout_vxvy_{ctx.stamp}"
    fig.savefig(f"{base}.png", dpi=300)
    fig.savefig(f"{base}.pdf")
    plt.close(fig)
    return Path(f"{base}.png")


def run(root: Path | None = None, out: Path | None = None, *, latex_copy: bool = False,
        quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out, stamp_fmt=C.STAMP_FMT_S)
    r = compute(ctx)
    if not quiet:
        for x in r["rows"]:
            print(f"{x['dof']} {x['event']}: fit(IC est.)={x['fit_est']:.1f}%  fit(IC 0)={x['fit_zero']:.1f}%  "
                  f"MATLAB={x['fit_ref']:.1f}%  delta={x['delta']:+.1f} pp")
    csvp = write_csv(ctx, r["rows"])
    png = figure(ctx, r["panels"])
    copied = C.copy_figure(png, ctx, "fit_holdout_vxvy.png", latex_copy and r["gate_ok"])
    if not quiet:
        print(f"\nCSV:    {csvp}\nFigura: {png} / .pdf")
        if r["gate_ok"]:
            print(f"GATE OK (todas |delta| <= {TOL_PP} pp)" + (f" -> candidato copiado: {copied}" if copied else ""))
        else:
            print(f"GATE FALHOU (|delta| > {TOL_PP} pp em algum evento) -> figura NAO copiada para latex/figures/")
    return dict(path=png, csv=csvp, rows=r["rows"], gate_ok=r["gate_ok"], latex=copied)


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
