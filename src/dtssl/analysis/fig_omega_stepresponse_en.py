"""Yaw step-response figure (Fig. 1 of the paper): measured vs FOPDT model for
three ``rotate`` events (1 train + 2 hold-out, split of
results/identificacao_omega_20260724.md).

Measured omega = ``gradient(savgol(theta, 7, 2))/dt`` on the legacy ``np.arange``
grid (``common.legacy_uy_series``; CSV when present else parquet); model =
promoted omega P1D through ``common.simulate_fopdt(align="legacy")`` (the
recurrence the legacy script used, one sample less transport delay than
``AnalyticFOPDTPlant`` — see common.py).

Legacy: scripts/fig_omega_stepresponse_en.py -> results/figs/omega_stepresponse_en.png.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from dtssl.analysis import common as C

NAME = "fig_omega_stepresponse_en"
KIND = "fig"
CLAIM = "Yaw step response, measured vs FOPDT (Fig. 1)"
REQUIRES = ("data",)
LABEL = "rotate"
# 3 panels: 1 train + 2 hold-out
PANELS = [("rotate_01_09", "train", "+5.0"), ("rotate_01_06", "hold-out", "-1.0"),
          ("rotate_01_07", "hold-out", "+2.5")]


def compute(ctx: C.Ctx, panels=PANELS, align: str = "legacy") -> list[dict]:
    p = ctx.params["w"]
    dt = ctx.ts
    out = []
    for ev, kind, amp in panels:
        cmd, rob = C.read_event_csv(LABEL, ev, dataset=ctx.dataset, data_root=ctx.data_root)
        s = C.legacy_uy_series(cmd, rob, "w", dt, min_len=1)
        if s is None:
            continue
        u, meas = s
        sim = C.simulate_fopdt(u, dt, p.K, p.tau, p.Td, align=align)
        tg = np.arange(len(u)) * dt
        out.append(dict(event=ev, kind=kind, amp=amp, t=tg, meas=meas, sim=sim,
                        fit=C.fit_percent(meas, sim)))
    return out


def figure(ctx: C.Ctx, panels: list[dict], name: str = "omega_stepresponse_en.png") -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(panels), 1, figsize=(3.5, 4.6), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, pn in zip(axes, panels):
        ax.plot(pn["t"], pn["meas"], color="0.25", lw=0.7, label="measured")
        ax.plot(pn["t"], pn["sim"], "r--", lw=1.3, label="FOPDT model")
        ax.set_ylabel(r"$\omega$ (rad/s)", fontsize=8)
        ax.tick_params(labelsize=7); ax.grid(alpha=.3, lw=.4)
        ax.set_title(f"{pn['amp']} rad/s step ({pn['kind']})", fontsize=8, pad=2)
    axes[0].legend(fontsize=7, loc="lower right", framealpha=.9)
    axes[-1].set_xlabel("time from step onset (s)", fontsize=8)
    plt.tight_layout(pad=0.3)
    o = ctx.figs / name
    plt.savefig(o, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return o


def run(root: Path | None = None, out: Path | None = None, *, align: str = "legacy",
        latex_copy: bool = False, quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    panels = compute(ctx, align=align)
    png = figure(ctx, panels)
    copied = C.copy_figure(png, ctx, png.name, latex_copy)
    if not quiet:
        for pn in panels:
            print(f"{pn['event']} ({pn['kind']}, {pn['amp']} rad/s): NRMSE fit over the padded split "
                  f"= {pn['fit']:.1f} % (diagnostic only, NOT the paper's hold-out fit; align={align})")
        print("gerada:", png)
    return dict(path=png, latex=copied, fits={pn["event"]: pn["fit"] for pn in panels}, align=align)


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
