"""Core v2 triple simulation: corrected physics, causal-safe storage.

Changes vs. the MNRAS-manuscript pipeline:
  * pairwise energies AND angular momenta use the total-mass normalization
        E_ij = 0.5 (m_i m_j / M) |dv|^2 - G m_i m_j / r
        L_ij = (m_i m_j / M) (r x v)
    so that sum_ij E_ij = E_total and sum_ij L_ij = J_total EXACTLY (all masses).
    (Pair-reduced-mass version sums to the conserved quantities only for N=2.)
  * ejection = unbound criterion (positive Jacobi outer energy + outgoing
    + beyond initial outer apoapsis), not a distance threshold.
  * exchange tracking via most-bound pair identity.
  * collisions are their own outcome class.
  * phase-uniform sampling (n_per_orbit samples per outer orbit) so that
    stable and ejected trajectories have the same cadence per orbit.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import numpy as np
import rebound

TWOPI = 2.0 * np.pi


# ---------------------------------------------------------------- config
@dataclass
class TripleConfig:
    n_systems: int = 400
    seed: int = 42

    mass_range: tuple = (0.5, 2.0)
    a_in_range: tuple = (0.8, 1.2)
    a_out_range: tuple = (3.0, 12.0)
    e_in_range: tuple = (0.0, 0.4)
    e_out_range: tuple = (0.0, 0.7)
    inc_range_deg: tuple = (0.0, 60.0)

    t_max_outer_periods: float = 30.0
    n_per_orbit: int = 20            # samples per outer orbit (phase-uniform)
    ejection_apo_factor: float = 1.0  # r > factor * a_out(1+e_out)
    use_physical_radii: bool = True   # collision radii from mass-radius relation
    collision_radius_factor: float = 0.01  # fallback if use_physical_radii=False
    r_coll_floor_au: float = 1e-5
    timeout_s: float = 900.0         # per-system wall-clock hang guard
    max_relative_energy_error: float = 1.0e-8
    H_critical: float = 2.5


SOLAR_RADIUS_AU = 4.65047e-3


def stellar_radius_au(mass_solar: float) -> float:
    """Main-sequence radius in AU from a power-law mass-radius relation."""
    m = float(np.clip(mass_solar, 0.001, 100.0))
    r_solar = m ** 0.8 if m < 0.43 else m ** 0.57
    return r_solar * SOLAR_RADIUS_AU


def collision_thresholds(m, cfg: TripleConfig, a_inner: float) -> np.ndarray:
    """Pairwise collision radii (AU): physical mass-radius, or a_in-fraction."""
    if not cfg.use_physical_radii:
        return np.full(3, cfg.collision_radius_factor * a_inner)
    R = np.array([stellar_radius_au(x) for x in m])
    th = np.array([R[0] + R[1], R[0] + R[2], R[1] + R[2]])
    return np.maximum(th, cfg.r_coll_floor_au)


# ---------------------------------------------------------------- ICs
def sample_triple_ic(system_id: int, cfg: TripleConfig) -> dict:
    ss = np.random.SeedSequence([cfg.seed, int(system_id)])
    rng = np.random.default_rng(ss)
    ic = dict(
        m0=float(rng.uniform(*cfg.mass_range)),
        m1=float(rng.uniform(*cfg.mass_range)),
        m2=float(rng.uniform(*cfg.mass_range)),
        a_inner=float(rng.uniform(*cfg.a_in_range)),
        e_inner=float(rng.uniform(*cfg.e_in_range)),
        inc_inner=0.0,
        Omega_inner=0.0,
        omega_inner=float(rng.uniform(0.0, TWOPI)),
        M_inner=float(rng.uniform(0.0, TWOPI)),
        a_outer=float(rng.uniform(*cfg.a_out_range)),
        e_outer=float(rng.uniform(*cfg.e_out_range)),
        inc_outer=float(np.deg2rad(rng.uniform(*cfg.inc_range_deg))),
        Omega_outer=float(rng.uniform(0.0, TWOPI)),
        omega_outer=float(rng.uniform(0.0, TWOPI)),
        M_outer=float(rng.uniform(0.0, TWOPI)),
    )
    # Mardling-Aarseth 2001 criterion & margin (for benchmarking)
    q_out = ic["m2"] / (ic["m0"] + ic["m1"])
    e_out, i_mut = ic["e_outer"], ic["inc_outer"]
    a_ratio_crit = 2.8 * ((1 + q_out) * (1 + e_out) / np.sqrt(1 - e_out)) ** (2 / 5)
    a_ratio_crit *= (1 - 0.3 * i_mut / np.pi)
    ic["MA01_crit"] = float(a_ratio_crit)
    ic["MA01_margin"] = float(ic["a_outer"] / ic["a_inner"] / a_ratio_crit)
    return ic


def outer_period_years(ic: dict) -> float:
    return float(np.sqrt(ic["a_outer"] ** 3 / (ic["m0"] + ic["m1"] + ic["m2"])))


def make_triple_sim(ic: dict) -> rebound.Simulation:
    sim = rebound.Simulation()
    sim.units = ("yr", "AU", "Msun")
    sim.integrator = "ias15"
    sim.add(m=ic["m0"])
    sim.add(m=ic["m1"], a=ic["a_inner"], e=ic["e_inner"],
            inc=ic["inc_inner"], Omega=ic["Omega_inner"],
            omega=ic["omega_inner"], M=ic["M_inner"],
            primary=sim.particles[0])
    sim.move_to_com()
    inner_com = sim.com(first=0, last=2)  # COM of bodies 0,1
    sim.add(m=ic["m2"], a=ic["a_outer"], e=ic["e_outer"],
            inc=ic["inc_outer"], Omega=ic["Omega_outer"],
            omega=ic["omega_outer"], M=ic["M_outer"],
            primary=inner_com)
    sim.move_to_com()
    return sim


# ---------------------------------------------------------------- diagnostics
def _arrays(sim: rebound.Simulation):
    p = sim.particles
    m = np.array([p[k].m for k in range(3)])
    r = np.array([[p[k].x, p[k].y, p[k].z] for k in range(3)])
    v = np.array([[p[k].vx, p[k].vy, p[k].vz] for k in range(3)])
    return m, r, v


def hierarchy_metric(m, r) -> float:
    r_in = np.linalg.norm(r[1] - r[0])
    if r_in <= 1e-14:
        return 1e30
    com = (m[0] * r[0] + m[1] * r[1]) / (m[0] + m[1])
    return float(np.linalg.norm(r[2] - com) / r_in)


def pair_diagnostics(m, r, v, G) -> dict:
    """Total-mass-normalized pair energies E_ij, angular momenta L_ij,
    Jacobi outer energy E_out, and seam tension Omega_res."""
    M = m.sum()
    E = np.zeros(3); L = np.zeros((3, 3))
    pairs = [(0, 1), (0, 2), (1, 2)]
    for k, (i, j) in enumerate(pairs):
        dr = r[j] - r[i]; dv = v[j] - v[i]
        d = np.linalg.norm(dr)
        E[k] = 0.5 * (m[i] * m[j] / M) * np.dot(dv, dv) - G * m[i] * m[j] / d
        L[k] = (m[i] * m[j] / M) * np.cross(dr, dv)
    # Jacobi outer channel (tertiary wrt inner pair)
    com01 = (m[0] * r[0] + m[1] * r[1]) / (m[0] + m[1])
    vcom01 = (m[0] * v[0] + m[1] * v[1]) / (m[0] + m[1])
    d_out = np.linalg.norm(r[2] - com01)
    mu_out = m[2] * (m[0] + m[1]) / M
    E_out = 0.5 * mu_out * np.dot(v[2] - vcom01, v[2] - vcom01) \
        - G * m[2] * (m[0] + m[1]) / d_out
    # seam tension (same definition as the manuscript)
    Om = 0.0
    for (a, b) in [(0, 1), (1, 2), (2, 0)]:
        Om += np.linalg.norm(L[a] - L[b])
    Om /= (np.linalg.norm(L[0]) + np.linalg.norm(L[1]) + np.linalg.norm(L[2]) + 1e-30)
    return dict(E=E, L=L, E_out=E_out, Omega=Om, d_out=d_out)


def bound_pair_id(E_pair: np.ndarray) -> int:
    """Index of the most bound pair (most negative E_ij): 0:(0,1) 1:(0,2) 2:(1,2)."""
    return int(np.argmin(E_pair))


def escape_energy(m, r, v, k, G) -> tuple:
    """Jacobi energy of body k with respect to the other pair + radial velocity."""
    i, j = [x for x in range(3) if x != k]
    com = (m[i] * r[i] + m[j] * r[j]) / (m[i] + m[j])
    vcom = (m[i] * v[i] + m[j] * v[j]) / (m[i] + m[j])
    dvec = r[k] - com; dv = v[k] - vcom
    d = np.linalg.norm(dvec)
    mu = m[k] * (m[i] + m[j]) / m.sum()
    E = 0.5 * mu * np.dot(dv, dv) - G * m[k] * (m[i] + m[j]) / d
    vrad = float(np.dot(dv, dvec) / d) if d > 1e-14 else 0.0
    return E, vrad, d


# ---------------------------------------------------------------- simulation
def simulate_triple(system_id: int, cfg: TripleConfig, ic_override: dict | None = None) -> dict:
    ic = ic_override if ic_override is not None else sample_triple_ic(system_id, cfg)
    sim = make_triple_sim(ic)
    G = float(sim.G)
    E0 = float(sim.energy())

    Pout = outer_period_years(ic)
    t_max = cfg.t_max_outer_periods * Pout
    n_samples = max(64, int(cfg.t_max_outer_periods * cfg.n_per_orbit))
    sample_times = np.linspace(0.0, t_max, n_samples)

    r_apo_out = ic["a_outer"] * (1 + ic["e_outer"]) * cfg.ejection_apo_factor
    r_coll = collision_thresholds(np.array([ic["m0"], ic["m1"], ic["m2"]]),
                                  cfg, ic["a_inner"])

    t_arr = []; H = []; E_pair = []; L_pair = []; E_out = []; Omega = []
    d_pair = []; vrad_k = np.full((n_samples, 3), 0.0); esc_E = np.full((n_samples, 3), 0.0)

    status = "stable"; t_event = None; escaper = None
    max_rel_err = 0.0
    t_start = time.time()

    for idx, t in enumerate(sample_times):
        sim.integrate(float(t), exact_finish_time=0)
        E = float(sim.energy())
        rel_err = abs((E - E0) / E0) if E0 != 0 else abs(E - E0)
        max_rel_err = max(max_rel_err, rel_err)

        m, r, v = _arrays(sim)
        pd_ = pair_diagnostics(m, r, v, G)

        t_arr.append(float(sim.t)); H.append(hierarchy_metric(m, r))
        E_pair.append(pd_["E"].copy()); L_pair.append(pd_["L"].copy())
        E_out.append(pd_["E_out"]); Omega.append(pd_["Omega"])
        d_pair.append([np.linalg.norm(r[0]-r[1]), np.linalg.norm(r[0]-r[2]),
                       np.linalg.norm(r[1]-r[2])])

        for k in range(3):
            Ek, vr, dk = escape_energy(m, r, v, k, G)
            esc_E[idx, k] = Ek; vrad_k[idx, k] = vr

        # ---- termination checks (energy -> step budget -> collision -> ejection)
        if rel_err > cfg.max_relative_energy_error:
            status = "numerical_error"; t_event = float(sim.t); break
        if time.time() - t_start > cfg.timeout_s:
            status = "timeout"; t_event = float(sim.t); break
        dp = np.array(d_pair[-1])
        if (dp < r_coll).any():
            status = "collision"; t_event = float(sim.t); break
        for k in range(3):
            if esc_E[idx, k] > 0.0 and vrad_k[idx, k] > 0.0 and \
               escape_energy(m, r, v, k, G)[2] > r_apo_out:
                status = "ejected"; escaper = k; t_event = float(sim.t); break
        if status != "stable":
            break

    # ---- final state bookkeeping
    m, r, v = _arrays(sim)
    pd_f = pair_diagnostics(m, r, v, G)
    bound_pair_final = bound_pair_id(pd_f["E"]) if status == "stable" else None
    exchange = (status == "stable") and (bound_pair_final != 0)

    t_arr = np.array(t_arr); H = np.array(H)
    E_pair = np.array(E_pair); L_pair = np.array(L_pair)
    E_out = np.array(E_out); Omega = np.array(Omega)
    d_pair = np.array(d_pair)

    return dict(
        system_id=system_id, status=status, label=int(status == "ejected"),
        escaper=escaper, t_event=t_event, exchange=exchange,
        bound_pair_final=bound_pair_final,
        t=t_arr, H=H, E_pair=E_pair, L_pair=L_pair, E_out=E_out,
        Omega=Omega, d_pair=d_pair, esc_E=esc_E[:len(t_arr)], vrad_k=vrad_k[:len(t_arr)],
        E0=E0, max_rel_err=max_rel_err, ic=ic, t_max=t_max,
    )


def triple_outcome_counts(records: list) -> dict:
    from collections import Counter
    return dict(Counter(r["status"] for r in records))


def save_records(records: list, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = []
    for r in records:
        d = {k: v for k, v in r.items() if k not in ("t", "H", "E_pair", "L_pair",
             "E_out", "Omega", "d_pair", "esc_E", "vrad_k")}
        d["n_samples"] = len(r["t"])
        out.append(d)
    with path.open("w") as f:
        json.dump(out, f, indent=1)


def load_records(path: str | Path) -> list:
    with open(path) as f:
        return json.load(f)
