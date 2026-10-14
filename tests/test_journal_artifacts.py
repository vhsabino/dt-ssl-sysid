"""Journal extension: the numbers read from the result artefacts, and the figures and tables built on them.

No dataset: everything comes from ``results/*.md|json|csv``. The expected values are the ones quoted in
``results/CHANGELOG.md``; a test is skipped when its artefact is absent (e.g. a clone without the
18/09 session committed yet).
"""
from __future__ import annotations

import pytest

from dtssl.analysis import fig_journal_closed_loop, fig_journal_identifiability, fig_journal_league_sims
from dtssl.analysis import journal_artifacts as J
from dtssl.analysis import journal_tables as T


def need(*keys: str) -> None:
    missing = [k for k in keys if not J.available(k)]
    if missing:
        pytest.skip(f"artefacts not present: {', '.join(J.ARTEFACTS[k] for k in missing)}")


def test_md_table_parser():
    text = "x\n| a | b |\n|---|---|\n| 1 | **2.5** |\n\nfoo\n| c |\n|---|\n| +0.3 |\n"
    t = J.md_tables(text)
    assert t == [[["a", "b"], ["1", "**2.5**"]], [["c"], ["+0.3"]]]
    assert J._num("**0.0388**") == 0.0388 and J._num("+0.0689 m") == 0.0689 and J._num("44.8 %") == 44.8


def test_sbr_numbers():
    need("three_models", "clustered", "gate", "shapley", "causal", "loo", "r3", "negctl", "rsim_delay", "excitation")
    h = {round(r["h_s"], 2): r for r in J.three_models()}
    assert (h[0.4]["epos"]["model"], h[0.4]["epos"]["ideal"], h[0.4]["epos"]["rsim"]) == (0.0388, 0.1005, 0.1293)
    assert (h[1.5]["epos"]["model"], h[1.5]["epos"]["ideal"]) == (0.1193, 0.2910)
    c = J.clustered()
    assert c["seconds"] == 73.5 and c["gap"] == 0.0689 and len(c["events"]) == 10
    g = J.gate()
    assert g["window"]["n"] == 49 and g["event"]["n"] == 10 and g["event"]["rb"] == 1.0
    s = J.shapley()
    assert [round(s["shares"][k]["fraction"], 2) for k in ("tau", "Td", "K")] == [0.55, 0.43, 0.02]
    assert s["ic"] == dict(ideal=0.1005, constant_velocity=0.16, model_from_rest=0.1137, model_measured_ic=0.0388)
    assert J.causal()["causal"]["epos_04"] == 0.0468
    lo = J.loo()
    assert (lo["vx"]["fit_mean"], lo["vx"]["fit_sd"], lo["vx"]["n_folds"]) == (84.3, 2.0, 4)
    assert (lo["vy"]["fit_mean"], lo["vy"]["fit_sd"], lo["vy"]["n_folds"]) == (82.8, 2.7, 13)
    r3 = J.r3()
    assert r3["closed_loop"]["K"] == 1.378 and r3["closed_loop"]["fit"] == 44.8 and r3["open_loop"]["fit"] == 71.1
    n = J.negctl()["perdof_vs_bayesopt"]
    assert (n["gap"], n["wins"], n["p"]) == (0.0038, "7/10", 0.04199)
    assert {round(r["h_s"], 2): r for r in J.rsim_delay()}[0.4]["rsim_delay"] == 0.1822
    assert J.excitation()["w"]["r2"] == 0.557


def test_september_numbers():
    need("c1", "c1b_delay", "c1b_nodelay", "c2a", "c2a_csv", "c4", "c2b", "c2b2_s2")
    y = J.yaw_insilico()
    assert round(y["route b + delay"][("R1", "none", "off")]["med"], 3) == 1.160
    assert round(y["route b + delay"][("R1", "vision", "on")]["med"], 3) == 1.270
    assert round(y["route b + delay"][("R1-wonly", "none", "off")]["med"], 3) == 0.988
    assert round(y["route b + delay"][("R2-rotate", "none", "off")]["med"], 3) == 0.996
    assert round(y["route b"][("R1", "none", "off")]["med"], 3) == 1.156
    b = J.backends()
    assert b["per_event"]["mujoco-rollers"]["event_median"] == 0.0791 and b["twin_event_median"] == 0.0421
    c2b = J.league_session("c2b")
    assert round(c2b["variants"]["erforce"]["window_median"], 4) == 0.0881
    assert round(c2b["variants"]["erforce+delay"]["window_median"], 4) == 0.0555
    assert round(c2b["variants"]["grsim"]["event_median"], 4) == 0.2341
    s2 = J.league_session("c2b2_s2")
    assert round(s2["variants"]["grsim+preroll"]["window_median"], 4) == 0.0809
    assert round(s2["variants"]["grsim+preroll"]["event_median"], 4) == 0.0975
    assert round(s2["variants"]["erforce+preroll"]["event_median"], 4) == 0.1114
    assert round(s2["model_event_median"], 4) == 0.0421
    assert round(s2["model_states_zeroed"][2], 4) == 0.1137 and round(s2["model_prerolled"][2], 4) == 0.0406
    assert all(v["wins"] == 10 for v in s2["variants"].values())
    cl = J.closed_loop()
    assert cl["criteria"]["score"] == 2 and round(cl["pool"]["frac_w_below_dz"], 3) == 0.905


def test_second_c2b2_session():
    need("c2b2_s1")
    s1 = J.league_session("c2b2_s1")
    assert round(s1["variants"]["grsim+preroll"]["window_median"], 4) == 0.0996
    assert round(s1["variants"]["grsim+preroll"]["event_median"], 4) == 0.1106
    assert round(s1["variants"]["erforce+preroll"]["window_median"], 4) == 0.0934
    assert all(s1["validity"].values())


def test_mimo_numbers():
    """WP2 (CHANGELOG 2026-10-14 12:11): M1 does not matter, M2 falsified, M3 no improvement, C- OK, C+ premise
    not reproduced."""
    need("mimo", "mimo_cminus", "mimo_cplus")
    m = J.coupling()
    assert (m["n_train"], m["n_test"], m["delays"]) == (36, 10, [5, 4, 6]) and round(m["K_ref"], 4) == 1.0016
    fp = m["fit_pooled"]
    assert [round(fp["promoted"][d], 1) for d in ("vx", "vy", "w")] == [75.3, 79.7, 40.1]
    assert [round(fp["diagonal"][d], 1) for d in ("vx", "vy", "w")] == [75.5, 79.9, 48.8]
    assert [round(fp["coupled"][d], 1) for d in ("vx", "vy", "w")] == [76.5, 80.1, 48.9]
    m1 = m["m1"]
    assert [round(m1["per_dof"][d]["fit_gain_pp"], 2) for d in ("vx", "vy", "w")] == [0.95, 0.23, 0.13]
    assert [round(m1["per_dof"][d]["contrib_ratio"], 3) for d in ("vx", "vy", "w")] == [0.058, 0.039, 0.048]
    assert not m1["coupling_matters"] and not m["pair_delays"]["m1"]["coupling_matters"]
    m2 = m["m2"]
    assert (round(m2["G_diag"], 4), round(m2["G_coupled"], 4), m2["premise"], m2["status"]) == (
        1.419, 1.4138, True, "FALSIFICADA")
    assert round(m2["inflation_diag"], 3) == 0.417 and round(m2["fraction_removed"], 2) == 0.01
    assert (round(m["m2_game"]["G_diag"], 4), m["m2_game"]["n_train"]) == (1.3719, 13)
    assert round(m["pair_delays"]["m2"]["G_coupled"], 4) == 1.4127
    ci = m["bootstrap"]["ci95"]
    assert m["bootstrap"]["n_boot"] == 200 and [round(v, 3) for v in ci["G_diag_w"]] == [1.36, 1.517]
    assert [round(v, 3) for v in ci["gain_vx"]] == [0.616, 1.07]
    assert [round(v, 3) for v in ci["ratio_w"]] == [0.026, 0.074]
    h = m["harness"]
    assert (h["n_windows"], h["n_trans"], round(h["sanity_promoted_event_median"], 4)) == (265, 264, 0.0421)
    ref = next(r for r in h["rows"] if abs(r["h_s"] - 0.4) < 1e-9)
    assert [round(ref["epos"][k], 4) for k in ("promoted", "diagonal", "coupled")] == [0.0388, 0.039, 0.0381]
    m3 = h["m3"]
    assert (m3["wins"], round(m3["p"], 3), round(m3["rb"], 2), m3["improves"]) == (6, 0.461, 0.05, False)
    c = m["controls"]
    nc = c["fopdt"]["negative_control"]
    assert nc["ok"] and round(nc["G"]["diagonal"], 4) == 0.9997 and round(nc["truth"], 4) == 1.0017
    cp = c["mujoco-rollers-delay"]
    assert not cp["m2"]["premise"] and round(cp["m2"]["inflation_diag"], 3) == 0.072
    assert round(cp["K_ref"], 4) == 0.9964
    assert round(cp["ratios"]["w"]["per_input"]["vy"], 3) == 0.216 and not cp["m1"]["coupling_matters"]


@pytest.mark.parametrize("mod", [fig_journal_identifiability, fig_journal_league_sims, fig_journal_closed_loop])
def test_journal_figures_render(mod, tmp_path):
    need("c1", "c1b_delay", "c1b_nodelay", "r3", "c2b", "c2b2_s1", "c2b2_s2", "c4")
    r = mod.run(out=tmp_path, latex_copy=False, quiet=True)
    assert r["paths"]["pdf"].is_file() and r["paths"]["png"].is_file()
    assert r["paths"]["pdf"].stat().st_size > 5000


def test_journal_tables_write_latex(tmp_path):
    need(*J.ARTEFACTS)
    r = T.run(tables_dir=str(tmp_path), quiet=True)
    names = {p.name for p in r["paths"]}
    assert names == {f"tab_journal_{n}.tex" for n in T.TABLES}
    base = (tmp_path / "tab_journal_baselines.tex").read_text(encoding="utf-8")
    assert "0.0809" in base and "0.1106" in base and "0.2389" in base and "\\label{tab:baselines}" in base
    ident = (tmp_path / "tab_journal_identified.tex").read_text(encoding="utf-8")
    assert "86.7" in ident and "1.378" in ident and "$84.3\\pm2.0$" in ident
    coup = (tmp_path / "tab_journal_coupling.tex").read_text(encoding="utf-8")
    assert "1.419 $\\rightarrow$ 1.414" in coup and "6/10, $p = 0.46$" in coup and "\\label{tab:coupling}" in coup
    assert "+0.95 [+0.62, +1.07]" in coup and "0.058 [0.046, 0.076]" in coup and "falsified" in coup
    for p in r["paths"]:
        text = p.read_text(encoding="utf-8")
        assert text.count("\\begin{table") == text.count("\\end{table") == 1
        assert "results/" in text                                   # sources listed in the header
