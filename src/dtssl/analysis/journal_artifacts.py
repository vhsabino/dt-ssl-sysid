"""Numbers of the journal manuscript, read from the result artefacts (no recomputation, no dataset).

Every figure and table of the journal extension (``fig_journal_*``, ``journal_tables``) takes its numbers
from here, and here only from files in ``results/`` named in :data:`ARTEFACTS` (JSON when the artefact
has one, otherwise the Markdown table the analysis wrote). A number that is not in one of these files
does not reach the manuscript. ``tests/test_journal_artifacts.py`` pins the values against the
``results/CHANGELOG.md`` entries.
"""
from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import Any

from dtssl.paths import repo_root

#: artefact of each result (file name in ``results/``)
ARTEFACTS: dict[str, str] = {
    # SBR/LARS 2026 (June to August 2026)
    "three_models": "epos_eang_three_models_20260810_1022.md",
    "clustered": "clustered_stats_20260809_2309.md",
    "gate": "gate_window_vs_event_20260810_1743.md",
    "shapley": "ablation_orderfree_20260810_1021.md",
    "causal": "causal_ic_check_20260810_1102.md",
    "loo": "loo_translational_20260810_1743.md",
    "r3": "r3_closedloop_omega_fit_20260810_1036.md",
    "negctl": "negcontrol_perevent_20260810_1035.md",
    "rsim_delay": "eval_rsim_delay_ablation_20260809_2154.md",
    "excitation": "excitation_per_dof_20260810_1022.md",
    # September 2026 (C1, C1b, C2a, B3, C4, C2b, C2b2)
    "c1": "identifiability_insilico_20260907_1552.json",
    "c1b_delay": "identifiability_insilico_mujoco-rollers-delay_v2_20260907_2044.json",
    "c1b_nodelay": "identifiability_insilico_mujoco-rollers_v2_20260907_2048.json",
    "c2a": "backends_holdout_20260907_1515.md",
    "c2a_csv": "backends_holdout_20260907_1515.csv",
    "b3": "session_report_sessao_01_20260907_2059.json",
    "c4": "closed_loop_stats_20260907_2137.json",
    "c2b": "protocol_holdout_20260910_0211.json",
    "c2b2_s1": "protocol_holdout_20260918_1326.json",
    "c2b2_s2": "protocol_holdout_20260920_1143.json",
    # October 2026 (WP2: pre-registered MIMO check on the competition logs and its two in-silico controls)
    "mimo": "coupled_mimo_check_20261014_1211.json",
    "mimo_cminus": "coupled_mimo_check_control-fopdt_20261014_1211.json",
    "mimo_cplus": "coupled_mimo_check_control-mujoco-rollers-delay_20261014_1216.json",
}
#: sessions of the league-simulator replays (C2b on 10/09; C2b2 run twice, 18/09 and 20/09)
SESSIONS = {"c2b": "2026-09-10", "c2b2_s1": "2026-09-18", "c2b2_s2": "2026-09-20"}
H_REF_S = 0.4


def results_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "results"


def path(key: str, root: Path | None = None) -> Path:
    return results_dir(root) / ARTEFACTS[key]


def available(key: str, root: Path | None = None) -> bool:
    return path(key, root).is_file()


@cache
def _json(p: str) -> Any:
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_json(key: str, root: Path | None = None) -> Any:
    return _json(str(path(key, root)))


def md_tables(text: str) -> list[list[list[str]]]:
    """Every pipe table of a Markdown text as rows of stripped cells (separator rows dropped)."""
    tables, cur = [], []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
                continue
            cur.append(cells)
        elif cur:
            tables.append(cur)
            cur = []
    if cur:
        tables.append(cur)
    return tables


def _md(key: str, root: Path | None = None) -> str:
    return path(key, root).read_text(encoding="utf-8")


def _num(s: str) -> float:
    """First number of a cell (``**0.039**``, ``+0.0689``, ``44.8 %`` -> float)."""
    m = re.search(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", s.replace("**", ""))
    if m is None:
        raise ValueError(f"no number in {s!r}")
    return float(m.group(0))


# =========================================================================
# SBR results (Markdown artefacts)
# =========================================================================
def three_models(root: Path | None = None) -> list[dict]:
    """Per horizon: median e_pos / e_ang of the model, ideal kinematics and rSim (translation bin)."""
    t = md_tables(_md("three_models", root))[0]
    out = []
    for r in t[1:]:
        h, tp, ip, rp, ta, ia, ra = (_num(c) for c in r[:7])
        out.append(dict(h_s=h, epos=dict(model=tp, ideal=ip, rsim=rp), eang=dict(model=ta, ideal=ia, rsim=ra)))
    return out


def clustered(root: Path | None = None) -> dict:
    """Per-event medians model vs ideal at h_ref (the paper's unit of analysis) and the test."""
    text = _md("clustered", root)
    t = md_tables(text)[0]
    events = [dict(idx=int(_num(r[0])), model=_num(r[1]), ideal=_num(r[2]), gap=_num(r[3]), windows=int(_num(r[4])))
              for r in t[1:]]
    p = _num(re.search(r"p = \*?\*?([0-9.eE+-]+)", text).group(1))
    gap = _num(re.search(r"Gap mediano por evento: \*\*([+0-9.]+) m", text).group(1))
    ci = re.search(r"IC95% bootstrap por evento \[([+0-9.-]+), ([+0-9.-]+)\]", text)
    seconds = _num(re.search(r"= \*\*([0-9.]+) s\*\*", text).group(1))
    return dict(events=events, p=p, gap=gap, ci=(_num(ci.group(1)), _num(ci.group(2))), seconds=seconds)


def gate(root: Path | None = None) -> dict:
    t = md_tables(_md("gate", root))[0]
    rows = {}
    for r in t[1:]:
        key = "window" if "janela" in r[0] else "event"
        ci = re.findall(r"[-+]?\d+\.\d+", r[3])
        rows[key] = dict(n=int(_num(r[1])), gap=_num(r[2]), ci=(float(ci[0]), float(ci[1])), rb=_num(r[4]),
                         p=_num(r[5]), verdict=r[6])
    return rows


def shapley(root: Path | None = None) -> dict:
    """Order-free (Shapley) attribution and the initial-condition arms of the ablation."""
    tabs = md_tables(_md("shapley", root))
    fact = {(r[0], r[1], r[2]): _num(r[3]) for r in tabs[0][1:]}
    shares = {}
    for r in tabs[1][1:]:
        name = "K" if "gain" in r[0] else "tau" if "time constant" in r[0] else "Td"
        shares[name] = dict(contribution_m=_num(r[1]), fraction=_num(r[2]) / 100.0)
    ic = {}
    for r in tabs[2][1:]:
        label = r[0].replace("**", "")
        if label.startswith("ideal"):
            ic["ideal"] = _num(r[2])
        elif "const-velocity" in label:
            ic["constant_velocity"] = _num(r[2])
        elif "repouso" in r[1]:
            ic["model_from_rest"] = _num(r[2])
        elif "medida" in r[1]:
            ic["model_measured_ic"] = _num(r[2])
    return dict(factorial=fact, shares=shares, ic=ic)


def causal(root: Path | None = None) -> dict:
    t = md_tables(_md("causal", root))[0]
    out = {}
    for r in t[1:]:
        key = "central" if r[0].startswith("central") else "causal"
        out[key] = dict(epos_01=_num(r[1]), epos_04=_num(r[2]), epos_15=_num(r[3]), gap_event=_num(r[4]),
                        wins=r[5], p=_num(r[6]))
    return out


def loo(root: Path | None = None) -> dict:
    text = _md("loo", root)
    out = {}
    for dof in ("vx", "vy"):
        blk = text[text.index(f"## {dof} "):]
        m = re.search(r"fit medio \*\*([0-9.]+) %\*\*, desvio \*\*([0-9.]+) p\.p\.\*\*, faixa ([0-9.]+)-([0-9.]+) %", blk)
        k = re.search(r"K medio ([0-9.]+), desvio ([0-9.]+) \(promovido: ([0-9.]+)\)", blk)
        n = re.search(r"\(`[a-z_]+`, (\d+) eventos", blk)
        out[dof] = dict(n_folds=int(n.group(1)), fit_mean=float(m.group(1)), fit_sd=float(m.group(2)),
                        fit_min=float(m.group(3)), fit_max=float(m.group(4)), K_mean=float(k.group(1)),
                        K_sd=float(k.group(2)), K_promoted=float(k.group(3)))
    return out


def r3(root: Path | None = None) -> dict:
    """Closed-loop yaw fit under the hold-out criterion and the open-loop reference row."""
    t = md_tables(_md("r3", root))[0]
    rows = {}
    for r in t[1:]:
        key = "closed_loop" if r[0].startswith("closed") else "open_loop"
        rows[key] = dict(K=_num(r[1]), tau=_num(r[2]), Td=_num(r[3]), fit=_num(r[4]))
    text = _md("r3", root)
    m = re.search(r"Eventos `shoot_to_goal` usados: (\d+) \((\d+) treino / (\d+) hold-out\)", text)
    rows["n"] = dict(events=int(m.group(1)), train=int(m.group(2)), holdout=int(m.group(3)))
    return rows


def negctl(root: Path | None = None) -> dict:
    t = md_tables(_md("negctl", root))[0]
    out = {}
    for r in t[1:]:
        key = {"per-DOF vs ideal": "perdof_vs_ideal", "bayesopt vs ideal": "bayesopt_vs_ideal",
               "per-DOF vs bayesopt": "perdof_vs_bayesopt"}[r[0]]
        out[key] = dict(med_a=_num(r[1]), med_b=_num(r[2]), gap=_num(r[3]), wins=r[4], p=_num(r[5]), rb=_num(r[6]))
    return out


def rsim_delay(root: Path | None = None) -> list[dict]:
    t = md_tables(_md("rsim_delay", root))[0]
    return [dict(h_s=_num(r[0]), model=_num(r[1]), rsim=_num(r[2]), rsim_delay=_num(r[4])) for r in t[1:]]


def excitation(root: Path | None = None) -> dict:
    t = md_tables(_md("excitation", root))[0]
    return {r[0]: dict(label=r[1].strip("`"), n=int(_num(r[2])), corr=_num(r[3]), r2=_num(r[4])) for r in t[1:]}


# =========================================================================
# September results (JSON where available)
# =========================================================================
REGIMES_YAW = ("R1", "R1-wonly", "R2-rotate", "R2-square", "R3", "R3-mild")


def yaw_insilico(root: Path | None = None) -> dict[str, dict]:
    """Yaw-gain estimates (median, p25, p75) per generator, regime and (noise, deadzone) cell."""
    out: dict[str, dict] = {}
    for gen, key in (("linear twin", "c1"), ("route b", "c1b_nodelay"), ("route b + delay", "c1b_delay")):
        d = load_json(key, root)
        cells = {}
        for c in d["cells"]:
            if c["dof"] != "w":
                continue
            cells[(c["regime"], c["noise"], c["deadzone"])] = dict(med=c["K_med"], p25=c["K_p25"], p75=c["K_p75"],
                                                                   n_rep=c["n_rep"])
        out[gen] = cells
    return out


def backends(root: Path | None = None) -> dict:
    """C2a: per-horizon medians (CSV) and per-event rows at h_ref (Markdown) of the MuJoCo routes."""
    import csv

    rows: dict[str, list[dict]] = {}
    with open(path("c2a_csv", root), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.setdefault(r["model"], []).append({k: (float(v) if k not in ("model",) else v) for k, v in r.items()})
    text = _md("c2a", root)
    per_event = {}
    for t in md_tables(text):
        if len(t[0]) > 2 and t[0][0] == "modelo" and "gemeo vence" in t[0][2]:
            for r in t[1:]:
                per_event[r[0]] = dict(event_median=_num(r[1]), wins=r[2], p=_num(r[3]), rb=_num(r[4]))
    twin_ev = _num(re.search(r"e_pos mediano dos eventos = ([0-9.]+) m", text).group(1))
    return dict(rows=rows, per_event=per_event, twin_event_median=twin_ev)


def league_session(key: str, root: Path | None = None) -> dict:
    """One protocol_holdout artefact: per variant, window medians per horizon, per-event medians at h_ref
    and the per-event test; plus the in-process columns (model, states zeroed, pre-rolled)."""
    d = load_json(key, root)
    hs = [h / 60.0 for h in d["horizons"]]
    k = d["horizons"].index(d["h_ref"])
    out: dict[str, Any] = dict(date=SESSIONS[key], horizons_s=hs, h_ref_s=d["h_ref_s"], events=d["events"],
                               n_windows=d["n_windows"], validity=d["validity"], variants={})
    twin = None
    for name, m in d["models"].items():
        rows = m["rows"]
        ev = m["per_event"]
        twin = [e[1] for e in ev]
        out["variants"][name] = dict(
            epos=[r["epos_model_trans"] for r in rows], eang=[r["eang_model_trans"] for r in rows],
            window_median=rows[k]["epos_model_trans"], event_values=[e[2] for e in ev],
            event_median=_median([e[2] for e in ev]), wins=rows[k]["wins"], n_events=rows[k]["n_events"],
            p=rows[k]["p_wilcoxon"], rb=rows[k]["rank_biserial"], n_failed=m["n_failed"])
        out["model_epos"] = [r["epos_twin_trans"] for r in rows]
        out["model_eang"] = [r["eang_twin_trans"] for r in rows]
    out["model_event_values"] = twin
    out["model_event_median"] = _median(twin)
    out["model_states_zeroed"] = [r["epos_model_trans"] for r in d["twin_v0zero"]["rows"]]
    if d.get("twin_preroll"):
        out["model_prerolled"] = [r["epos_model_trans"] for r in d["twin_preroll"]["rows"]]
    return out


def _median(v) -> float:
    s = sorted(float(x) for x in v)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def closed_loop(root: Path | None = None) -> dict:
    """C4 quantiles and criteria (session field players, competition pool, per label)."""
    d = load_json("c4", root)
    comp = d["competition"]
    return dict(field=d["field"], keeper=d["keeper"], pool=comp["pool"],
                per_label={k: v["stats"] for k, v in comp["per_label"].items()},
                n_events=comp["n_events"], dist=d["dist"], criteria=d["criteria"],
                per_label_dist=d["per_label_dist"], tracking=d["tracking"])


def session_report(root: Path | None = None) -> dict:
    return load_json("b3", root)


MIMO_CONTROLS = {"mimo_cminus": "fopdt", "mimo_cplus": "mujoco-rollers-delay"}


def coupling(root: Path | None = None) -> dict:
    """WP2: the pre-registered coupled (MIMO) check on the competition logs and its in-silico controls.

    ``fit_pooled`` / ``fit_mean``: hold-out fit (%) per arm (promoted, diagonal, coupled) and DOF; ``G`` and
    ``tau_s``: static gain matrices (row = output, column = command) and time constants per arm; ``ratios``:
    cross-term contribution (RMS cross / RMS direct) per output, total and per input; ``m1``, ``m2``,
    ``m2_game`` (training restricted to the game label) and ``harness`` (with ``m3``): the pre-registered
    verdicts; ``pair_delays`` and ``bootstrap``: the secondary analyses; ``controls``: the same quantities
    for C- (``fopdt``) and C+ (``mujoco-rollers-delay``) when their artefacts are present.
    """
    d = load_json("mimo", root)
    arms = ("promoted", "diagonal", "coupled")
    pdl = d["pair_delays"]
    out = dict(n_train=d["n_train"], n_test=d["n_test"], K_ref=d["K_ref_w"], delays=d["delays_primary"],
               fit_pooled=d["score"]["pooled"], fit_mean=d["score"]["mean"],
               G={k: d["models"][k]["G"] for k in arms}, tau_s={k: d["models"][k]["tau_s"] for k in arms},
               ratios=d["ratios"], m1=d["m1"], m2=d["m2"], m2_game=d["m2_stg_only"],
               pair_delays=dict(fit_pooled=pdl["score"]["pooled"], m1=pdl["m1"], m2=pdl["m2"],
                                G_coupled=pdl["models"]["coupled"]["G"], M_coupled=pdl["models"]["coupled"]["M"]),
               bootstrap=d["bootstrap"], harness=d["harness"], controls={})
    for key, name in MIMO_CONTROLS.items():
        if available(key, root):
            c = load_json(key, root)
            out["controls"][name] = dict(K_ref=c["K_ref_w"], m1=c["m1"], m2=c["m2"], ratios=c["ratios"],
                                         G_coupled=c["models"]["coupled"]["G"],
                                         negative_control=c.get("negative_control"))
    return out


# =========================================================================
# figure helpers (Elsevier sizes: single column 90 mm, 1.5 column 140 mm, double 190 mm)
# =========================================================================
MM = 1.0 / 25.4
JOURNAL_DIR = "latex_journal"


def figure_style() -> None:
    """Matplotlib settings shared by the journal figures (Times-like text, 8 pt)."""
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams.update({
        "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"], "mathtext.fontset": "stix",
        "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8, "legend.fontsize": 7, "xtick.labelsize": 7,
        "ytick.labelsize": 7, "axes.linewidth": 0.6, "lines.linewidth": 1.1, "grid.linewidth": 0.4,
        "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "pdf.fonttype": 42,
    })


def save_figure(fig, ctx, name: str, latex_copy: bool = True) -> dict[str, Path]:
    """``results/figs/<name>_<stamp>.{pdf,png}`` and, with ``latex_copy``, ``latex_journal/figures/<name>.pdf``."""
    import shutil

    out = {}
    for ext in ("pdf", "png"):
        p = ctx.figs / f"{name}_{ctx.stamp}.{ext}"
        fig.savefig(p, dpi=300)
        out[ext] = p
    if latex_copy:
        dst = ctx.root / JOURNAL_DIR / "figures" / f"{name}.pdf"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out["pdf"], dst)
        out["latex"] = dst
    return out
