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
    for p in r["paths"]:
        text = p.read_text(encoding="utf-8")
        assert text.count("\\begin{table") == text.count("\\end{table") == 1
        assert "results/" in text                                   # sources listed in the header
