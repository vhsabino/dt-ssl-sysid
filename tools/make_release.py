#!/usr/bin/env python3
"""Build the anonymised public reproduction package ``dist/dtssl-release/``.

Replaces the hand-maintained ``open-source/`` directory (removed on 2026-09-02).
What goes in (see ``MANIFEST``):

* ``src/dtssl`` (minus internal-only modules: ``analysis/meeting_overlay.py``,
  ``analysis/fig_spec_main_result.py`` — the analysis registry drops missing entries),
  ``config/``, ``tests/``, ``matlab/dtssl/``, ``docs/PREREGISTRO_OMEGA_20260724.md``,
  ``pyproject.toml``, ``LICENSE`` (anonymised), a generated ``README.md`` and
  ``requirements.txt``;
* the ``results/`` artefacts the paper cites (explicit list — never ``_BROKEN_*``);
* the rSim rollout cache converted to ``.npz`` (no pickle in the release);
* the paper figures from ``latex/figures/*.png`` (missing ones are reported).

Then a SCRUB step rewrites identifying strings (author, team, institution, firmware
repository and commit hashes, private paths, repository URL) in every text file and
finally FAILS (exit 1) if any forbidden token is still found in ANY file of the
package (text or binary).

Usage::

    python3 tools/make_release.py                 # -> dist/dtssl-release/
    python3 tools/make_release.py --out /tmp/rel --zip
    python3 tools/make_release.py --check-only    # only scan an existing package

Run from anywhere inside the repository (root auto-detected via config/twin_params.json).
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------
MANIFEST: dict = {
    "trees": {                      # source dir -> destination (relative to the package)
        "src/dtssl": "src/dtssl",
        "config": "config",
        "tests": "tests",
        "matlab/dtssl": "matlab/dtssl",
    },
    "tree_excludes": {              # path fragments excluded from the trees above
        "__pycache__", ".pyc", ".pytest_cache", ".DS_Store",
        "src/dtssl/analysis/meeting_overlay.py",         # internal meeting aid (GUIA §2.3)
        "src/dtssl/analysis/fig_spec_main_result.py",    # PT-BR internal diagram (GUIA §2.4)
    },
    "files": {                      # single files -> destination
        "docs/PREREGISTRO_OMEGA_20260724.md": "docs/PREREGISTRO_OMEGA_20260724.md",
        # pre-registrations of the extension (written before each run; PT-BR, kept verbatim)
        "docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_20260907.md": "docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_20260907.md",
        "docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_20260907.md": "docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_20260907.md",
        "docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_V2_20260907.md": "docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_V2_20260907.md",
        "docs/PREREGISTRO_C4_MALHA_FECHADA_20260908.md": "docs/PREREGISTRO_C4_MALHA_FECHADA_20260908.md",
        "docs/PREREGISTRO_C2B_SIMULADORES_LIGA_20260910.md": "docs/PREREGISTRO_C2B_SIMULADORES_LIGA_20260910.md",
        "docs/PREREGISTRO_C2B2_PREROLAGEM_20260916.md": "docs/PREREGISTRO_C2B2_PREROLAGEM_20260916.md",
        "docs/PREREGISTRO_MIMO_CHECK_20260923.md": "docs/PREREGISTRO_MIMO_CHECK_20260923.md",
        "pyproject.toml": "pyproject.toml",
        "LICENSE": "LICENSE",
    },
    "results": [                    # artefacts cited by the paper (results/<name>)
        "epos_eang_three_models_20260810_1022.md",
        "clustered_stats_20260809_2309.md",
        "ablation_orderfree_20260810_1021.md",
        "gap_decomposition_20260809_2308.md",
        "causal_ic_check_20260810_1102.md",
        "gate_window_vs_event_20260810_1743.md",
        "excitation_per_dof_20260810_1022.md",
        "omega_excitation_analysis_20260807_133917.json",
        "omega_threshold_sensitivity_20260807_133917.csv",
        "r3_closedloop_omega_fit_20260810_1036.md",
        "loo_translational_20260810_1743.md",       # NOT the 1742 run (mm/m bug, _BROKEN_)
        "negcontrol_perevent_20260810_1035.md",
        "eval_rsim_delay_ablation_20260809_2154.md",
        "eval_twin_vs_rsim_modeA_20260617_0030.md",
        "identificacao_omega_20260724.md",
        "fit_holdout_vxvy_20260731_024049.csv",
        # extension (journal manuscript): September and October 2026, every artefact the CHANGELOG cites
        "backends_holdout_20260907_1515.md",                                   # C2a
        "backends_holdout_20260907_1515.csv",
        "identifiability_insilico_20260907_1552.md",                           # C1
        "identifiability_insilico_20260907_1552.json",
        "identifiability_insilico_mujoco-velocity_20260907_2038.json",         # C1b sanity (route a)
        "identifiability_insilico_mujoco-rollers-delay_20260907_2038.json",    # C1b v1 (kept, superseded by v2)
        "identifiability_insilico_mujoco-rollers_20260907_2041.json",
        "identifiability_insilico_mujoco-rollers-delay_v2_20260907_2044.md",   # C1b v2
        "identifiability_insilico_mujoco-rollers-delay_v2_20260907_2044.json",
        "identifiability_insilico_mujoco-rollers_v2_20260907_2048.md",
        "identifiability_insilico_mujoco-rollers_v2_20260907_2048.json",
        "identifiability_insilico_fopdt_v2_20260907_2051.json",
        "session_report_sessao_01_20260907_2059.md",                           # B3
        "session_report_sessao_01_20260907_2059.json",
        "closed_loop_stats_20260907_2137.md",                                  # C4
        "closed_loop_stats_20260907_2137.json",
        "protocol_holdout_20260910_0211.md",                                   # C2b
        "protocol_holdout_20260910_0211.json",
        "protocol_holdout_20260910_0211.csv",
        "protocol_holdout_20260918_1326.md",                                   # C2b2 session 1
        "protocol_holdout_20260918_1326.json",
        "protocol_holdout_20260918_1326.csv",
        "protocol_holdout_20260920_1143.md",                                   # C2b2 session 2
        "protocol_holdout_20260920_1143.json",
        "protocol_holdout_20260920_1143.csv",
        "coupled_mimo_check_20261014_1211.md",                                 # WP2 (MIMO) + controls
        "coupled_mimo_check_20261014_1211.json",
        "coupled_mimo_check_20261014_1211.csv",
        "coupled_mimo_check_control-fopdt_20261014_1211.md",
        "coupled_mimo_check_control-fopdt_20261014_1211.json",
        "coupled_mimo_check_control-mujoco-rollers-delay_20261014_1216.md",
        "coupled_mimo_check_control-mujoco-rollers-delay_20261014_1216.json",
        "CHANGELOG.md",                                                        # provenance of every number
    ],
    "rsim_cache": "results/_cache_rsim_rollouts.pkl",       # converted to .npz
    "figures": [                    # latex/figures/<name> -> figures/<name>
        "main_result_en.png",
        "omega_stepresponse_en.png",
        "trajectory_holdout_en.png",
        "trajectory_by_label_en.png",
        "twin_vs_rsim_epos_en.png",
    ],
}

#: Strings that must NOT appear anywhere in the package (checked as bytes, all files).
FORBIDDEN: tuple[str, ...] = (
    "happy-modest-euler", "vhsabino", "Sabino", "RobôCIn", "RoboCin", "UFPE",
    "ssl-embedded", "eb57531", "C:\\Users",
    # added 14/10/2026 after the dry run of the extended package: first name alone, the user name in paths
    # (also JSON-escaped), the team name with a capital I, the lower-case institution, the PC host name
    "RoboCIn", "Victor", "victo", "ufpe", "WIN-DU3TCF0CCSB",
)

#: Ordered literal replacements applied to text files (longest / most specific first).
REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("/sessions/happy-modest-euler/mnt/digitaltwin", "<repo>"),
    ("C:\\\\Users\\\\victo\\\\Documents\\\\digitaltwin", "<repo>"),     # JSON-escaped Windows path
    ("C:\\Users\\victo\\Documents\\digitaltwin", "<repo>"),
    ("/mnt/c/Users/victo/Documents/digitaltwin", "<repo>"),
    ("C:\\\\Users\\\\victo", "<home>"),
    ("C:\\Users\\victo", "<home>"),
    ("/mnt/c/Users/victo", "<home>"),
    ("/home/victo", "<home>"),
    ("WIN-DU3TCF0CCSB", "<host>"),
    ("happy-modest-euler", "anonymous-env"),
    ("https://github.com/vhsabino/dt-ssl-sysid", "https://anonymous.4open.science/r/behavioral-twin-ssl"),
    ("vhsabino", "anonymous"),
    ("Victor H. S. Sabino (CIn-UFPE / RobôCIn)", "Anonymous (withheld for double-blind review)"),
    ("Copyright (c) 2025 Victor Sabino", "Copyright (c) 2025 Anonymous (withheld for review)"),
    ("por V. Sabino", "pelo autor (nome retido para revisão)"),
    ("Victor Sabino", "Anonymous"),
    ("V. Sabino", "Anonymous"),
    ("Sabino", "Anonymous"),
    ("Victor", "the author"),
    ("RoboCIn v2025", "SSL v2025"),
    ("RoboCIn", "the team"),
    ("RobôCIn v2025", "SSL v2025"),
    ("RobôCIn", "the team"),
    ("RoboCin", "the team"),
    ("CIn-UFPE", "the institution"),
    ("UFPE", "the institution"),
    ("eb575311dd2573805daaa560d4746cb3294a35a3", "<commit withheld>"),
    ("commit eb57531", "commit <withheld>"),
    ("eb57531", "<withheld>"),
    ("ssl-embedded", "the robot firmware repository"),
    ("C:\\Users", "<home>"),
)

#: Regex scrubs (own-repository commit hashes written into artefacts by git rev-parse).
REGEX_SCRUBS: tuple[tuple[str, str], ...] = (
    (r"commit `[0-9a-f]{7,40}(-dirty)?`", "commit `withheld`"),
    (r"commit [0-9a-f]{7}(-dirty)?\b", "commit withheld"),
)

TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".cfg", ".ini", ".m", ".csv", ".yaml",
                 ".yml", ".tex", ".bib", ".rst", ".html", ".svg", ""}

README = """# A Behavioral Model for Reality-Gap Mitigation in Digital Twins of Omnidirectional Soccer Robots

Reproduction package of the SBR/LARS 2026 paper and of its journal extension (in
preparation). Every number is produced by the code here from the configurations in
`config/`, and each claim below names the exact command and artefact that backs it;
`results/CHANGELOG.md` is the provenance log of every artefact (one entry per run).

> **Anonymised for double-blind review.** No author, institution or team name
> appears in this repository or in its commit history.

## Layout

| Path | Content |
|---|---|
| `src/dtssl/` | Python package: plants (`models/`), free-run rollout (`sim/`), multi-horizon metric and statistical gate (`eval/`), loader (`data/`), one analysis module per claim (`analysis/`) |
| `matlab/dtssl/` | MATLAB identification: per-DOF FOPDT fits, excitation diagnostics, SE(2) promotion gate |
| `config/` | Identified parameters, metric configuration, frozen hold-out list, robot geometry |
| `docs/` | Pre-registration document, committed before the yaw estimation |
| `results/` | The exact artefacts the paper cites (+ the persisted rSim rollouts, `.npz`) |
| `figures/` | Figures as they appear in the paper |
| `tests/` | pytest suite (goldens of the plant, resampling, metric, analysis registry) |

## Environment

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[mat]"           # numpy, pandas, scipy, pyarrow, matplotlib, h5py
pip install robosim==1.0          # optional: rSim (Linux/ODE) — only to re-simulate rSim
```

Python 3.10+. MATLAB with the System Identification Toolbox is needed only for
`matlab/dtssl`; the evaluation harness and every analysis below are pure Python.

## Data

Competition logs and the dedicated rotation collection are DVC-tracked. Place
the decoded splits under

```
data/extracted/<log>/splits/<label>/<event>/{commands,processed_robots}.parquet
```

`config/holdout_events.json` is the single source of truth for the ten hold-out
events (a literal list, not a seeded draw). The five events that validated `v_x`
and `v_y` are a subset of it, and the other five carry a label that entered
neither fit: no event contributed to both parameter selection and fidelity scoring
(`dtssl analysis run epos_eang_three_models` prints the check).

## One command per claim

`dtssl analysis list` shows every registered analysis with its requirements;
`dtssl analysis run <name> [--out DIR]` writes a time-stamped artefact with a
provenance header (theta, dataset, seed). Figures: `dtssl fig <name>`.

| Claim in the paper | Command | Artefact |
|---|---|---|
| Per-DOF FOPDT parameters, hold-out fit (Table I) | `matlab -batch "identify_trans_dof('x'); identify_trans_dof('y')"`, `identify_omega_rotate` | — |
| Position and heading error, three plants, six horizons (Table II, Fig. 2a) | `dtssl analysis run epos_eang_three_models` | `results/epos_eang_three_models_*.md` |
| Per-event statistics, 10/10 events, 73.5 s (Fig. 2b) | `dtssl analysis run clustered_stats` | `results/clustered_stats_*.md` |
| Order-independent ablation (Shapley) and initial-condition arms | `dtssl analysis run ablation_orderfree` | `results/ablation_orderfree_*.md` |
| Robustness to a strictly causal initial velocity | `dtssl analysis run causal_ic_check` | `results/causal_ic_check_*.md` |
| Pre-registered window gate vs per-event analysis | `dtssl analysis run gate_window_vs_event` | `results/gate_window_vs_event_*.md` |
| Screening: actuation share and explained variance per DOF | `dtssl analysis run excitation_per_dof` | `results/excitation_per_dof_*.md` |
| Dilution analysis, threshold sensitivity, wheel-angle sweep | `dtssl analysis run analyze_omega_excitation` | `results/omega_excitation_analysis_*.json` |
| Closed-loop yaw fit under the paper's hold-out criterion | `dtssl analysis run r3_closedloop_omega_fit` | `results/r3_closedloop_omega_fit_*.md` |
| Leave-one-event-out dispersion of the vx/vy fits | `dtssl analysis run loo_translational` | `results/loo_translational_*.md` |
| Negative control (joint Bayesian calibration), per event | `dtssl analysis run negcontrol_perevent` | `results/negcontrol_perevent_*.md` |
| Matched-delay ablation on rSim | `dtssl analysis run eval_rsim_delay_ablation` (`--kw mode=cache` first, needs robosim) | `results/eval_rsim_delay_ablation_*.md` |
| Twin vs rSim gate (mode A) | `dtssl analysis run eval_twin_vs_rsim` (needs robosim) | `results/eval_twin_vs_rsim_modeA_*.md` |
| Main figure | `dtssl fig fig_main_result` | `figures/main_result_en.png` |
| Yaw step response | `dtssl fig fig_omega_stepresponse_en` | `figures/omega_stepresponse_en.png` |

rSim rollouts are persisted in `results/_cache_rsim_rollouts.npz` so that the
rSim comparisons do not need to re-simulate.

## Extension (journal manuscript): one command per claim

Each run has a pre-registration in `docs/` written before any number was computed.

| Claim | Command | Artefact |
|---|---|---|
| MuJoCo routes a and b against the behavioral plant on the frozen hold-out (C2a) | `dtssl analysis run backends_holdout` (needs mujoco) | `results/backends_holdout_*.md` |
| In-silico identifiability by excitation regime, linear generator (C1) | `dtssl analysis run identifiability_insilico` | `results/identifiability_insilico_*.json` |
| In-silico mechanism of the closed-loop yaw bias, physical generators (C1b v2) | `dtssl analysis run identifiability_insilico --kw variant=v2 generator=mujoco-rollers-delay` (and `mujoco-rollers`) | `results/identifiability_insilico_mujoco-*_v2_*.json` |
| Recorded closed-loop session against the twin, round trip of the harness (B3) | `dtssl analysis run session_report --kw session=results/sessao_01` (session under DVC) | `results/session_report_*.json` |
| Closed-loop plausibility against the competition logs (C4) | `dtssl analysis run closed_loop_stats` | `results/closed_loop_stats_*.json` |
| grSim and ER-Force on the hold-out through the ssl-simulation-protocol (C2b) | `tools/external_sims/run_protocol_holdout.sh` (WSL2/Linux, simulators installed), `dtssl analysis run protocol_holdout --kw from_cache=...` | `results/protocol_holdout_*.json` |
| Pre-rolled league simulators, fair initial condition (C2b2, two sessions) | `tools/external_sims/run_protocol_holdout.sh --delay none --preroll 0.5` | `results/protocol_holdout_2026091*.json`, `_20260920_*.json` |
| Cross-coupling (MIMO) check with in-silico controls (WP2) | `dtssl analysis run coupled_mimo_check` (+ `--kw control=fopdt` and `control=mujoco-rollers-delay`) | `results/coupled_mimo_check_*.{md,json}` |
| Journal tables and figures from the artefacts (no recomputation) | `dtssl analysis run journal_tables`, `dtssl fig fig_journal_identifiability` / `fig_journal_league_sims` / `fig_journal_closed_loop` | `latex_journal/tables/`, `latex_journal/figures/` |

## Definitions used in the paper

**hold-out fit.** Normalised RMSE as a percentage, of the model output against
the measured body velocity, on events never used for fitting:
`fit = 100 · (1 − ‖y − ŷ‖ / ‖y − mean(y)‖)`. 100% is exact, 0% is no better than
predicting the mean. Computed per event, then averaged over hold-out events. The
model runs in simulation, driven by commands only, not one-step prediction.

**free run.** The model starts at a known pose and is driven only by the
recorded command stream, with no correction from measured data inside the
window. Scoring one step at a time instead would measure sensor noise and
overstate fidelity.

**actuation share.** The fraction of the commanded per-wheel effort attributable
to one command channel. Computed from the log alone, before any fit.

**explained variance.** The fraction of the attained body velocity that its own
command accounts for, once aligned by the identified dead time.

**placeholder.** The no-dynamics reference used by the yaw promotion gate:
`K = 1`, `τ = 0.1 s`, `Td = 0`.

## A note on the initial condition

The loader estimates the initial body velocity with a central difference, which
at the window anchor reads one sample from inside the evaluation window.
`dtssl analysis run causal_ic_check` re-runs everything with a strictly causal
backward difference: both plants get worse, the gap widens, and the verdict is
unchanged. The result does not depend on that sample.
"""


# ---------------------------------------------------------------------------
def _excluded(rel: str, excludes: set[str]) -> bool:
    return any(frag in rel for frag in excludes)


def copy_tree(src: Path, dst: Path, excludes: set[str], rel_prefix: str) -> int:
    n = 0
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        rel = f"{rel_prefix}/{p.relative_to(src).as_posix()}"
        if _excluded(rel, excludes):
            continue
        d = dst / p.relative_to(src)
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, d)
        n += 1
    return n


def requirements_from_pyproject(pyproject: Path) -> list[str]:
    try:
        import tomllib
    except ImportError:  # pragma: no cover (py<3.11)
        return ["numpy>=1.26", "pandas>=2.1", "scipy>=1.11", "pyarrow>=14", "matplotlib>=3.8"]
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    deps = list(data["project"]["dependencies"])
    deps += data["project"].get("optional-dependencies", {}).get("mat", [])
    return deps


def build(root: Path, out: Path, *, zip_it: bool = False, strict: bool = False) -> Path:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    m = MANIFEST
    excludes = set(m["tree_excludes"])
    warnings: list[str] = []

    for src_rel, dst_rel in m["trees"].items():
        src = root / src_rel
        if not src.is_dir():
            warnings.append(f"missing tree {src_rel}")
            continue
        n = copy_tree(src, out / dst_rel, excludes, src_rel)
        print(f"  {src_rel:32s} -> {dst_rel}  ({n} files)")

    for src_rel, dst_rel in m["files"].items():
        src = root / src_rel
        if not src.is_file():
            warnings.append(f"missing file {src_rel}")
            continue
        (out / dst_rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out / dst_rel)

    (out / "results").mkdir(exist_ok=True)
    for name in m["results"]:
        if name.startswith("_BROKEN_"):
            raise SystemExit(f"manifest must never ship a _BROKEN_ artefact: {name}")
        src = root / "results" / name
        if not src.is_file():
            warnings.append(f"missing result {name}")
            continue
        shutil.copy2(src, out / "results" / name)

    cache = root / m["rsim_cache"]
    if cache.is_file():
        from dtssl.sim.rollout import convert_pickle_cache
        npz = convert_pickle_cache(cache, out / "results" / "_cache_rsim_rollouts.npz")
        print(f"  {m['rsim_cache']:32s} -> results/{npz.name} (+ .json)")
    else:
        npz_src = cache.with_suffix(".npz")
        if npz_src.is_file():
            shutil.copy2(npz_src, out / "results" / npz_src.name)
            if npz_src.with_suffix(".json").is_file():
                shutil.copy2(npz_src.with_suffix(".json"), out / "results" / npz_src.with_suffix(".json").name)
        else:
            warnings.append("missing rSim cache (results/_cache_rsim_rollouts.{pkl,npz})")

    (out / "figures").mkdir(exist_ok=True)
    for name in m["figures"]:
        src = root / "latex" / "figures" / name
        if src.is_file():
            shutil.copy2(src, out / "figures" / name)
        else:
            warnings.append(f"missing figure latex/figures/{name}")

    (out / "README.md").write_text(README, encoding="utf-8")
    (out / "requirements.txt").write_text("\n".join(requirements_from_pyproject(root / "pyproject.toml")) + "\n",
                                          encoding="utf-8")

    n_scrubbed = scrub(out)
    print(f"  scrub: {n_scrubbed} file(s) rewritten")
    leaks = scan(out)
    for w in warnings:
        print(f"  WARNING: {w}")
    if leaks:
        print("\nFORBIDDEN tokens still present:")
        for line in leaks:
            print(f"  {line}")
        raise SystemExit(1)
    if strict and warnings:
        raise SystemExit(f"{len(warnings)} warning(s) with --strict")
    if zip_it:
        zpath = out.with_suffix(".zip")
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(out.rglob("*")):
                if p.is_file():
                    z.write(p, f"{out.name}/{p.relative_to(out).as_posix()}")
        print(f"  zip: {zpath}")
    print(f"\nrelease package: {out}  (clean: no forbidden token)")
    return out


def scrub(out: Path) -> int:
    n = 0
    for p in sorted(out.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = text
        for old, rep in REPLACEMENTS:
            new = new.replace(old, rep)
        for pat, rep in REGEX_SCRUBS:
            new = re.sub(pat, rep, new)
        if new != text:
            p.write_text(new, encoding="utf-8")
            n += 1
    return n


def scan(out: Path) -> list[str]:
    """All files, as bytes: every forbidden token in every encoding we care about."""
    needles = []
    for tok in FORBIDDEN:
        needles.append((tok, tok.encode("utf-8")))
        try:
            latin = tok.encode("latin-1")
            if latin != tok.encode("utf-8"):
                needles.append((tok, latin))
        except UnicodeEncodeError:
            pass
    leaks = []
    for p in sorted(out.rglob("*")):
        if not p.is_file():
            continue
        data = p.read_bytes()
        for tok, nb in needles:
            if nb in data:
                line_no = data[:data.index(nb)].count(b"\n") + 1
                leaks.append(f"{p.relative_to(out)}:{line_no}: {tok!r}")
    return leaks


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "dtssl-release")
    ap.add_argument("--zip", action="store_true", help="also write <out>.zip")
    ap.add_argument("--strict", action="store_true", help="fail on missing manifest entries")
    ap.add_argument("--check-only", action="store_true", help="only scan an existing package")
    a = ap.parse_args(argv)
    if a.check_only:
        leaks = scan(a.out)
        for line in leaks:
            print(line)
        print("clean" if not leaks else f"{len(leaks)} leak(s)")
        return 1 if leaks else 0
    print(f"building {a.out} from {ROOT}")
    build(ROOT, a.out, zip_it=a.zip, strict=a.strict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
