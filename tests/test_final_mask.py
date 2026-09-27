"""Train/serve-mask tests: stored indices 72/73 are identically zero in FINAL inputs."""

import numpy as np
import pytest

from hierarchical_triple_ejection.features import (
    FEATURE_NAMES,
    FINAL_DISABLED_INDICES,
    apply_final_mask,
)


def test_final_disabled_indices_are_72_and_73():
    assert tuple(FINAL_DISABLED_INDICES) == (72, 73)
    assert len(FEATURE_NAMES) == 79
    assert FEATURE_NAMES[73] == "n_frac"
    assert "breach" in FEATURE_NAMES[72].lower()


def test_apply_final_mask_zeros_slots_vector_and_batch():
    rng = np.random.default_rng(0)
    for shape in [(79,), (16, 79)]:
        x = rng.normal(size=shape) + 5.0  # nonzero everywhere, incl. 72/73
        y = apply_final_mask(x)
        assert y.shape == x.shape
        assert np.all(y[..., 72] == 0.0)
        assert np.all(y[..., 73] == 0.0)
        kept = [i for i in range(79) if i not in (72, 73)]
        np.testing.assert_array_equal(y[..., kept], x[..., kept])


def test_apply_final_mask_does_not_mutate_and_is_idempotent():
    x = np.ones((4, 79))
    y = apply_final_mask(x)
    assert np.all(x == 1.0)  # input untouched
    np.testing.assert_array_equal(apply_final_mask(y), y)


def test_apply_final_mask_rejects_short_vectors():
    with pytest.raises(ValueError):
        apply_final_mask(np.ones(10))
