"""Validacao do schema: Segment valido passa; NaN/gaps sao detectados."""
import dataclasses

import numpy as np
import pytest

from dtssl import load_segment
from dtssl.data.schema import validate_segment

pytestmark = pytest.mark.requires_data   # every test here loads a real event


@pytest.fixture(scope="module")
def seg():
    return load_segment("side_to_side", "side_to_side_01_05")


def test_valid_segment_has_no_issues(seg):
    assert validate_segment(seg, raise_on_error=False) == []


def test_nan_is_detected(seg):
    bad = dataclasses.replace(seg, pos_x=seg.pos_x.copy())
    bad.pos_x[5] = np.nan
    issues = validate_segment(bad, raise_on_error=False)
    assert any("pos_x" in m and "NaN" in m for m in issues)
    with pytest.raises(ValueError):
        validate_segment(bad, raise_on_error=True)


def test_gap_in_grid_is_detected(seg):
    t2 = seg.t.copy()
    t2[10:] += 0.05            # injeta um gap de timestamp
    bad = dataclasses.replace(seg, t=t2)
    issues = validate_segment(bad, raise_on_error=False)
    assert any("grade nao uniforme" in m or "gap" in m for m in issues)
