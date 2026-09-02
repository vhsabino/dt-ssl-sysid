"""Order-independent ablation (full 2^3 factorial + Shapley) and initial-condition arms.

Median e_pos (translation bin, h_ref = 0.4 s, same windows) for all eight on/off
combinations of the parameter groups {gain K, time constant tau, dead time Td};
Shapley attribution of the improvement over the ideal kinematics; and the
initial-condition arms: constant-velocity extrapolation (uses ONLY the measured
IC), FOPDT started from rest (like rSim) and FOPDT with the measured IC.

Legacy: scripts/ablation_orderfree.py -> results/ablation_orderfree_20260810_1021.md.
"""
from __future__ import annotations

import itertools
import math
from pathlib import Path

import numpy as np

from dtssl.analysis import common as C
from dtssl.models import AnalyticFOPDTPlant, Plant

NAME = "ablation_orderfree"
KIND = "analysis"
CLAIM = "Order-independent ablation (Shapley) and initial-condition arms (item 4, review V2)"
REQUIRES = ("data",)
GROUPS = ("gain K", "time constant tau", "dead time Td")


class ColdFOPDT(AnalyticFOPDTPlant):
    """Same twin, but WITHOUT the measured initial body velocity: starts from
    rest, like rSim."""

    def reset(self, pose0, velb0=(0.0, 0.0, 0.0)):
        super().reset(pose0, (0.0, 0.0, 0.0))


class ConstVel(Plant):
    """Constant-velocity extrapolation: uses ONLY the measured IC and ignores the
    commands — the honest comparator to separate IC from identified dynamics."""

    def reset(self, pose0, velb0=(0.0, 0.0, 0.0)):
        self.x, self.y, self.th = (float(v) for v in pose0)
        self._v = np.asarray(velb0, float).reshape(3)
        self._vbody = self._v.copy()

    def prime_delay(self, prev_cmds):
        pass

    def step(self, cmd, dt):
        th = self.th + dt * self._v[2]
        c, s = math.cos(th), math.sin(th)
        self.x += dt * (c * self._v[0] - s * self._v[1])
        self.y += dt * (s * self._v[0] + c * self._v[1])
        self.th = th
        return (self.x, self.y, self.th)


def shapley(E: dict, idx: int) -> float:
    tot = 0.0
    others = [i for i in range(3) if i != idx]
    for bits in itertools.product([0, 1], repeat=2):
        s = [0, 0, 0]
        for k, i in enumerate(others):
            s[i] = bits[k]
        a = list(s); a[idx] = 0
        b = list(s); b[idx] = 1
        w = (math.factorial(sum(bits)) * math.factorial(2 - sum(bits))) / math.factorial(3)
        tot += w * (E[tuple(a)] - E[tuple(b)])      # error reduction
    return tot


def compute(ctx: C.Ctx, h_ref: int = 24) -> dict:
    segs, _ = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    k = H.index(h_ref)

    def med(factory) -> float:
        ro = C.ros(segs, factory, horizons=H)
        T = C.paired_table(ctx, ro, ro)
        return float(np.median(T.epos_twin[C.trans_mask(T), k]))

    E = {}
    for uK, ut, uD in itertools.product([0, 1], repeat=3):
        v = C.variant_params(P, bool(uK), bool(ut), bool(uD))
        E[(uK, ut, uD)] = med(lambda v=v: AnalyticFOPDTPlant(v))
    sh = [shapley(E, i) for i in range(3)]
    full = C.variant_params(P, True, True, True)
    return dict(E=E, shapley=sh, e_full=E[(1, 1, 1)], e_ideal=E[(0, 0, 0)],
                e_cold=med(lambda: ColdFOPDT(full)), e_cv=med(lambda: ConstVel()),
                h_ref_s=h_ref * ctx.ts)


def render(ctx: C.Ctx, r: dict) -> list[str]:
    E, sh = r["E"], r["shapley"]
    L = C.result_header("Ablacao ordem-robusta + condicao inicial", ctx, generator=f"dtssl.analysis.{NAME}")
    L += [f"Mediana de e_pos (m) no bin translacional, h_ref = {r['h_ref_s']:.1f} s, mesmas janelas.", "",
          "## 1. Fatorial completo 2^3 (todas as 8 combinacoes, IC medida)", "",
          "| K | tau | Td | e_pos (m) |", "|---|---|---|---|"]
    for key in sorted(E):
        L.append(f"| {'on' if key[0] else 'off'} | {'on' if key[1] else 'off'} | "
                 f"{'on' if key[2] else 'off'} | {E[key]:.4f} |")
    L += ["", "## 2. Atribuicao de Shapley (ordem-INDEPENDENTE)", "",
          "Reducao media de e_pos atribuivel a cada grupo, sobre todas as ordens:", "",
          "| grupo | contribuicao (m) | fracao da melhoria |", "|---|---|---|"]
    tot = sum(sh)
    for n, s in zip(GROUPS, sh):
        L.append(f"| {n} | {s:+.4f} | {100 * s / tot:+.0f}% |")
    L += ["", f"Soma = {tot:+.4f} m = melhoria total (ideal {r['e_ideal']:.4f} -> completo {r['e_full']:.4f}).",
          "", "## 3. Quanto da vitoria e condicao inicial, e nao dinamica", "",
          "| planta | IC | e_pos (m) |", "|---|---|---|",
          f"| ideal kinematics (memoryless) | irrelevante | {r['e_ideal']:.4f} |",
          f"| **const-velocity extrapolation** | **usa SO a IC medida** | **{r['e_cv']:.4f}** |",
          f"| FOPDT completo | parte do repouso (como o rSim) | {r['e_cold']:.4f} |",
          f"| FOPDT completo | IC medida | {r['e_full']:.4f} |", "",
          f"- A extrapolacao de velocidade constante, que usa a IC e IGNORA os comandos, da {r['e_cv']:.4f} m.",
          f"- O gemeo sem IC medida da {r['e_cold']:.4f} m; com IC medida, {r['e_full']:.4f} m.",
          f"- Logo a IC sozinha explica {r['e_cold'] - r['e_full']:+.4f} m e a dinamica identificada o restante."]
    return L


def run(root: Path | None = None, out: Path | None = None, *, h_ref: int = 24,
        quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    r = compute(ctx, h_ref=h_ref)
    L = render(ctx, r)
    p = ctx.write_text(NAME, L)
    if not quiet:
        print("\n".join(L)); print(f"\nartefato: {p.name}")
    r["path"] = p
    return r


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
