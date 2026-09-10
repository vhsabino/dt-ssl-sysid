"""League simulators on the hold-out through the ssl-simulation-protocol (C2b): twin vs grSim / ER-Force.

The hold-out windows of the paper's harness (re-anchored SE(2) windows, stride 15, H_max 90, horizons of
``config/metrics.json``) are replayed through external simulators with :class:`dtssl.sim.protocol_plant.ProtocolPlant`
(teleport to the true pose/velocity, commands streamed at 60 Hz, poses read back from the simulator's vision and
aligned to the window clock).  Per simulator of ``config/external_sims.json`` two variants:

* ``<sim>``        -- the recorded body commands as they are (the simulator's own actuation latency is part of it);
* ``<sim>+delay``  -- the identified per-DOF transport delay ``Td`` applied on the sending side (the analogue of
                      the rSim + Td ablation of the paper and of ``mujoco-rollers-delay`` in ``backends_holdout``).

Same windows and metric as ``backends_holdout``: window-level medians of ``e_pos`` / ``e_ang`` in the translation
bin per horizon; per event (n = hold-out events): medians at ``h_ref``, wins vs the twin, one-sided paired Wilcoxon
(twin < simulator) and rank-biserial.  Windows the simulator failed to reproduce (teleport not seen, vision gap)
are excluded and counted.  With ``repeat=2`` the whole replay is run twice and the run-to-run agreement is reported
(the protocol replay is real-time and non-deterministic by nature: this is its repeatability).

Fairness, printed with the result: the league simulators are **not** calibrated to the RobôCIn robot (their own
robot models, actuation and vision pipelines) -- they are the "league physics as shipped" baselines the paper
compared against with rSim.  Two handicaps of the protocol path are made explicit: (i) the alignment removes the
simulator's vision delay (ER-Force: 35 ms) but not its command delay / standby logic; (ii) the **initial velocity**
of a window cannot be imposed on every simulator (grSim resets the robot on teleport and turns the velocity into
a motor setpoint: every window starts from rest; ER-Force honours the linear velocity only, see
``teleport_omega``).  The twin with the same handicap (``fopdt_v0=0``: FOPDT states reset to zero at ``t0``) is
reported next to the paper's twin so the reader can separate "league physics vs FOPDT" from "initial condition".

Real time: ~8 min per variant for the 265 windows.  Run it on the same machine / network namespace as the
simulator (multicast; in WSL2, inside WSL -- ``tools/external_sims/README.md``); grSim and ER-Force use the same
ports, so run one simulator at a time and merge the caches offline (``from_cache``):

    dtssl analysis run protocol_holdout --kw sims=grsim [delay=both|none|theta] [repeat=1]
    dtssl analysis run protocol_holdout --kw sims=erforce
    dtssl analysis run protocol_holdout --kw from_cache=results/_cache_protocol_grsim_*.npz,results/_cache_protocol_erforce_*.npz

Output: ``results/protocol_holdout_<stamp>.md`` (+ ``.csv``, ``.json``) and the rollouts of every variant in
``results/_cache_protocol_<sim>[_delay]_<stamp>[_r<k>].npz`` (+ ``.stats.json`` with the replay diagnostics),
re-analysable offline without the simulator through ``from_cache`` (labels and repeats are read from the file names).
Self-test: ``sims=dtssl`` with ``dtssl serve --backend fopdt --theta <theta with Td = 0>`` running reproduces the
twin (``tests/test_protocol_plant.py`` / ``tests/test_protocol_holdout.py`` do it in-process at the mm level).
"""
from __future__ import annotations

import glob
import json
import re
import time
from pathlib import Path

import numpy as np

from dtssl.analysis import common as C
from dtssl.eval.stats import rank_biserial, wilcoxon_less
from dtssl.models import AnalyticFOPDTPlant

NAME = "protocol_holdout"
KIND = "analysis"
CLAIM = "Behavioral twin vs league simulators (grSim, ER-Force) replayed through the ssl-simulation-protocol"
REQUIRES = ("data", "net")
DEFAULT_SIMS = ("grsim", "erforce")


_CACHE_RE = re.compile(r"_cache_protocol_(?P<sim>[A-Za-z0-9-]+?)(?P<delay>_delay)?_(?P<stamp>\d{8}_\d{4,6})(?:_r(?P<rep>\d+))?\.npz$")


def _variants(sims, delay: str) -> list[tuple[str, str, str | None]]:
    """``(label, sim, delay_mode)`` for the requested simulators and delay option."""
    modes = {"both": (None, "theta"), "none": (None,), "theta": ("theta",)}[delay]
    out = []
    for s in sims:
        for m in modes:
            out.append((f"{s}+delay" if m == "theta" else s, s, m))
    return out


def cache_stem(label: str, stamp: str, rep: int | None = None) -> str:
    return f"_cache_protocol_{label.replace('+', '_')}_{stamp}" + (f"_r{rep}" if rep is not None else "")


def parse_cache_name(path: str | Path) -> tuple[str, str, int]:
    """``(label, stamp, repeat)`` from a cache file name written by :func:`compute` (KeyError otherwise)."""
    m = _CACHE_RE.search(Path(path).name)
    if m is None:
        raise KeyError(f"{Path(path).name}: not a protocol_holdout cache name (_cache_protocol_<sim>[_delay]_<stamp>[_r<k>].npz)")
    label = m.group("sim") + ("+delay" if m.group("delay") else "")
    return label, m.group("stamp"), int(m.group("rep") or 0)


class _ZeroICPlant:
    """The analytic twin with the FOPDT states reset to zero at ``t0`` (the grSim handicap), same delay tap."""

    def __init__(self, params):
        self.inner = AnalyticFOPDTPlant(params)
        self.params = self.inner.params

    def reset(self, pose0, velb0=(0.0, 0.0, 0.0)):
        self.inner.reset(pose0, (0.0, 0.0, 0.0))

    def prime_delay(self, prev_cmds):
        self.inner.prime_delay(prev_cmds)

    def step(self, cmd, dt):
        return self.inner.step(cmd, dt)


def _per_event_nan(table, k: int, mask: np.ndarray):
    sid = np.asarray(table.seg_id)[mask]
    a, b = table.epos_twin[mask, k], table.epos_def[mask, k]
    ids = sorted(set(int(s) for s in sid))
    ev_t = np.array([np.nanmedian(a[sid == s]) for s in ids])
    ev_m = np.array([np.nanmedian(b[sid == s]) for s in ids])
    ok = np.isfinite(ev_m)
    return ev_t[ok], ev_m[ok], [i for i, o in zip(ids, ok, strict=True) if o]


def _summarise(ctx: C.Ctx, tw, ro, H, kref) -> dict:
    T = C.paired_table(ctx, tw, ro)
    m = C.trans_mask(T)
    allm = np.ones(T.W, dtype=bool)
    failed = ~np.isfinite(T.epos_def).all(axis=1)
    rows = []
    for k, h in enumerate(H):
        ev_t, ev_m, ids = _per_event_nan(T, k, m)
        rows.append(dict(
            h=int(h), h_s=float(h * T.ts),
            epos_twin_trans=float(np.nanmedian(T.epos_twin[m, k])), epos_model_trans=float(np.nanmedian(T.epos_def[m, k])),
            epos_twin_all=float(np.nanmedian(T.epos_twin[allm, k])), epos_model_all=float(np.nanmedian(T.epos_def[allm, k])),
            eang_twin_trans=float(np.nanmedian(T.eang_twin[m, k])), eang_model_trans=float(np.nanmedian(T.eang_def[m, k])),
            p_wilcoxon=float(wilcoxon_less(ev_t, ev_m)) if len(ids) >= 2 else float("nan"),
            rank_biserial=float(rank_biserial(ev_m, ev_t)) if len(ids) >= 2 else float("nan"),
            wins=int((ev_t < ev_m).sum()), n_events=len(ids)))
    ev_t, ev_m, ids = _per_event_nan(T, kref, m)
    gap = np.abs(T.epos_def[:, kref] - T.epos_twin[:, kref])
    return dict(rows=rows, per_event=[(int(i), float(a), float(b)) for i, a, b in zip(ids, ev_t, ev_m, strict=True)],
                gap_vs_twin_med=float(np.nanmedian(gap)), gap_vs_twin_max=float(np.nanmax(gap)),
                n_windows=int(T.W), n_trans=int(m.sum()), n_failed=int(failed.sum()),
                epos_href=[float(v) for v in T.epos_def[:, kref]])


def _rows_only(ctx: C.Ctx, tw, ro, H) -> list[dict]:
    """Window-level medians per horizon (translation bin) of ``ro`` vs the paper's twin ``tw``."""
    T = C.paired_table(ctx, tw, ro)
    m = C.trans_mask(T)
    return [dict(h=int(h), h_s=float(h * T.ts), epos_model_trans=float(np.nanmedian(T.epos_def[m, k])),
                 eang_model_trans=float(np.nanmedian(T.eang_def[m, k]))) for k, h in enumerate(H)]


def _check_cache(ro, segs, path) -> None:
    if len(ro) != len(segs):
        raise ValueError(f"{path}: {len(ro)} rollouts for {len(segs)} hold-out segments")
    for r, s in zip(ro, segs, strict=True):
        if r.meta.get("event") != s.meta.get("event"):
            raise ValueError(f"{path}: rollout of {r.meta.get('event')!r} paired with segment {s.meta.get('event')!r}")


def _finish(ctx: C.Ctx, tw, tw0, H, kref, segs, dropped, models, order, cost, caches, delay, repeat) -> dict:
    zero = _rows_only(ctx, tw, tw0, H)
    return dict(models=models, order=order, horizons=list(H), h_ref=int(H[kref]), h_ref_s=float(H[kref] * tw[0].meta["ts"]),
                n_events=len(segs), n_windows=sum(r.n_total for r in tw), events=[s.meta.get("event") for s in segs],
                dropped=[d.get("event") if isinstance(d, dict) else str(d) for d in dropped], cost_s=cost,
                caches=caches, delay=delay, repeat=int(repeat), twin_v0zero=dict(rows=zero))


def _attach_repeat(runs: list[dict], repeat: int) -> dict:
    first = runs[0]
    if repeat > 1:
        e = np.array([run["epos_href"] for run in runs])                # (repeat, W)
        d = np.abs(e[1:] - e[0])
        with np.errstate(all="ignore"):
            first["repeat"] = dict(n=int(repeat), abs_diff_med=float(np.nanmedian(d)), abs_diff_p90=float(np.nanpercentile(d, 90)),
                                   medians=[float(np.nanmedian(x)) for x in e])
    for run in runs:
        run.pop("epos_href", None)
    return first


def compute(ctx: C.Ctx, sims=DEFAULT_SIMS, delay: str = "both", repeat: int = 1, h_ref: int | None = None,
            save_cache: bool = True, endpoints_path: str | Path | None = None) -> dict:
    from dtssl.sim.protocol_plant import ProtocolPlant, load_endpoint
    from dtssl.sim.rollout import save_rollouts

    segs, dropped = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    h_ref = int(ctx.mcfg["verdict"]["h_ref"] if h_ref is None else h_ref)
    kref = H.index(h_ref)
    t0 = time.perf_counter()
    tw = C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H)
    tw0 = C.ros(segs, lambda: _ZeroICPlant(P), horizons=H)
    cost = {"fopdt": time.perf_counter() - t0}
    models: dict[str, dict] = {}
    caches: dict[str, str] = {}
    order = []
    for label, sim, mode in _variants(sims, delay):
        ep = load_endpoint(sim, endpoints_path)
        runs = []
        for r in range(int(repeat)):
            plant = ProtocolPlant(ep, delay=mode, params=P)
            t1 = time.perf_counter()
            try:
                ro = C.ros(segs, lambda plant=plant: plant, horizons=H)
            finally:
                plant.close()
            key = f"{label}#{r}" if repeat > 1 else label
            cost[key] = time.perf_counter() - t1
            summ = _summarise(ctx, tw, ro, H, kref)
            summ["diagnostics"] = plant.stats.as_dict()
            summ["endpoint"] = dict(name=ep.name, host=ep.host, vision=f"{ep.vision_ip}:{ep.vision_port}",
                                    control_port=ep.control_port, team=ep.team, robot_id=ep.robot_id,
                                    teleport_omega=bool(ep.teleport_omega))
            if save_cache:
                path = save_rollouts(ctx.out / cache_stem(label, ctx.stamp, r if repeat > 1 else None), ro)
                side = dict(label=label, sim=sim, delay=mode, repeat=r, endpoint=summ["endpoint"],
                            diagnostics=summ["diagnostics"], cost_s=cost[key], stamp=ctx.stamp)
                path.with_suffix(".stats.json").write_text(json.dumps(side, indent=1, default=str), encoding="utf-8")
                caches[key] = str(path)
            runs.append(summ)
        models[label] = _attach_repeat(runs, int(repeat))
        order.append(label)
    return _finish(ctx, tw, tw0, H, kref, segs, dropped, models, order, cost, caches, delay, repeat)


def compute_from_caches(ctx: C.Ctx, paths, h_ref: int | None = None) -> dict:
    """Re-analyse saved protocol rollouts (no simulator needed); variants and repeats from the file names."""
    from dtssl.sim.rollout import load_rollouts

    files: list[Path] = []
    for p in paths:
        hits = sorted(glob.glob(str(p)))
        files += [Path(h) for h in hits] if hits else [Path(p)]
    if not files:
        raise ValueError("from_cache: no cache files given")
    groups: dict[str, list[tuple[int, Path]]] = {}
    for f in files:
        label, _, rep = parse_cache_name(f)
        groups.setdefault(label, []).append((rep, f))
    segs, dropped = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    h_ref = int(ctx.mcfg["verdict"]["h_ref"] if h_ref is None else h_ref)
    kref = H.index(h_ref)
    t0 = time.perf_counter()
    tw = C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H)
    tw0 = C.ros(segs, lambda: _ZeroICPlant(P), horizons=H)
    cost = {"fopdt": time.perf_counter() - t0}
    models: dict[str, dict] = {}
    caches: dict[str, str] = {}
    order = []
    for label, items in groups.items():
        runs = []
        for rep, f in sorted(items):
            ro = load_rollouts(f)
            _check_cache(ro, segs, f)
            summ = _summarise(ctx, tw, ro, H, kref)
            side_path = f.with_suffix(".stats.json")
            side = json.loads(side_path.read_text(encoding="utf-8")) if side_path.is_file() else {}
            summ["diagnostics"] = side.get("diagnostics", {})
            summ["endpoint"] = side.get("endpoint", dict(name=label.split("+")[0], host="?", vision="?", control_port="?",
                                                         team="?", robot_id="?"))
            key = f"{label}#{rep}" if len(items) > 1 else label
            cost[key] = float(side.get("cost_s", float("nan")))
            caches[key] = str(f)
            runs.append(summ)
        models[label] = _attach_repeat(runs, len(items))
        order.append(label)
    delay = "both" if any("+delay" in n for n in order) and any("+delay" not in n for n in order) else (
        "theta" if all("+delay" in n for n in order) else "none")
    return _finish(ctx, tw, tw0, H, kref, segs, dropped, models, order, cost, caches, delay,
                   max(len(v) for v in groups.values()))


def instrument_validity(M: dict) -> tuple[bool, str]:
    """Pre-registered validity criterion V of one variant: ``(valid, one-line verdict)``."""
    d = M.get("diagnostics") or {}
    n_win, n_failed = int(M.get("n_windows", 0)), int(M.get("n_failed", 0))
    lost = n_failed / n_win if n_win else 1.0
    jit = d.get("send_jitter_mean")
    late, sent = d.get("send_late"), d.get("controls_sent")
    late_frac = (late / sent) if (late is not None and sent) else None
    spread = d.get("teleport_latency_spread")
    period = d.get("vision_period_wall")
    est, tot = d.get("tau0_estimated"), d.get("windows")
    checks = [
        ("janelas perdidas", lost <= 0.05, f"{n_failed}/{n_win} = {100 * lost:.1f} %"),
        ("jitter de envio", jit is not None and jit < 0.002 and late_frac is not None and late_frac <= 0.01,
         "-" if jit is None else f"medio {1e3 * jit:.2f} ms, atrasados > 10 ms: {late}/{sent}"
         + (f" (max {1e3 * d['send_jitter_max']:.1f} ms)" if d.get("send_jitter_max") is not None else "")),
        ("latencia do teleporte", spread is not None and period is not None and spread < period,
         "-" if spread is None or period is None else f"espalhamento {1e3 * spread:.1f} ms vs quadro {1e3 * period:.1f} ms"),
        ("tau0 estimado", bool(tot) and est is not None and est >= 0.5 * tot, "-" if not tot else f"{est}/{tot}"),
    ]
    ok = all(c[1] for c in checks)
    text = ("VALIDO" if ok else "INVALIDO") + " (" + "; ".join(f"{name} {'ok' if good else 'FALHA'}: {info}"
                                                                for name, good, info in checks) + ")"
    return ok, text


def render(ctx: C.Ctx, r: dict) -> list[str]:
    L = C.result_header("Simuladores da liga no hold-out via ssl-simulation-protocol: gemeo x grSim / ER-Force", ctx,
                        generator=f"dtssl.analysis.{NAME}",
                        extra="mesmas janelas do theta oficial, stride 15, H_max 90; replay em tempo real via protocolo")
    zero = r.get("twin_v0zero", {}).get("rows")
    L += [f"Hold-out: {r['n_events']} eventos ({', '.join(r['events'])}); {r['n_windows']} janelas; "
          f"h_ref = {r['h_ref']} amostras = {r['h_ref_s']:.2f} s. Variantes: {', '.join(r['order'])} "
          f"(`+delay` = Td identificado aplicado nos comandos enviados). `fopdt_v0=0` = o gemeo com os estados "
          "FOPDT zerados em t0 (a mesma desvantagem do grSim, que ignora a velocidade inicial no teleporte).", "",
          "## e_pos mediano por horizonte (bin translacional, janelas densas; NaN = janelas perdidas excluidas)", "",
          "| h (s) | fopdt | fopdt_v0=0 | " + " | ".join(r["order"]) + " |", "|---|---|---|" + "---|" * len(r["order"])]
    first = r["models"][r["order"][0]]["rows"]
    z = lambda k, key: f"{zero[k][key]:.4f}" if zero else "-"  # noqa: E731
    for k, row in enumerate(first):
        cells = [f"{row['h_s']:.2f}", f"{row['epos_twin_trans']:.4f}", z(k, "epos_model_trans")]
        cells += [f"{r['models'][n]['rows'][k]['epos_model_trans']:.4f}" for n in r["order"]]
        L.append("| " + " | ".join(cells) + " |")
    L += ["", "## e_ang mediano por horizonte (rad, bin translacional)", "",
          "| h (s) | fopdt | fopdt_v0=0 | " + " | ".join(r["order"]) + " |", "|---|---|---|" + "---|" * len(r["order"])]
    for k, row in enumerate(first):
        cells = [f"{row['h_s']:.2f}", f"{row['eang_twin_trans']:.4f}", z(k, "eang_model_trans")]
        cells += [f"{r['models'][n]['rows'][k]['eang_model_trans']:.4f}" for n in r["order"]]
        L.append("| " + " | ".join(cells) + " |")
    kref = r["horizons"].index(r["h_ref"])
    L += ["", f"## Por evento em h_ref = {r['h_ref_s']:.2f} s (medianas por evento)", "",
          "| variante | e_pos mediano (eventos) | gemeo vence | Wilcoxon p (gemeo < sim) | rank-biserial | "
          "janelas perdidas | |delta e_pos| vs gemeo (mediana / max) |", "|---|---|---|---|---|---|---|"]
    for n in r["order"]:
        M = r["models"][n]
        row = M["rows"][kref]
        med_ev = float(np.median([b for _, _, b in M["per_event"]])) if M["per_event"] else float("nan")
        L.append(f"| {n} | {med_ev:.4f} | {row['wins']}/{row['n_events']} | {row['p_wilcoxon']:.3g} | "
                 f"{row['rank_biserial']:+.2f} | {M['n_failed']}/{M['n_windows']} | {M['gap_vs_twin_med']:.4f} / "
                 f"{M['gap_vs_twin_max']:.4f} |")
    tw_ev = float(np.median([a for _, a, _ in r["models"][r["order"][0]]["per_event"]]))
    L += ["", f"Gemeo (`fopdt`) em h_ref: e_pos mediano dos eventos = {tw_ev:.4f} m.", "",
          "## Diagnostico do replay via protocolo", "",
          "| variante | endpoint | visao (Hz sim) | latencia teleporte (ms) | tau0 mediano (ms) | tau0 estimado | "
          "fase de envio | jitter envio max/med (ms) | envios atrasados | teleporte nao visto | ancora tardia | "
          "janelas curtas | gaps de visao |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for n in r["order"]:
        M = r["models"][n]
        d, e = M["diagnostics"], M["endpoint"]
        f = lambda v, s=1.0: "-" if v is None else f"{v * s:.2f}"  # noqa: E731
        g = lambda k, d=d: "-" if d.get(k) is None else d.get(k)  # noqa: E731
        L.append(f"| {n} | {e['name']} {e['host']} vis {e['vision']} ctrl {e['control_port']} ({e['team']} {e['robot_id']}"
                 f"{'' if e.get('teleport_omega', True) else ', sem omega0'}) | "
                 f"{f(d.get('vision_rate_sim'))} | {f(d.get('teleport_latency_wall'), 1e3)} | {f(d.get('tau0_median'), 1e3)} | "
                 f"{g('tau0_estimated')}/{g('windows')} | {f(d.get('send_phase_median'))} | "
                 f"{f(d.get('send_jitter_max'), 1e3)} / {f(d.get('send_jitter_mean'), 1e3)} | "
                 f"{g('send_late')}/{g('controls_sent')} | {g('anchor_failures')} | {g('anchor_late')} | {g('short_windows')} | "
                 f"{g('vision_gaps')} |")
    L += ["", "Validade do instrumento (pre-registro C2b, criterio V: janelas perdidas <= 5 %, jitter medio de envio < 2 ms "
          "com <= 1 % dos envios atrasados > 10 ms, espalhamento da latencia < 1 quadro, tau0 estimado em >= 50 % das "
          "janelas):", ""]
    for n in r["order"]:
        L.append(f"- {n}: " + instrument_validity(r["models"][n])[1])
    if r["repeat"] > 1:
        L += ["", f"## Repetibilidade ({r['repeat']} execucoes; |delta e_pos| entre execucoes por janela em h_ref)", "",
              "| variante | mediana (m) | p90 (m) | e_pos mediano por execucao |", "|---|---|---|---|"]
        for n in r["order"]:
            rp = r["models"][n].get("repeat")
            if rp:
                L.append(f"| {n} | {rp['abs_diff_med']:.4f} | {rp['abs_diff_p90']:.4f} | "
                         + ", ".join(f"{v:.4f}" for v in rp["medians"]) + " |")
    L += ["", "## Custo (segundos de parede)", "", "| variante | s |", "|---|---|"]
    for n, s in r["cost_s"].items():
        L.append(f"| {n} | {s:.1f} |")
    if r["caches"]:
        L += ["", "Rollouts salvos (reanalise offline): " + ", ".join(f"`{Path(p).name}`" for p in r["caches"].values())]
    L += ["", "## Leitura", "",
          "- Os simuladores da liga entram **como saem da caixa** (modelo de robo, atuacao e visao proprios; sem "
          "calibracao ao robo RoboCIn): sao as baselines 'fisica da liga nao sintonizada', o papel que o rSim tinha "
          "no artigo, agora com o mesmo harness e as mesmas janelas.",
          "- O alinhamento por teleporte remove o atraso de visao do simulador (ER-Force: 35 ms) mas nao o atraso de "
          "comando nem a logica de standby; `+delay` mostra quanto do gap e explicado pelo atraso de transporte "
          "identificado.",
          "- Condicao inicial: o grSim reinicia o robo no teleporte e converte a velocidade em setpoint dos motores "
          "(toda janela parte do repouso); o ER-Force aplica a velocidade linear mas nao a de guinada (v_angular "
          "cai no eixo x do Bullet no simrobot.cpp; enviamos 0). A coluna `fopdt_v0=0` da o custo dessa desvantagem "
          "no proprio gemeo: o que sobra alem dela e fisica.",
          "- Replay em tempo real: as janelas perdidas (teleporte nao visto / visao insuficiente) sao excluidas e "
          "contadas; use `repeat=2` para reportar a repetibilidade."]
    return L


def run(root: Path | None = None, out: Path | None = None, *, sims: str = ",".join(DEFAULT_SIMS),
        delay: str = "both", repeat: int = 1, h_ref: int | None = None, save_cache: bool = True,
        endpoints: str | None = None, from_cache: str | None = None, quiet: bool = False, **kw) -> dict:
    if delay not in ("both", "none", "theta"):
        raise ValueError("delay must be both | none | theta")
    ctx = C.make_context(root, out)
    if from_cache:
        paths = [p.strip() for p in str(from_cache).split(",") if p.strip()]
        r = compute_from_caches(ctx, paths, h_ref=h_ref)
    else:
        names = [s.strip() for s in str(sims).split(",") if s.strip()]
        r = compute(ctx, names, delay=delay, repeat=int(repeat), h_ref=h_ref, save_cache=bool(save_cache),
                    endpoints_path=endpoints)
    r["validity"] = {n: instrument_validity(M)[0] for n, M in r["models"].items()}
    L = render(ctx, r)
    p = ctx.write_text(NAME, L)
    pj = ctx.out_path(NAME, "json")
    pj.write_text(json.dumps(r, indent=2, default=str), encoding="utf-8")
    pc = ctx.out_path(NAME, "csv")
    with open(pc, "w", encoding="utf-8") as f:
        f.write("model,h,h_s,epos_twin_trans,epos_model_trans,eang_twin_trans,eang_model_trans,wins,n_events,p_wilcoxon\n")
        for n in r["order"]:
            for row in r["models"][n]["rows"]:
                f.write(f"{n},{row['h']},{row['h_s']:.4f},{row['epos_twin_trans']:.6f},{row['epos_model_trans']:.6f},"
                        f"{row['eang_twin_trans']:.6f},{row['eang_model_trans']:.6f},{row['wins']},{row['n_events']},"
                        f"{row['p_wilcoxon']:.4g}\n")
    r.update(path=p, json=pj, csv=pc)
    if not quiet:
        print("\n".join(L))
        print(f"\nartefato: {p}\njson: {pj}\ncsv: {pc}")
    return r


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
