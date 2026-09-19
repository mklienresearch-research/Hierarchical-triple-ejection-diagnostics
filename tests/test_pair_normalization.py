import numpy as np

from hierarchical_triple_ejection.core import pair_diagnostics


def test_total_mass_pair_sums_match_total_com_quantities():
    rng = np.random.default_rng(7)
    m = np.array([0.7, 1.3, 2.1])
    r = rng.normal(size=(3, 3))
    v = rng.normal(size=(3, 3))
    # Transform to center-of-mass coordinates.
    r -= np.sum(m[:, None] * r, axis=0) / m.sum()
    v -= np.sum(m[:, None] * v, axis=0) / m.sum()
    G = 1.0

    d = pair_diagnostics(m, r, v, G)
    kinetic = 0.5 * np.sum(m[:, None] * v * v)
    potential = sum(
        -G * m[i] * m[j] / np.linalg.norm(r[j] - r[i])
        for i, j in [(0, 1), (0, 2), (1, 2)]
    )
    angular = np.sum(m[:, None] * np.cross(r, v), axis=0)

    np.testing.assert_allclose(d["E"].sum(), kinetic + potential, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(d["L"].sum(axis=0), angular, rtol=1e-12, atol=1e-12)
