"""Figures and Markdown report of the evaluation harness (+ single-event replay outputs).

``make_figures``/``markdown_report`` consume the dict returned by ``dtssl.eval.evaluate``.
``replay_csv``/``replay_figure`` serve ``dtssl replay`` (free-run of one event vs truth).
matplotlib is imported lazily (Agg backend) so importing the package never needs a display.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from dtssl.eval.metrics import BIN_LABEL, BIN_ORDER, pose_errors

__all__ = ["make_figures", "markdown_report", "replay_csv", "replay_figure"]


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


# =========================================================================
def make_figures(result: dict, outdir, stamp: str) -> list:
    """e_pos and e_ang vs horizon (twin vs default) with CI bands; aggregate and per bin.
    Saves PNG + SVG. Returns the PNG paths."""
    plt = _plt()
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    files = []
    C_TWIN, C_DEF = (0.10, 0.30, 0.65), (0.40, 0.40, 0.40)
    for scope in ("all",) + BIN_ORDER:
        res = result["scopes"][scope]
        if res.get("n_total", 0) == 0 or "epos_twin_med" not in res:
            continue
        hs = res["horizons_s"]
        fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
        for a, key, ttl, ylab in ((ax[0], "epos", "RMSE posicao", "e_pos mediana (m)"),
                                   (ax[1], "eang", "erro heading", "e_ang mediana (rad)")):
            tw, df = res[f"{key}_twin_med"], res[f"{key}_def_med"]
            tw_ci, df_ci = res[f"{key}_twin_ci"], res[f"{key}_def_ci"]
            a.fill_between(hs, df_ci[:, 0], df_ci[:, 1], color=C_DEF, alpha=0.18)
            a.fill_between(hs, tw_ci[:, 0], tw_ci[:, 1], color=C_TWIN, alpha=0.18)
            a.plot(hs, df, "-o", color=C_DEF, lw=1.8, label="ideal (default)")
            a.plot(hs, tw, "-d", color=C_TWIN, lw=2.0, label="twin (FOPDT)")
            a.set_xlabel("horizonte h (s)"); a.set_ylabel(ylab); a.set_title(ttl)
            a.grid(alpha=0.3); a.legend(loc="upper left")
        vb = result["verdicts"].get(scope)
        vtxt = f" — {vb['verdict']}" if vb else ""
        fig.suptitle(f"Fidelidade vs horizonte [{BIN_LABEL.get(scope, 'TODOS')}] "
                     f"(N={res['n_total']}, indep={res['n_indep']}){vtxt}")
        fig.tight_layout()
        base = outdir / f"M1_metrics_{scope}_{stamp}"
        fig.savefig(f"{base}.png", dpi=150); fig.savefig(f"{base}.svg")
        plt.close(fig)
        files.append(f"{base}.png")
    return files


def markdown_report(result: dict, fig_files=None) -> str:
    mcfg = result["mcfg"]; href = mcfg["verdict"]["h_ref"]
    nmin = mcfg["verdict"]["n_min_independent"]; ts = result["table"].ts
    L = ["# Relatorio — metrica SE(2) multi-horizonte (dtssl.eval)",
         "",
         f"Config: horizontes(amostras)={list(result['table'].horizons)} "
         f"(s={[round(float(x),3) for x in result['table'].horizons*ts]}), "
         f"h_ref={href}, N_min={nmin}, alpha={mcfg['verdict']['alpha']}, "
         f"effect_min={mcfg['verdict']['effect_size_min']}, bloco_MBB={result['table'].block_windows} janelas.",
         "", "## Distribuicao de bins", "",
         "| bin | total (densas) | independentes |", "|---|---:|---:|"]
    d = result["bin_distribution"]
    for b in BIN_ORDER:
        L.append(f"| {BIN_LABEL[b]} | {d[b]['total']} | {d[b]['indep']} |")
    L.append(f"| **TODOS** | {d['all']['total']} | {d['all']['indep']} |")

    for scope in ("all",) + BIN_ORDER:
        res = result["scopes"][scope]
        L += ["", f"## {BIN_LABEL.get(scope,'TODOS (agregado)')}"]
        if res.get("n_total", 0) == 0 or "epos_twin_med" not in res:
            L.append("_(sem janelas)_"); continue
        L.append(f"N total={res['n_total']}, independentes={res['n_indep']}")
        L += ["", "| h (s) | twin e_pos | ideal e_pos | gap (m) | gap CI | p (nao-sobr.) | effect |",
              "|---:|---:|---:|---:|---:|---:|---:|"]
        for k, h in enumerate(res["horizons"]):
            cik = res["gap_epos_ci"][k]
            L.append(f"| {h*ts:.2f} | {res['epos_twin_med'][k]:.4f} | {res['epos_def_med'][k]:.4f} "
                     f"| {res['gap_epos'][k]:+.4f} | [{cik[0]:+.4f},{cik[1]:+.4f}] "
                     f"| {res['p_wilcoxon'][k]:.3g} | {res['effect'][k]:+.3f} |")
        if res.get("divergence"):
            L.append("\n> ⚠ DIVERGENCIA: Wilcoxon significativo mas bootstrap CI inclui 0 em algum h "
                     "(a sobreposicao pode estar enganando).")

    L += ["", "## Vereditos por bin (gates aplicados)", "",
          "| bin | veredito | N indep | gap@h_ref | p@h_ref | effect@h_ref |",
          "|---|---|---:|---:|---:|---:|"]
    for b in BIN_ORDER:
        v = result["verdicts"][b]
        g = f"{v.get('gap_at_href'):+.4f}" if v.get("gap_at_href") is not None else "-"
        pp = f"{v.get('p_at_href'):.3g}" if v.get("p_at_href") is not None else "-"
        ee = f"{v.get('effect_at_href'):+.3f}" if v.get("effect_at_href") is not None else "-"
        L.append(f"| {BIN_LABEL[b]} | {v['verdict']} | {v['n_indep']} | {g} | {pp} | {ee} |")
    if fig_files:
        L += ["", "## Figuras"] + [f"- `{f}`" for f in fig_files]
    return "\n".join(L) + "\n"


# =========================================================================
# Single-event replay (dtssl replay)
def replay_csv(seg, pose_sim: np.ndarray, path) -> Path:
    """Per-sample CSV: t, commands, real pose, simulated pose, e_pos, e_ang."""
    import pandas as pd
    pose_sim = np.asarray(pose_sim, dtype=float)
    n = pose_sim.shape[0]
    pose_real = np.column_stack([seg.pos_x[:n], seg.pos_y[:n], seg.theta[:n]])
    epos, eang = pose_errors(pose_sim, pose_real)
    df = pd.DataFrame({
        "t": seg.t[:n], "cmd_vx": seg.cmd_vx[:n], "cmd_vy": seg.cmd_vy[:n], "cmd_w": seg.cmd_w[:n],
        "x_real": pose_real[:, 0], "y_real": pose_real[:, 1], "theta_real": pose_real[:, 2],
        "x_sim": pose_sim[:, 0], "y_sim": pose_sim[:, 1], "theta_sim": pose_sim[:, 2],
        "e_pos": epos, "e_ang": eang,
    })
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def replay_figure(seg, pose_sim: np.ndarray, path, title: str | None = None,
                  horizon_table: dict | None = None) -> Path:
    """XY trajectory (truth vs free-run) + e_pos(t)/e_ang(t); optional per-horizon medians inset."""
    plt = _plt()
    pose_sim = np.asarray(pose_sim, dtype=float)
    n = pose_sim.shape[0]
    pose_real = np.column_stack([seg.pos_x[:n], seg.pos_y[:n], seg.theta[:n]])
    epos, eang = pose_errors(pose_sim, pose_real)
    t = seg.t[:n] - seg.t[0]

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    ax[0].plot(pose_real[:, 0], pose_real[:, 1], "-", color=(0.4, 0.4, 0.4), lw=1.8, label="verdade (visao)")
    ax[0].plot(pose_sim[:, 0], pose_sim[:, 1], "--", color=(0.10, 0.30, 0.65), lw=1.8, label="free-run")
    ax[0].plot(pose_real[0, 0], pose_real[0, 1], "o", color="k", ms=5)
    ax[0].set_aspect("equal", adjustable="datalim")
    ax[0].set_xlabel("x (m)"); ax[0].set_ylabel("y (m)"); ax[0].grid(alpha=0.3); ax[0].legend(loc="best")
    ax[1].plot(t, epos, color=(0.10, 0.30, 0.65), lw=1.6, label="e_pos (m)")
    ax[1].set_xlabel("t desde t0 (s)"); ax[1].set_ylabel("e_pos (m)"); ax[1].grid(alpha=0.3)
    ax2 = ax[1].twinx()
    ax2.plot(t, eang, color=(0.75, 0.25, 0.15), lw=1.2, alpha=0.8, label="e_ang (rad)")
    ax2.set_ylabel("e_ang (rad)")
    h1, l1 = ax[1].get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax[1].legend(h1 + h2, l1 + l2, loc="upper left")
    fig.suptitle(title or f"replay {seg.meta.get('event', '?')}")
    if horizon_table:
        txt = "mediana de e_pos por horizonte (janelas):  " + "   ".join(
            f"{h:.2f}s: {v:.3f} m" for h, v in horizon_table.items())
        fig.text(0.5, 0.01, txt, ha="center", va="bottom", fontsize=8.5, family="monospace")
        fig.tight_layout(rect=(0, 0.05, 1, 1))
    else:
        fig.tight_layout()
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
