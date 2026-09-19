import numpy as np

from hierarchical_triple_ejection.features import FEATURE_NAMES, extract_window_features


def synthetic_record(n=41, future_scale=1.0):
    t = np.linspace(0.0, 10.0, n)
    # Smooth, non-degenerate channels with valid feature shapes.
    H = 3.0 + 0.3 * np.sin(t) * future_scale
    E = np.column_stack([
        -1.0 + 0.02 * np.sin(t),
        -0.4 + 0.03 * np.cos(0.7 * t),
        -0.2 + 0.01 * np.sin(1.3 * t),
    ])
    L = np.zeros((n, 3, 3))
    for k in range(3):
        L[:, k, k] = 1.0 + 0.1 * (k + 1) * np.sin((k + 1) * t / 4)
    omega = 0.2 + 0.05 * np.cos(t)
    eout = -0.5 + 0.02 * np.sin(0.4 * t)
    distances = np.column_stack([
        1.0 + 0.1 * np.sin(t),
        4.0 + 0.2 * np.cos(t),
        4.5 + 0.2 * np.sin(0.8 * t),
    ])
    return {
        "t": t,
        "H": H,
        "E_pair": E,
        "L_pair": L,
        "Omega": omega,
        "E_out": eout,
        "d_pair": distances,
    }


def test_feature_schema_and_deprecated_slot():
    rec = synthetic_record()
    x = extract_window_features(rec, t_horizon=5.0)
    assert len(FEATURE_NAMES) == 79
    assert x.shape == (79,)
    assert FEATURE_NAMES[73] == "n_frac"
    assert x[73] == 0.0


def test_future_extension_cannot_change_horizon_features():
    base = synthetic_record(n=41)
    horizon = 5.0

    # Extend the record after the horizon with deliberately extreme values.
    extended = {}
    extra_t = np.linspace(10.25, 20.0, 40)
    extended["t"] = np.concatenate([base["t"], extra_t])
    for key in ["H", "Omega", "E_out"]:
        tail_shape = (len(extra_t),)
        extended[key] = np.concatenate([base[key], np.full(tail_shape, 1e6)])
    for key in ["E_pair", "L_pair", "d_pair"]:
        tail_shape = (len(extra_t),) + base[key].shape[1:]
        extended[key] = np.concatenate([base[key], np.full(tail_shape, 1e6)], axis=0)

    x_base = extract_window_features(base, t_horizon=horizon)
    x_extended = extract_window_features(extended, t_horizon=horizon)
    np.testing.assert_allclose(x_base, x_extended, rtol=0.0, atol=0.0)


def test_first_breach_is_normalized_by_window_not_full_record():
    base = synthetic_record(n=41)
    base["H"][3:8] = 2.0
    horizon = 5.0

    extended = {k: np.copy(v) for k, v in base.items()}
    extra_t = np.linspace(10.25, 20.0, 40)
    extended["t"] = np.concatenate([base["t"], extra_t])
    for key in ["H", "Omega", "E_out"]:
        extended[key] = np.concatenate([base[key], np.zeros(len(extra_t))])
    for key in ["E_pair", "L_pair", "d_pair"]:
        tail_shape = (len(extra_t),) + base[key].shape[1:]
        extended[key] = np.concatenate([base[key], np.zeros(tail_shape)], axis=0)

    x1 = extract_window_features(base, t_horizon=horizon)
    x2 = extract_window_features(extended, t_horizon=horizon)
    assert x1[72] == x2[72]
