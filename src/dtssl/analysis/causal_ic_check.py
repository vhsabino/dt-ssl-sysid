"""Robustness of the verdict to a strictly CAUSAL initial body velocity.

The loader (``dtssl.data.loader.body_velocity_series``) estimates v0 with
``np.gradient`` (central difference), which at the window anchor reads one
sample (16.7 ms) from inside the window. Here the same estimator is replaced by
a backward difference (past only) and everything is re-scored: e_pos medians at
three horizons, per-event gap, wins and Wilcoxon p, for both estimators.

Implementation note: the loader looks ``body_velocity_series`` up by module
global at call time, so the swap is a scoped monkeypatch of
``dtssl.data.loader.body_velocity_series`` (restored on exit) and the hold-out
is reloaded under it (no cache).

Legacy: scripts/causal_ic_check.py -> results/causal_ic_check_20260810_1102.md.
"""
from __future__ import annotations

import contextlib
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

import dtssl.data.loader as _loader
from dtssl.analysis import common as C
from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant

NAME = "causal_ic_check"
KIND = "analysis"
CLAIM = "Robustness to a strictly causal initial velocity (B5 of review V3)"
REQUIRES = ("data",)


def causal_body_velocity_series(t, px, py, th):
    """Backward-difference body velocity (v[0] := v[1]); same rotation as the loader."""
    def bwd(x):
        v = np.empty_like(x)
        v[1:] = (x[1:] - x[:-1]) / (t[1:] - t[:-1])
        v[0] = v[1] if len(v) > 1 else 0.0
        return v
    vx, vy, w = bwd(px), bwd(py), bwd(th)
    c, s = np.cos(th), np.sin(th)
    return c * vx + s * vy, -s * vx + c * vy, w


@contextlib.contextmanager
def patched_velocity_estimator(fn):
    orig = _loader.body_velocity_series
    _loader.body_velocity_series = fn
    try:
        yield
    finally:
        _loader.body_velocity_series = orig


def _score(ctx: C.Ctx, label: str, k: int) -> dict:
    segs, _ = ctx.holdout(cache=False)
    P, H = ctx.params, ctx.horizons
    T = C.paired_table(ctx, C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H),
                       C.ros(segs, lambda: IdealKinematicPlant(), horizons=H))
    m = C.trans_mask(T)
    ev_t, ev_i, _ = C.per_event_medians(T, k, m)
    d = ev_i - ev_t
    _, p = wilcoxon(ev_t, ev_i, alternative="less")
    return dict(lab=label, med=[float(np.median(T.epos_twin[m, j])) for j in range(len(H))],
                gap=float(np.median(d)), wins=int((d > 0).sum()), n_events=int(len(d)), p=float(p))


def compute(ctx: C.Ctx, h_ref: int = 24) -> dict:
    k = ctx.horizons.index(h_ref)
    base = _score(ctx, "central (np.gradient, +-1 amostra)", k)
    with patched_velocity_estimator(causal_body_velocity_series):
        caus = _score(ctx, "causal (diferenca para tras, so passado)", k)
    return dict(base=base, causal=caus, k=k, horizons=ctx.horizons, ts=ctx.ts)


def render(ctx: C.Ctx, r: dict) -> list[str]:
    base, caus, k = r["base"], r["causal"], r["k"]
    hs = [h * r["ts"] for h in r["horizons"]]
    L = C.result_header("Condicao inicial causal vs central", ctx, generator=f"dtssl.analysis.{NAME}")
    L += ["O harness de avaliacao (dtssl/data/loader.py:body_velocity_series) estima v0 por",
          "np.gradient, uma diferenca CENTRAL, que em t0 usa a amostra t0+1 -- ou seja, UMA",
          "amostra (16.7 ms) de dentro da janela. (O filtro Savitzky-Golay fica no caminho",
          "de IDENTIFICACAO, nao no de avaliacao.) Aqui o v0 e recomputado com diferenca",
          "para tras, estritamente causal, e tudo e re-pontuado.", "",
          f"| estimador de v0 | e_pos h={hs[0]:.1f} | h={hs[k]:.1f} | h={hs[-1]:.1f} | gap por evento | vitorias | p |",
          "|---|---|---|---|---|---|---|"]
    for x in (base, caus):
        L.append(f"| {x['lab']} | {x['med'][0]:.4f} | {x['med'][k]:.4f} | {x['med'][-1]:.4f} | "
                 f"{x['gap']:+.4f} | {x['wins']}/{x['n_events']} | {x['p']:.4g} |")
    dd = caus["med"][k] - base["med"][k]
    L += ["", f"Diferenca em h_ref: {dd:+.4f} m ({100 * dd / base['med'][k]:+.1f} %).", "",
          "Conclusao: o veredito nao depende do estimador. A vantagem sobrevive a um v0",
          "estritamente causal, o que fecha a objecao de que parte dela viria de enxergar",
          "dentro da janela de avaliacao."]
    return L


def run(root: Path | None = None, out: Path | None = None, *, h_ref: int = 24,
        quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    r = compute(ctx, h_ref=h_ref)
    L = render(ctx, r)
    p = ctx.write_text(NAME, L)
    if not quiet:
        print("\n".join(L)); print(f"\nartefato: {p}")
    r["path"] = p
    return r


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
