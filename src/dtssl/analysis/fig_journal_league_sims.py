"""Journal figure: the league simulators (grSim, ER-Force) replayed through the ssl-simulation-protocol on
the paper's hold-out windows, raw and with the pre-roll initial-condition protocol, in every session
that was run, against the identified model.

(a) median e_pos per horizon (translation bin) of the 20/09 session (thick) and the 18/09 session
(thin) for the simulators, with the model, the model with its states zeroed at t0 and the model under
the same pre-roll; (b) per-event medians at h_ref = 0.4 s, one marker per event and session.

Numbers only from the artefacts (``journal_artifacts``): results/protocol_holdout_20260910_0211.json (C2b),
results/protocol_holdout_20260918_1326.json and results/protocol_holdout_20260920_1143.json (C2b2, two
sessions of the same pre-registered design). Output: results/figs/fig_journal_league_sims_<stamp>.{pdf,png}
and latex_journal/figures/fig_journal_league_sims.pdf.
"""
from __future__ import annotations

from pathlib import Path

from dtssl.analysis import common as C
from dtssl.analysis import journal_artifacts as J

NAME = "fig_journal_league_sims"
KIND = "fig"
CLAIM = "Journal Fig.: model vs grSim / ER-Force (raw, pre-rolled, every session) on the hold-out (C2b/C2b2)"
REQUIRES: tuple[str, ...] = ()
SIMS = (("grsim", "grSim, teleport from rest", "#ff7f0e", "-"), ("grsim+preroll", "grSim, pre-rolled", "#ff7f0e", "--"),
        ("erforce", "ER-Force, teleport", "#2ca02c", "-"), ("erforce+preroll", "ER-Force, pre-rolled", "#2ca02c", "--"))
PANEL_B = (("model", "Model"), ("grsim", "grSim"), ("grsim+preroll", "grSim\npre-rolled"),
           ("grsim+delay", "grSim\n+ delay"), ("erforce", "ER-Force"), ("erforce+preroll", "ER-Force\npre-rolled"),
           ("erforce+delay", "ER-Force\n+ delay"))
SESSION_MARK = {"c2b": ("^", "2026-09-10"), "c2b2_s1": ("o", "2026-09-18"), "c2b2_s2": ("s", "2026-09-20")}


def data(root: Path | None = None) -> dict:
    return {k: J.league_session(k, root) for k in ("c2b", "c2b2_s1", "c2b2_s2")}


def make_figure(d: dict):
    J.figure_style()
    import matplotlib.pyplot as plt

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(190 * J.MM, 66 * J.MM), gridspec_kw=dict(width_ratios=[1.0, 1.25]))
    s2, s1 = d["c2b2_s2"], d["c2b2_s1"]
    hs = s2["horizons_s"]
    ax.plot(hs, s2["model_epos"], color="k", marker="o", ms=2.5, label="Model (identified FOPDT)")
    ax.plot(hs, s2["model_prerolled"], color="k", ls=":", marker="o", ms=2.0, mfc="white", label="Model, pre-rolled")
    ax.plot(hs, s2["model_states_zeroed"], color="0.55", ls="-.", label="Model, states zeroed at $t_0$")
    for key, label, color, ls in SIMS:
        ax.plot(hs, s2["variants"][key]["epos"], color=color, ls=ls, marker="s", ms=2.3, label=label)
        ax.plot(hs, s1["variants"][key]["epos"], color=color, ls=ls, lw=0.6, alpha=0.6)
    ax.set_xlabel("horizon (s)")
    ax.set_ylabel(r"median $e_{\mathrm{pos}}$ (m)")
    ax.set_xlim(0.0, max(hs) + 0.05)
    ax.set_ylim(0.0, None)
    ax.grid(alpha=0.35)
    ax.legend(loc="upper left", frameon=False, handlelength=2.2)
    ax.set_title("(a) per horizon, session 2026-09-20 (thin: 2026-09-18)", loc="left")

    positions = {k: i for i, (k, _) in enumerate(PANEL_B)}
    for skey, (marker, _date) in SESSION_MARK.items():
        S = d[skey]
        dx = {"c2b": -0.2, "c2b2_s1": 0.0, "c2b2_s2": 0.2}[skey]
        if skey == "c2b2_s2":
            xs = [positions["model"] + dx * 0] * len(S["model_event_values"])
            bx.scatter(xs, S["model_event_values"], s=9, marker="D", color="k", zorder=3, label="Model (all sessions)")
        for key, _ in PANEL_B[1:]:
            v = S["variants"].get(key)
            if v is None:
                continue
            color = "#ff7f0e" if key.startswith("grsim") else "#2ca02c"
            bx.scatter([positions[key] + dx] * len(v["event_values"]), v["event_values"], s=9, marker=marker,
                       facecolors="white" if skey == "c2b" else color, edgecolors=color, linewidths=0.7, zorder=3)
            bx.hlines(v["event_median"], positions[key] + dx - 0.08, positions[key] + dx + 0.08, color="k", lw=1.0,
                      zorder=4)
    for skey, (marker, date) in SESSION_MARK.items():
        bx.scatter([], [], marker=marker, s=12, facecolors="white" if skey == "c2b" else "0.5", edgecolors="0.3",
                   label=f"session {date}")
    bx.hlines(d["c2b2_s2"]["model_event_median"], -0.12, 0.12, color="k", lw=1.0)
    bx.set_xticks(range(len(PANEL_B)))
    bx.set_xticklabels([lab for _, lab in PANEL_B])
    bx.set_ylabel(r"per-event median $e_{\mathrm{pos}}$ at 0.4 s (m)")
    bx.set_ylim(0.0, None)
    bx.grid(axis="y", alpha=0.35)
    bx.legend(loc="upper right", frameon=False, handletextpad=0.2)
    bx.set_title("(b) per event at $h_{\\mathrm{ref}}$; bars: medians over events", loc="left")
    fig.tight_layout(w_pad=1.2)
    return fig


def run(root: Path | None = None, out: Path | None = None, *, latex_copy: bool = True, quiet: bool = False,
        **kw) -> dict:
    ctx = C.make_context(root, out)
    d = data(ctx.root)
    fig = make_figure(d)
    paths = J.save_figure(fig, ctx, NAME, latex_copy=latex_copy)
    import matplotlib.pyplot as plt

    plt.close(fig)
    if not quiet:
        print(f"figura: {paths['pdf']}")
    return dict(path=paths["pdf"], paths=paths)


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
