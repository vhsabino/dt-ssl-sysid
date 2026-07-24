"""Hold-out: a fonte unica devolve exatamente os 10 eventos esperados."""
from phase0_replay import load_holdout_list, load_holdout_segments
from phase0_replay.io import event_dir

EXPECTED = [
    ("front_to_back", "front_to_back_01_01"),
    ("side_to_side", "side_to_side_01_05"),
    ("side_to_side", "side_to_side_01_06"),
    ("side_to_side", "side_to_side_01_07"),
    ("side_to_side", "side_to_side_02_03"),
    ("shoot_to_goal", "shoot_to_goal_05_02"),
    ("shoot_to_goal", "shoot_to_goal_08_01"),
    ("shoot_to_goal", "shoot_to_goal_09_01"),
    ("shoot_to_goal", "shoot_to_goal_12_01"),
    ("shoot_to_goal", "shoot_to_goal_14_02"),
]


def test_holdout_list_is_the_ten():
    cfg = load_holdout_list()
    got = [(e["label"], e["event"]) for e in cfg["events"]]
    assert got == EXPECTED
    assert len(got) == 10


def test_holdout_event_dirs_exist():
    for label, event in EXPECTED:
        d = event_dir(label, event)
        assert (d / "commands.parquet").exists(), d
        assert (d / "processed_robots.parquet").exists(), d


def test_holdout_segments_load_and_move():
    segs, dropped = load_holdout_segments(min_displacement_m=0.1)
    # todos os eventos do hold-out sao tarefas de movimento -> nenhum idle
    assert len(segs) + len(dropped) == 10
    assert len(segs) == 10, f"descartados inesperados: {dropped}"
    for s in segs:
        assert s.n > 1 and s.duration_s > 0
