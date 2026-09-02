"""Screening per DOF in the competition logs: corr(cmd, meas) and explained variance.

For each DOF the command (aligned by the identified dead time, ``round(Td/dt)``
samples) is compared with the measured body velocity obtained with the paper's
pre-processing (Savitzky-Golay window 7 order 2 + central differences) over all
events of the DOF's label (vx: front_to_back, vy: side_to_side, w: shoot_to_goal):
Pearson correlation, R^2 of a linear regression, std of command and measurement.

Data path: legacy resampling (``common.legacy_uy_series``: ``np.arange`` grid,
LINEAR command interpolation, absolute ``timestamp``), read from
``commands.csv``/``processed_robots.csv`` when present, else the parquet twins.
Positions are kept in the logged mm (``std meas`` in mm/s for vx/vy), exactly as
the published table.

Legacy: scripts/excitation_per_dof.py -> results/excitation_per_dof_20260810_1022.md.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from dtssl.analysis import common as C

NAME = "excitation_per_dof"
KIND = "analysis"
CLAIM = "Screening: actuation share and explained variance per DOF (C8/C9, Q7/Q8)"
REQUIRES = ("data",)
LABELS = {"vx": "front_to_back", "vy": "side_to_side", "w": "shoot_to_goal"}


def compute(ctx: C.Ctx, labels: dict[str, str] | None = None, min_len: int = 40) -> dict:
    labels = labels or LABELS
    dt = ctx.ts
    rows = []
    for dof, label in labels.items():
        Td = ctx.params[dof].Td
        m = int(round(Td / dt))
        U, Y = [], []
        for ev in C.list_events(ctx.splits_dir, label):
            cmd, rob = C.read_event_csv(label, ev, dataset=ctx.dataset, data_root=ctx.data_root)
            s = C.legacy_uy_series(cmd, rob, dof, dt, min_len=min_len, pos_scale=1.0)
            if s is None:
                continue
            u, y = s
            if m > 0:
                u, y = u[:-m], y[m:]
            U.append(u); Y.append(y)
        u, y = np.concatenate(U), np.concatenate(Y)
        r = float(np.corrcoef(u, y)[0, 1])
        b = np.polyfit(u, y, 1)
        yh = np.polyval(b, u)
        r2 = 1 - float(np.sum((y - yh) ** 2) / np.sum((y - np.mean(y)) ** 2))
        rows.append(dict(dof=dof, label=label, n=int(len(u)), corr=r, R2=r2,
                         std_cmd=float(np.std(u)), std_meas=float(np.std(y)), lag=m))
    return dict(rows=rows)


def render(ctx: C.Ctx, r: dict) -> list[str]:
    L = C.result_header("Excitacao por DOF nos logs de competicao", ctx, generator=f"dtssl.analysis.{NAME}")
    L += ["Comando alinhado pelo Td identificado; velocidade de corpo medida pelo mesmo",
          "pre-processamento do artigo (Savitzky-Golay janela 7 ordem 2 + diferencas centrais).", "",
          "| DOF | label | n | corr(cmd, meas) | R^2 (var. explicada) | std cmd | std meas |",
          "|---|---|---|---|---|---|---|"]
    for d in r["rows"]:
        L.append(f"| {d['dof']} | `{d['label']}` | {d['n']} | **{d['corr']:.3f}** | **{d['R2']:.3f}** "
                 f"| {d['std_cmd']:.3f} | {d['std_meas']:.3f} |")
    L += ["", "Leitura: para vx/vy o comando explica a maior parte da variancia da velocidade",
          "medida; para omega, nao. Esse e o diagnostico espectral/de correlacao que faltava",
          "(objecoes C8/C9 e perguntas 7-8 do revisor)."]
    return L


def run(root: Path | None = None, out: Path | None = None, *, quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    r = compute(ctx)
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
