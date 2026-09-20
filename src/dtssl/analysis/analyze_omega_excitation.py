"""Yaw dilution analysis: threshold sensitivity (C9) and wheel-level dead-zone check (B4).

Hypothesis H-B4: the dead zone is ELECTRICAL and PER WHEEL, applied after the
inverse kinematics (firmware clamp ``MOTOR_MIN_SPEED_RAD_S = 1.567 rad/s`` on
each wheel setpoint). The body-yaw threshold 0.58-0.60 rad/s is that clamp
converted for PURE rotation only (the ``rotate`` regime). In play, translation
and rotation are simultaneous: the wheel setpoints are dominated by the
translational term, the wheels already spin far above the clamp and the yaw
command is NOT zeroed — it is a small perturbation on a large wheel speed.

Angle-independent metric: for any 4-wheel layout with pair symmetry
``sum_i cos^2(a_i - phi) = 2`` for every ``phi``, so the per-wheel RMS of the
translational term is ``t_rms = |v| / (r*sqrt(2))`` exactly; the yaw term is
``y = (R/r)*|w|``. A sweep over plausible wheel-angle sets checks that the
conclusion is invariant to the (then undocumented) mounting angles.

Reads every ``commands.{csv,parquet}`` of the competition labels (CSV when
present, else parquet — identical columns). Constants from
config/robot_geometry.json. Writes ``omega_excitation_analysis_<stamp>.json`` and
``omega_threshold_sensitivity_<stamp>.csv``.

Legacy: scripts/analyze_omega_excitation.py -> results/omega_excitation_analysis_20260807_133917.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from dtssl.analysis import common as C

NAME = "analyze_omega_excitation"
KIND = "analysis"
CLAIM = "Dilution analysis, threshold sensitivity, wheel-angle sweep (B4/C9 of review 2026-07-31)"
REQUIRES = ("data",)
COMPETITION_LABELS = ("front_to_back", "side_to_side", "shoot_to_goal", "square")


def load_commands(ctx: C.Ctx, labels=COMPETITION_LABELS) -> pd.DataFrame:
    """Concatenate the commands table of every competition event."""
    rows = []
    for label in labels:
        for ev in C.list_events(ctx.splits_dir, label):
            try:
                cmd, _ = C.read_event_csv(label, ev, dataset=ctx.dataset, data_root=ctx.data_root)
            except FileNotFoundError:
                continue
            df = cmd[["move_x", "move_y", "move_w"]].copy()
            df["label"] = label
            df["event"] = ev
            rows.append(df)
    if not rows:
        raise FileNotFoundError(f"no commands table found under {ctx.splits_dir}")
    return pd.concat(rows, ignore_index=True)


def compute(ctx: C.Ctx) -> tuple[dict, list[dict]]:
    G = ctx.geometry
    R = G["physical"]["R_contact_m"]
    r = G["physical"]["wheel_radius_m"]
    R_OVER_R_FW = G["firmware"]["R_over_r_implied"]
    MOTOR_MIN = G["firmware"]["motor_min_speed_rad_s"]
    DZ_LO, DZ_HI = G["firmware"]["omega_cmd_deadzone_rad_s_range"]
    thresholds = [0.5, DZ_LO, DZ_HI, 1.0]

    cmd = load_commands(ctx).dropna(subset=["move_x", "move_y", "move_w"])
    w = cmd["move_w"].to_numpy(float)
    vmag = np.hypot(cmd["move_x"].to_numpy(float), cmd["move_y"].to_numpy(float))
    t_rms = vmag / (r * np.sqrt(2.0))
    y_term = R_OVER_R_FW * np.abs(w)
    n = len(cmd)

    out = {"_meta": {
        "gerado_em": ctx.stamp, "script": f"dtssl.analysis.{NAME}", "commit": C.git_commit(ctx.root),
        "n_amostras": int(n), "n_eventos": int(cmd["event"].nunique()), "labels": list(COMPETITION_LABELS),
        "constantes": {"R_contact_m": R, "wheel_radius_m": r, "R_over_r_firmware": R_OVER_R_FW,
                       "motor_min_speed_rad_s": MOTOR_MIN, "deadzone_corpo_rad_s": [DZ_LO, DZ_HI]},
        "fonte_constantes": "config/robot_geometry.json"}}

    sens = []
    sub = (cmd["label"] == "shoot_to_goal").to_numpy()
    for th in thresholds:
        sens.append({"limiar_rad_s": th,
                     "frac_abaixo_pooled_pct": 100 * float(np.mean(np.abs(w) < th)),
                     "frac_abaixo_shoot_to_goal_pct": 100 * float(np.mean(np.abs(w[sub]) < th))})
    out["C9_sensibilidade_limiar"] = sens

    below = np.abs(w) < DZ_LO
    nb = int(below.sum())
    b4 = {"definicao": ("entre as amostras com |w_cmd| < limiar de corpo, qual "
                        "fração tem setpoint de roda (RMS) acima do clamp do motor"),
          "n_amostras_sub_limiar": nb, "frac_sub_limiar_pct": 100.0 * nb / n,
          "t_rms_mediana_rad_s": float(np.median(t_rms[below])),
          "t_rms_p10_rad_s": float(np.percentile(t_rms[below], 10)),
          "t_rms_p90_rad_s": float(np.percentile(t_rms[below], 90)),
          "frac_rodas_acima_do_clamp_pct": 100.0 * float(np.mean(t_rms[below] > MOTOR_MIN)),
          "vmag_mediana_m_s": float(np.median(vmag[below]))}
    with np.errstate(divide="ignore", invalid="ignore"):
        snr = np.where(t_rms[below] > 0, y_term[below] / t_rms[below], np.nan)
    b4["snr_yaw_sobre_translacao_mediana"] = float(np.nanmedian(snr))
    b4["snr_yaw_sobre_translacao_p90"] = float(np.nanpercentile(snr, 90))
    b4["frac_rotacao_quase_pura_pct"] = 100.0 * float(np.mean(below & (t_rms < MOTOR_MIN)))
    out["B4_zona_morta_vs_translacao"] = b4

    vx_b = cmd["move_x"].to_numpy(float)[below]
    vy_b = cmd["move_y"].to_numpy(float)[below]
    w_b = w[below]
    sweep = []
    for a_deg in (30.0, 45.0, 60.0):
        for b_deg in (120.0, 135.0, 150.0):
            ang = np.radians([a_deg, b_deg, -b_deg, -a_deg])
            t_i = (-np.sin(ang)[:, None] * vx_b + np.cos(ang)[:, None] * vy_b) / r
            sp = t_i + R_OVER_R_FW * w_b[None, :]
            clamped = np.abs(sp) < MOTOR_MIN
            sweep.append({"angulos_deg": [a_deg, b_deg, -b_deg, -a_deg],
                          "frac_rodas_clampadas_pct": 100.0 * float(clamped.mean()),
                          "frac_amostras_com_4_rodas_clampadas_pct": 100.0 * float(clamped.all(axis=0).mean()),
                          "frac_amostras_com_alguma_roda_ativa_pct": 100.0 * float((~clamped).any(axis=0).mean())})
    out["B4_robustez_angulos"] = {
        "nota": ("varredura sobre conjuntos plausíveis de ângulos porque os ângulos reais não "
                 "estavam em config/robot_geometry.json na época; a conclusão de B4 deve ser "
                 "invariante ao conjunto escolhido"),
        "varredura": sweep,
        "frac_amostras_com_alguma_roda_ativa_min_pct": min(s["frac_amostras_com_alguma_roda_ativa_pct"] for s in sweep),
        "frac_amostras_com_alguma_roda_ativa_max_pct": max(s["frac_amostras_com_alguma_roda_ativa_pct"] for s in sweep)}
    out["B4_contraste_rotate"] = {
        "nota": ("no dataset `rotate` vx=vy=0 por construção, logo t_rms=0 e o clamp morde "
                 "exatamente no limiar de corpo — é o unico regime em que o joelho de zona "
                 "morta é observável no yaw de corpo"),
        "t_rms_rad_s": 0.0}
    return out, sens


def run(root: Path | None = None, out: Path | None = None, *, quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out, stamp_fmt=C.STAMP_FMT_S)
    res, sens = compute(ctx)
    jf = ctx.out_path("omega_excitation_analysis", "json")
    cf = ctx.out_path("omega_threshold_sensitivity", "csv")
    jf.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame(sens).to_csv(cf, index=False)
    if not quiet:
        m, b4, rb = res["_meta"], res["B4_zona_morta_vs_translacao"], res["B4_robustez_angulos"]
        print(f"amostras={m['n_amostras']}  eventos={m['n_eventos']}  (esperado 46)")
        print("\n--- C9: sensibilidade da fração sub-limiar ---")
        print(pd.DataFrame(sens).to_string(index=False, float_format=lambda x: f"{x:8.2f}"))
        print("\n--- B4: entre as amostras sub-limiar ---")
        for k, v in b4.items():
            if k != "definicao":
                print(f"  {k:42s} {v}")
        print("\n--- B4: robustez aos ângulos de montagem ---")
        print(pd.DataFrame(rb["varredura"]).to_string(index=False, float_format=lambda x: f"{x:8.2f}"))
        print(f"  alguma roda ativa: min={rb['frac_amostras_com_alguma_roda_ativa_min_pct']:.2f}% "
              f"max={rb['frac_amostras_com_alguma_roda_ativa_max_pct']:.2f}%")
        print(f"\nartefatos:\n  {jf}\n  {cf}")
    return dict(path=jf, csv=cf, result=res, sensitivity=sens)


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
