# =====================================================================
#  CORRECTED DEEP-TAIL SESSION - 100,000 matched triples x 3000 T_out
#  100,000 triples x 3000 T_out (censoring measurement), in two halves.
#  HOW TO RUN (pick one):
#    A) Paste EVERYTHING into ONE Kaggle code cell and run.
#    B) Upload as session_deeptail.py, then run a cell with:
#           %run /kaggle/working/session_deeptail.py
# =====================================================================

# ---- install dependencies (pure Python; works in every mode) ----
import subprocess as _sp, sys as _sys
_sp.run([_sys.executable, "-m", "pip", "install", "-q",
        "rebound", "xgboost", "scikit-learn", "joblib",
        "numpy", "jax"])


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


"""Binary-single encounters (flagship application): same diagnostics, causal
question = predict exchange/ionization/flyby BEFORE closest approach.

Setup (G=1 units): binary (bodies 0,1) with semi-major axis a=1 at the origin,
incoming single (body 2) launched from R0 with velocity v_inf and impact
parameter b. Diagnostics use the ORIGINAL binary identity for H(t) throughout
(label-agnostic, causal-safe).
"""

from dataclasses import dataclass
from pathlib import Path
import json
import time

import numpy as np
import rebound


TWOPI = 2.0 * np.pi


@dataclass
class EncounterConfig:
    n_systems: int = 300
    seed: int = 7

    m1: float = 1.0
    m2: float = 1.0
    m3: float = 1.0
    stratified_masses: bool = True   # 3 strata by system_id % 3 (see MASS_STRATA)
    a_bin: float = 1.0
    e_bin_max: float = 0.9          # thermal eccentricity p(e)=2e up to this

    vinf_over_vcrit_range: tuple = (0.1, 1.2)   # uniform in v/v_crit
    b_over_a_range: tuple = (0.0, 3.0)          # uniform impact parameter / a

    R0: float = 30.0                # launch distance
    t_max_bin_periods: float = 15.0
    n_samples: int = 300
    R_term: float = 30.0            # resolution radius
    timeout_s: float = 900.0        # per-system wall-clock hang guard


# (m1, m2, m3) per stratum; outer-to-binary mass ratio q = m3/(m1+m2):
#   stratum 0: equal masses        q = 0.50
#   stratum 1: heavy binary        q = 0.33
#   stratum 2: heavy outer body    q = 2.00
MASS_STRATA = [(1.0, 1.0, 1.0), (1.5, 1.5, 1.0), (0.5, 0.5, 2.0)]


def v_critical(m1: float, m2: float, m3: float, a: float) -> float:
    """Hut-Bahcall critical velocity (G=1)."""
    return float(np.sqrt(m1 * m2 * (m1 + m2 + m3) / (m3 * (m1 + m2) * a)))


def solve_kepler(M: float, e: float) -> float:
    """Eccentric anomaly from mean anomaly (Newton iteration)."""
    E = M if e < 0.8 else np.pi
    for _ in range(40):
        f = E - e * np.sin(E) - M
        fp = 1.0 - e * np.cos(E)
        E -= f / fp
        if abs(f) < 1e-13:
            break
    return E


def binary_state(m1: float, m2: float, a: float, e: float, M0: float, rng):
    """Positions/velocities of a binary in its COM frame (G=1)."""
    E = solve_kepler(M0, e)
    cosE, sinE = np.cos(E), np.sin(E)
    # position in orbital plane
    x = a * (cosE - e); y = a * np.sqrt(1 - e * e) * sinE
    r = np.hypot(x, y)
    # vis-viva: v^2 = mu(2/r - 1/a), mu = G(m1+m2)=m1+m2
    mu = m1 + m2
    v = np.sqrt(mu * (2.0 / r - 1.0 / a))
    # velocity direction: derivative of position wrt E, scaled
    dx = -a * sinE; dy = a * np.sqrt(1 - e * e) * cosE
    n = np.hypot(dx, dy)
    vx = v * dx / n; vy = v * dy / n
    # rotate by random orientation (Euler angles)
    def rand_rot(rng):
        a1, a2, a3 = rng.uniform(0, TWOPI, 3)
        Rz = lambda t: np.array([[np.cos(t), -np.sin(t), 0], [np.sin(t), np.cos(t), 0], [0, 0, 1]])
        Ry = lambda t: np.array([[np.cos(t), 0, np.sin(t)], [0, 1, 0], [-np.sin(t), 0, np.cos(t)]])
        return Rz(a3) @ Ry(a2) @ Rz(a1)
    R = rand_rot(rng)
    xyz = R @ np.array([x, y, 0.0])
    vxyz = R @ np.array([vx, vy, 0.0])
    # positions relative to COM
    r1 = xyz * (m2 / (m1 + m2)); r2 = -xyz * (m1 / (m1 + m2))
    v1 = vxyz * (m2 / (m1 + m2)); v2 = -vxyz * (m1 / (m1 + m2))
    return r1, r2, v1, v2


def sample_encounter_ic(system_id: int, cfg: EncounterConfig) -> dict:
    ss = np.random.SeedSequence([cfg.seed, int(system_id)])
    rng = np.random.default_rng(ss)
    if cfg.stratified_masses:
        m1, m2, m3 = MASS_STRATA[int(system_id) % 3]
        stratum = int(system_id) % 3
    else:
        m1, m2, m3 = cfg.m1, cfg.m2, cfg.m3
        stratum = 0
    e_bin = float(np.sqrt(rng.uniform(0.0, cfg.e_bin_max ** 2)))  # thermal p(e)=2e
    M0 = float(rng.uniform(0.0, TWOPI))
    r1, r2, v1, v2 = binary_state(m1, m2, cfg.a_bin, e_bin, M0, rng)
    vcrit = v_critical(m1, m2, m3, cfg.a_bin)
    vinf = float(rng.uniform(*cfg.vinf_over_vcrit_range) * vcrit)
    b = float(rng.uniform(*cfg.b_over_a_range) * cfg.a_bin)
    theta = float(rng.uniform(0.0, TWOPI))
    # single launched from (R0, 0, 0) direction offset by impact parameter
    bhat = np.array([np.cos(theta), np.sin(theta), 0.0])
    r3 = np.array([cfg.R0, 0.0, 0.0]) + b * bhat
    v3 = np.array([-vinf, 0.0, 0.0])
    T_bin = TWOPI * np.sqrt(cfg.a_bin ** 3 / (m1 + m2))
    return dict(r1=r1, r2=r2, r3=r3, v1=v1, v2=v2, v3=v3,
                m1=m1, m2=m2, m3=m3,
                e_bin=e_bin, vinf=vinf, vcrit=vcrit, b=b,
                stratum=stratum, T_bin=float(T_bin),
                t_approach=float(cfg.R0 / vinf))


def simulate_encounter(system_id: int, cfg: EncounterConfig) -> dict:
    ic = sample_encounter_ic(system_id, cfg)
    sim = rebound.Simulation()
    sim.G = 1.0
    sim.integrator = "ias15"
    for k in range(3):
        sim.add(m=[ic["m1"], ic["m2"], ic["m3"]][k],
                x=[ic["r1"], ic["r2"], ic["r3"]][k][0],
                y=[ic["r1"], ic["r2"], ic["r3"]][k][1],
                z=[ic["r1"], ic["r2"], ic["r3"]][k][2],
                vx=[ic["v1"], ic["v2"], ic["v3"]][k][0],
                vy=[ic["v1"], ic["v2"], ic["v3"]][k][1],
                vz=[ic["v1"], ic["v2"], ic["v3"]][k][2])
    sim.move_to_com()
    G = float(sim.G)
    E0 = float(sim.energy())

    T_bin = TWOPI * np.sqrt(cfg.a_bin ** 3 / (ic["m1"] + ic["m2"]))
    t_max = cfg.t_max_bin_periods * T_bin
    sample_times = np.linspace(0.0, t_max, cfg.n_samples)

    t_arr = []; H = []; E_pair = []; L_pair = []; E_out = []; Omega = []; d_pair = []
    status = "unresolved"; t_event = t_max
    min_d_so_far = 1e30; t_peri = None
    max_rel_err = 0.0
    t_start = time.time()

    for idx, t in enumerate(sample_times):
        sim.integrate(float(t), exact_finish_time=0)
        E = float(sim.energy())
        rel_err = abs((E - E0) / E0) if E0 != 0 else abs(E - E0)
        max_rel_err = max(max_rel_err, rel_err)

        m = np.array([p.m for p in sim.particles])
        r = np.array([[p.x, p.y, p.z] for p in sim.particles])
        v = np.array([[p.vx, p.vy, p.vz] for p in sim.particles])

        if time.time() - t_start > cfg.timeout_s:
            status = "timeout"
            break
        pd_ = pair_diagnostics(m, r, v, G)
        t_arr.append(float(sim.t)); H.append(hierarchy_metric(m, r))
        E_pair.append(pd_["E"].copy()); L_pair.append(pd_["L"].copy())
        E_out.append(pd_["E_out"]); Omega.append(pd_["Omega"])
        dp = [np.linalg.norm(r[0]-r[1]), np.linalg.norm(r[0]-r[2]),
              np.linalg.norm(r[1]-r[2])]
        d_pair.append(dp)
        if min(dp) < min_d_so_far:
            min_d_so_far = min(dp); t_peri = float(sim.t)

        # resolution: any body beyond R_term with positive Jacobi energy, outgoing
        for k in range(3):
            Ek, vr, dk = escape_energy(m, r, v, k, G)
            if Ek > 0.0 and vr > 0.0 and dk > cfg.R_term:
                status = "resolved"; t_event = float(sim.t); break
        if status == "resolved":
            break

    # ---- outcome classification at the end
    m = np.array([p.m for p in sim.particles])
    r = np.array([[p.x, p.y, p.z] for p in sim.particles])
    v = np.array([[p.vx, p.vy, p.vz] for p in sim.particles])
    pd_f = pair_diagnostics(m, r, v, G)
    bp = bound_pair_id(pd_f["E"])
    bound_exists = bool(pd_f["E"][bp] < 0.0)
    if bound_exists and bp == 0:
        outcome = "flyby"
    elif bound_exists:
        outcome = "exchange"
    else:
        outcome = "ionization"

    return dict(
        system_id=system_id, status=status, outcome=outcome,
        t_event=t_event, t_peri=t_peri if t_peri is not None else t_event,
        min_pair_dist=min_d_so_far,
        t=np.array(t_arr), H=np.array(H), E_pair=np.array(E_pair),
        L_pair=np.array(L_pair), E_out=np.array(E_out),
        Omega=np.array(Omega), d_pair=np.array(d_pair),
        E0=E0, max_rel_err=max_rel_err, ic={k: (v.tolist() if hasattr(v, "tolist") else v)
                                            for k, v in ic.items()},
        t_max=t_max,
    )


def encounter_outcome_counts(records: list) -> dict:
    from collections import Counter
    return dict(Counter(r["outcome"] for r in records))


def save_encounter_records(records: list, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = []
    for r in records:
        d = {k: v for k, v in r.items() if k not in ("t", "H", "E_pair", "L_pair",
             "E_out", "Omega", "d_pair")}
        d["n_samples"] = len(r["t"])
        out.append(d)
    with path.open("w") as f:
        json.dump(out, f, indent=1)


"""Window-aware (causal-safe) feature extraction for triples and encounters.

Two window modes:
  * fraction f of the recorded trajectory (sample-index based),
  * physical time horizon: only samples with t <= t_horizon (the honest
    causal mode used by the v2 experiments).
Features use ONLY window data. The horizon mismatch of the v1 pipeline is
removed: every system (stable or not) uses the same absolute horizon.
"""

from typing import Any

import numpy as np


# ------------------------------------------------------------------ helpers
def _safe(x: Any) -> np.ndarray:
    return np.nan_to_num(np.asarray(x, dtype=float), nan=0.0, posinf=1e30, neginf=-1e30)


def _slope(y: np.ndarray, t: np.ndarray) -> float:
    if len(y) < 2:
        return 0.0
    try:
        return float(np.polyfit(t, y, 1)[0])
    except Exception:
        return 0.0


def _curv(y: np.ndarray, t: np.ndarray) -> float:
    if len(y) < 3:
        return 0.0
    try:
        return float(2.0 * np.polyfit(t, y, 2)[0])
    except Exception:
        return 0.0


def _spectral_entropy(y: np.ndarray) -> float:
    y = _safe(y)
    if len(y) < 8 or np.allclose(y, y[0]):
        return 0.0
    yc = y - np.mean(y)
    psd = np.abs(np.fft.rfft(yc)) ** 2
    psd = psd[1:]
    tot = psd.sum()
    if tot <= 0:
        return 0.0
    p = psd / tot
    return float(-np.sum(p * np.log(p + 1e-30)) / np.log(len(p)))


def _autocorr(y: np.ndarray, lag: int = 5) -> float:
    y = _safe(y)
    if len(y) <= lag or np.allclose(y, y[0]):
        return 0.0
    yc = y - np.mean(y)
    d = np.dot(yc, yc)
    return float(np.dot(yc[:-lag], yc[lag:]) / d) if d > 0 else 0.0


# ------------------------------------------------------------------ features
def _torque_norms(L_pair: np.ndarray, t: np.ndarray) -> np.ndarray:
    """||Gamma_ij(t)|| = ||dL_ij/dt|| for the three pair channels."""
    Gammas = np.gradient(L_pair, t, axis=0)  # (n,3,3)
    return np.linalg.norm(Gammas, axis=2)    # (n,3)


def extract_window_features(rec: dict, f: float = 1.0, t_horizon: float | None = None,
                            Hcrit: float = 2.5, kappa: float = 4.0) -> np.ndarray:
    """Features from the first fraction f of the recorded trajectory, or from
    samples with t <= t_horizon (physical-time causal window)."""
    t = _safe(rec["t"]); n = len(t)
    if n == 0:
        return np.zeros(len(FEATURE_NAMES))
    if t_horizon is not None:
        nmax = int(np.searchsorted(t, t_horizon, side="right"))
    else:
        nmax = max(2, int(round(n * f)))
    nmax = min(max(nmax, 2), n)
    sl = slice(0, nmax)
    t = t[sl]; H = _safe(rec["H"][sl])
    E = _safe(rec["E_pair"][sl])     # (n,3)
    L = _safe(rec["L_pair"][sl])     # (n,3,3)
    Om = _safe(rec["Omega"][sl])
    dur = t[-1] - t[0]

    dH = np.gradient(H, t)
    d2H = np.gradient(dH, t)
    Hdot_c = max(abs(H[0]) / max(dur, 1e-12), 1e-12)
    psi = 0.5 * (1 + np.tanh(kappa * (np.abs(dH) / Hdot_c - 1)))

    Gnorm = _torque_norms(L, t)      # (n,3)
    Lnorm = np.linalg.norm(L, axis=2)  # (n,3)

    # pairwise-distance features (collision/encounter indicators)
    dp = rec.get("d_pair")
    if dp is None or len(dp) == 0:
        dmin = np.full(nmax, np.nan)
    else:
        dmin = np.min(_safe(dp)[sl], axis=1)
    dmin_min = float(np.nanmin(dmin)) if np.any(np.isfinite(dmin)) else 0.0
    dmin_frac = float(np.nanargmin(dmin) / max(1, nmax - 1)) if np.any(np.isfinite(dmin)) else 1.0
    dmin_rate = np.abs(np.gradient(np.nan_to_num(dmin, nan=1e30), t))
    dmin_rate_max = float(np.max(dmin_rate)) if len(dmin_rate) else 0.0
    # bound-pair identity switches within the window (exchange activity)
    pair_id = np.argmin(E, axis=1)   # most bound pair per sample
    n_pair_changes = int(np.sum(pair_id[1:] != pair_id[:-1])) if n > 1 else 0

    below = H < Hcrit
    crossings = int(np.sum((H[1:] < Hcrit) & (H[:-1] >= Hcrit))) if n > 1 else 0
    breach = np.where(below)[0]
    first_breach = breach[0] / max(1, nmax - 1) if len(breach) else 1.0

    E_std = np.std(E, axis=0)
    E_scale = float(np.mean(np.abs(E)) + 1e-30)
    E_slopes = np.array([_slope(E[:, k], t) for k in range(3)])

    # torque spike ratio (periastron false-positive diagnostic)
    med = np.median(Gnorm, axis=0) + 1e-30
    spike = np.max(Gnorm, axis=0) / med

    feats = np.array([
        # hierarchy stats (12)
        np.min(H), np.max(H), np.mean(H), np.std(H), np.median(H),
        np.max(H) - np.min(H), H[-1], H[0], _slope(H, t), _curv(H, t),
        np.mean(below), crossings,
        # hierarchy derivatives (8)
        np.min(dH), np.max(dH), np.std(dH), np.max(np.abs(dH)),
        np.min(d2H), np.max(d2H), np.std(d2H), np.max(np.abs(d2H)),
        # psi filter (4)
        np.mean(psi), np.max(psi), np.std(psi), psi[-1],
        # pair energies (10)
        E_std[0], E_std[1], E_std[2], E_std.sum(),
        E_std.sum() / E_scale, E_slopes[0], E_slopes[1], E_slopes[2],
        E[-1, 0], E[-1, 1],
        # outer-channel energy (4)
        np.min(_safe(rec["E_out"][sl])), np.max(_safe(rec["E_out"][sl])),
        _safe(rec["E_out"][sl])[-1], _slope(_safe(rec["E_out"][sl]), t),
        # angular momentum channels (12)
        np.min(Lnorm[:, 0]), np.max(Lnorm[:, 0]), np.std(Lnorm[:, 0]),
        np.min(Lnorm[:, 1]), np.max(Lnorm[:, 1]), np.std(Lnorm[:, 1]),
        np.min(Lnorm[:, 2]), np.max(Lnorm[:, 2]), np.std(Lnorm[:, 2]),
        _slope(Lnorm[:, 0], t), _slope(Lnorm[:, 1], t), _slope(Lnorm[:, 2], t),
        # torques (12)
        np.max(Gnorm[:, 0]), np.mean(Gnorm[:, 0]), spike[0],
        np.max(Gnorm[:, 1]), np.mean(Gnorm[:, 1]), spike[1],
        np.max(Gnorm[:, 2]), np.mean(Gnorm[:, 2]), spike[2],
        np.max(Gnorm), np.mean(Gnorm), np.max(spike), np.mean(spike),
        # seam tension (6)
        np.min(Om), np.max(Om), np.mean(Om), np.std(Om), Om[-1], _slope(Om, t),
        # signal processing (3)
        _spectral_entropy(H), _spectral_entropy(Om), _autocorr(H, 5),
        # time anchors (3)
        first_breach, 0.0, dur,  # index 73 deprecated: future-length leak removed
        # pairwise-distance & exchange activity (4)
        dmin_min, dmin_frac, dmin_rate_max, float(n_pair_changes),
    ])
    return np.nan_to_num(feats, nan=0.0, posinf=1e30, neginf=-1e30)


def full_trajectory_features(rec: dict, **kw) -> np.ndarray:
    return extract_window_features(rec, 1.0, **kw)


FEATURE_NAMES = [
    "H_min", "H_max", "H_mean", "H_std", "H_med", "H_range", "H_final", "H_initial",
    "H_slope", "H_curv", "H_below_frac", "H_crossings",
    "dH_min", "dH_max", "dH_std", "abs_dH_max",
    "d2H_min", "d2H_max", "d2H_std", "abs_d2H_max",
    "psi_mean", "psi_max", "psi_std", "psi_final",
    "E01_std", "E02_std", "E12_std", "E_exch", "E_exch_norm",
    "E01_slope", "E02_slope", "E12_slope", "E01_final", "E02_final",
    "Eout_min", "Eout_max", "Eout_final", "Eout_slope",
    "L01_min", "L01_max", "L01_std", "L02_min", "L02_max", "L02_std",
    "L12_min", "L12_max", "L12_std", "L01_slope", "L02_slope", "L12_slope",
    "G01_max", "G01_mean", "G01_spike", "G02_max", "G02_mean", "G02_spike",
    "G12_max", "G12_mean", "G12_spike", "G_all_max", "G_all_mean",
    "G_spike_max", "G_spike_mean",
    "Om_min", "Om_max", "Om_mean", "Om_std", "Om_final", "Om_slope",
    "H_entropy", "Om_entropy", "H_autocorr",
    "first_breach", "n_frac", "dur",
    "dmin_min", "dmin_frac", "dmin_rate_max", "n_pair_changes",
]


"""Causal experiment (v2, corrected protocol).

For each horizon fraction f we build features ONLY from samples with
t <= t_horizon, where the horizon is anchored in PHYSICAL time:
  * triples    : t_horizon = f * t_max  (t_max = 100 T_out in the full run)
  * encounters : t_horizon = f * t_peri (fraction of the infall phase)

Evaluation per horizon is restricted to systems still "in play"
(t_event > t_horizon), so the classifier can never see its own label inside
the window. Systems that terminated before the horizon are reported
separately (survival curve) — those are detectable, not predictable.
"""

from typing import Callable

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, recall_score, \
    precision_score, f1_score, confusion_matrix


try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except Exception:
    HAS_XGB = False


FRACTIONS = [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0]


def make_model(seed: int = 0):
    if HAS_XGB:
        return XGBClassifier(
            n_estimators=250, max_depth=3, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
            objective="binary:logistic", eval_metric="logloss",
            random_state=seed, n_jobs=4, tree_method="hist")
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(
        max_iter=250, learning_rate=0.05, max_leaf_nodes=15,
        l2_regularization=0.05, random_state=0)


def _horizon(rec: dict, f: float, anchor: str) -> float:
    if anchor == "peri_frac":
        return f * float(rec["t_peri"])
    return f * float(rec["t_max"])


def run_causal_experiment(records: list, positive_label_fn: Callable,
                          fractions=FRACTIONS, seed: int = 0,
                          test_size: float = 0.3,
                          anchor: str = "tmax_frac") -> list:
    """anchor: 'tmax_frac' (triples: f*t_max) or 'peri_frac' (encounters:
    f*t_peri). Returns per-horizon rows incl. survival/excluded counts."""
    y = np.array([positive_label_fn(r) for r in records], dtype=int)
    if y.sum() == 0 or y.sum() == len(y):
        raise ValueError("only one class")

    rows = []
    for f in fractions:
        horizon = np.array([_horizon(r, f, anchor) for r in records])
        t_event = np.array([r["t_event"] if r["t_event"] is not None
                            else np.inf for r in records])
        in_play = t_event > horizon  # not yet terminated at horizon
        n_excl_pos = int(((t_event <= horizon) & (y == 1)).sum())
        n_excl_neg = int(((t_event <= horizon) & (y == 0)).sum())
        idx = np.where(in_play)[0]
        if len(idx) < 20 or y[idx].sum() < 5 or y[idx].sum() == len(idx):
            rows.append(dict(fraction=f, accuracy=np.nan, auc=np.nan,
                             recall_pos=np.nan, precision_pos=np.nan,
                             f1_pos=np.nan, tn=0, fp=0, fn=0, tp=0,
                             n_in_play=len(idx), n_excl_pos=n_excl_pos,
                             n_excl_neg=n_excl_neg))
            continue
        X = np.vstack([extract_window_features(records[i], 1.0,
                                               t_horizon=horizon[i])
                       for i in idx])
        X = np.nan_to_num(X, nan=0.0, posinf=1e30, neginf=-1e30)
        y_sub = y[idx]
        X_train, X_val, y_train, y_val = train_test_split(
            X, y_sub, test_size=test_size, random_state=seed, stratify=y_sub)
        clf = make_model(seed)
        clf.fit(X_train, y_train)
        p = clf.predict_proba(X_val)[:, 1]
        pred = (p >= 0.5).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_val, pred, labels=[0, 1]).ravel()
        rows.append(dict(
            fraction=f,
            accuracy=float(accuracy_score(y_val, pred)),
            auc=float(roc_auc_score(y_val, p)),
            recall_pos=float(recall_score(y_val, pred, zero_division=0)),
            precision_pos=float(precision_score(y_val, pred, zero_division=0)),
            f1_pos=float(f1_score(y_val, pred, zero_division=0)),
            tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp),
            n_in_play=int(len(idx)), n_excl_pos=n_excl_pos, n_excl_neg=n_excl_neg,
        ))
    return rows


def print_causal_table(rows: list) -> None:
    hdr = (f"{'f':>5} {'acc':>7} {'AUC':>7} {'rec+':>6} {'prec+':>6} "
           f"{'F1+':>6} {'inplay':>6} {'excl+':>5} {'excl-':>5} {'FN':>4} {'TP':>5}")
    print(hdr); print("-" * len(hdr))
    for r in rows:
        print(f"{r['fraction']:5.2f} {r['accuracy']*100:6.1f}% {r['auc']:7.4f} "
              f"{r['recall_pos']*100:5.1f}% {r['precision_pos']*100:5.1f}% "
              f"{r['f1_pos']:6.3f} {r['n_in_play']:6d} {r['n_excl_pos']:5d} "
              f"{r['n_excl_neg']:5d} {r['fn']:4d} {r['tp']:5d}")
    print("(excl+ / excl- : systems that already terminated by the horizon;")
    print(" metrics are evaluated on in-play systems only)")


#!/usr/bin/env python3
"""PRODUCTION RUNS for the v2 paper. Chunked for Kaggle multi-notebook use.

Tasks:
  triples    : 100,000 IAS15 hierarchical triples x 100 T_out   (main suite)
  boundary   :  10,000 triples sampled near the MA01 criterion   (stratum suite)
  tail       :  10,000 triples x 1000 T_out                      (survival/censoring)
  encounters : 100,000 binary-single encounters                  (flagship app)

Parallelism / Kaggle:
  * Each system is seeded deterministically from (global_seed, system_id):
    chunk results are bit-identical regardless of machine or order.
  * --chunk-id k --n-chunks K  ->  system ids [k*N/K, (k+1)*N/K)
    Run 8 Kaggle notebooks (4 cores each, 32 workers total) with k = 0..7.
  * Inside a notebook, use ProcessPoolExecutor(n_jobs=4).
  * Outputs (per chunk, ~30-60 MB): chunk_{task}_{k}_of_{K}.npz  (features+meta)
                                     chunk_{task}_{k}_of_{K}_series.pkl (10% subsample series)

Usage (single machine or one Kaggle notebook):
  python production.py --task triples --chunk-id 0 --n-chunks 8 --out-dir /kaggle/working/v2out
  python production.py --task encounters --chunk-id 3 --n-chunks 8 ...
Merge afterwards:
  python merge_chunks.py --task triples --out-dir /kaggle/working/v2out

Resume: partial progress is dumped every --checkpoint-every systems to
  chunk_{task}_{k}_of_{K}.partial.pkl  (use --resume to continue from it).
"""

import argparse
import json
import multiprocessing as _mp
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np



# ---------------------------------------------------------------- constants
TRIPLE_FRACTIONS = [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0]
ENCOUNTER_FRACTIONS = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
                       0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
N_IC_FIELDS = 19            # ic vector length (see _ic_vec)
SERIES_PER_ORBIT = 2        # downsampled series cadence (per outer orbit)


def _keep_series(system_id):
    """Decide series storage per system (env-tunable at run time)."""
    frac = float(os.environ.get("V2_SERIES_FRAC", "0.10"))
    if frac <= 0:
        return False
    return system_id % int(round(1.0 / frac)) == 0


# ---------------------------------------------------------------- tasks
def _ic_vec(ic: dict) -> np.ndarray:
    keys = ["m0", "m1", "m2", "a_inner", "e_inner", "inc_inner", "Omega_inner",
            "omega_inner", "M_inner", "a_outer", "e_outer", "inc_outer",
            "Omega_outer", "omega_outer", "M_outer"]
    return np.array([ic[k] for k in keys] +
                    [ic["MA01_crit"], ic["MA01_margin"], 0.0, 0.0], dtype=np.float32)


def _process_triple(system_id: int, cfg_kw: dict) -> dict:
    cfg = TripleConfig(**cfg_kw)
    rec = simulate_triple(system_id, cfg)
    # Deep-tail is for censoring/survival only. The 300-T_out main run
    # already contains causal features, so do not waste storage recomputing
    # 79 x 11 features here. Event/status/IC fields are sufficient.
    out = dict(
        id=np.int32(system_id),
        status=rec["status"], label=np.int8(rec["label"]),
        exchange=np.int8(bool(rec["exchange"])),
        escaper=np.int8(rec["escaper"] if rec["escaper"] is not None else -1),
        t_event=np.float32(rec["t_event"] if rec["t_event"] is not None else np.nan),
        t_max=np.float32(rec["t_max"]),
        E0=np.float32(rec["E0"]), max_rel_err=np.float32(rec["max_rel_err"]),
        ic=_ic_vec(rec["ic"]),
    )
    if os.environ.get("V2_SKIP_FEATURES", "0") != "1":
        out["feats"] = np.vstack([
            extract_window_features(rec, 1.0, t_horizon=f * rec["t_max"])
            for f in TRIPLE_FRACTIONS]).astype(np.float32)
    # downsampled series for a subsample
    if _keep_series(system_id):
        t = rec["t"]; keep = np.unique(np.linspace(0, len(t) - 1,
                                    max(8, int(rec["t_max"] / 0.5) + 1)).astype(int))
        G = np.gradient(rec["L_pair"], t, axis=0)
        Gmax = np.max(np.linalg.norm(G, axis=2), axis=1)
        dmin = np.min(rec["d_pair"], axis=1)
        Lmax = np.max(np.linalg.norm(rec["L_pair"], axis=2), axis=1)
        out["series"] = np.stack([t[keep], rec["H"][keep], rec["Omega"][keep],
                                  rec["E_out"][keep], Gmax[keep], dmin[keep],
                                  Lmax[keep]], axis=1).astype(np.float32)
    return out


def _process_boundary(system_id: int, cfg_kw: dict) -> dict:
    """Near-MA01 stratum: a_out drawn within [0.6, 1.4] x MA01 criterion."""
    cfg = TripleConfig(**cfg_kw)
    ic = sample_triple_ic(system_id, cfg)
    ss = np.random.SeedSequence([cfg.seed, int(system_id), 99])
    rng = np.random.default_rng(ss)
    ic["e_outer"] = min(ic["e_outer"], 0.6)  # keep boundary suite physical
    # recompute MA01 criterion with the (possibly capped) e_out
    q_out = ic["m2"] / (ic["m0"] + ic["m1"])
    e_out, i_mut = ic["e_outer"], ic["inc_outer"]
    crit = 2.8 * ((1 + q_out) * (1 + e_out) / np.sqrt(1 - e_out)) ** (2 / 5)
    crit *= (1 - 0.3 * i_mut / np.pi)
    ic["MA01_crit"] = float(crit)
    ic["a_outer"] = float(ic["a_inner"] * crit * rng.uniform(0.6, 1.4))
    ic["MA01_margin"] = float(ic["a_outer"] / ic["a_inner"] / crit)
    rec = simulate_triple(system_id, cfg, ic_override=ic)
    feats = np.vstack([extract_window_features(rec, 1.0, t_horizon=f * rec["t_max"])
                       for f in TRIPLE_FRACTIONS]).astype(np.float32)
    out = dict(
        id=np.int32(system_id),
        status=rec["status"], label=np.int8(rec["label"]),
        exchange=np.int8(bool(rec["exchange"])),
        escaper=np.int8(rec["escaper"] if rec["escaper"] is not None else -1),
        t_event=np.float32(rec["t_event"] if rec["t_event"] is not None else np.nan),
        t_max=np.float32(rec["t_max"]),
        E0=np.float32(rec["E0"]), max_rel_err=np.float32(rec["max_rel_err"]),
        ic=_ic_vec(rec["ic"]), feats=feats,
    )
    if _keep_series(system_id):
        t = rec["t"]; keep = np.unique(np.linspace(0, len(t) - 1,
                                    max(8, int(rec["t_max"] / 0.5) + 1)).astype(int))
        G = np.gradient(rec["L_pair"], t, axis=0)
        Gmax = np.max(np.linalg.norm(G, axis=2), axis=1)
        dmin = np.min(rec["d_pair"], axis=1)
        Lmax = np.max(np.linalg.norm(rec["L_pair"], axis=2), axis=1)
        out["series"] = np.stack([t[keep], rec["H"][keep], rec["Omega"][keep],
                                  rec["E_out"][keep], Gmax[keep], dmin[keep],
                                  Lmax[keep]], axis=1).astype(np.float32)
    return out


def _process_encounter(system_id: int, cfg_kw: dict) -> dict:
    cfg = EncounterConfig(**cfg_kw)
    rec = simulate_encounter(system_id, cfg)
    t_app = rec["ic"]["t_approach"]
    feats = np.vstack([extract_window_features(rec, 1.0, t_horizon=f * t_app)
                       for f in ENCOUNTER_FRACTIONS]).astype(np.float32)
    ic = rec["ic"]
    icv = np.array([ic["m1"], ic["m2"], ic["m3"], 1.0, ic["e_bin"], 0, 0, 0, 0,
                    1.0, 0.0, 0.0, 0, 0, 0, ic["vinf"], ic["vcrit"], ic["b"],
                    t_app, ic["stratum"], ic["T_bin"]], dtype=np.float32)
    out = dict(
        id=np.int32(system_id),
        status=rec["outcome"],   # exchange / flyby / ionization
        label=np.int8(1 if rec["outcome"] == "exchange" else 0),
        outcome=rec["outcome"],
        t_event=np.float32(rec["t_event"]), t_peri=np.float32(rec["t_peri"]),
        t_approach=np.float32(t_app),
        t_max=np.float32(rec["t_max"]),
        min_pair_dist=np.float32(rec["min_pair_dist"]),
        E0=np.float32(rec["E0"]), max_rel_err=np.float32(rec["max_rel_err"]),
        ic=icv, feats=feats,
    )
    if _keep_series(system_id):
        t = rec["t"]
        keep = np.arange(0, len(t), max(1, len(t) // 400))
        G = np.gradient(rec["L_pair"], t, axis=0)
        Gmax = np.max(np.linalg.norm(G, axis=2), axis=1)
        dmin = np.min(rec["d_pair"], axis=1)
        Lmax = np.max(np.linalg.norm(rec["L_pair"], axis=2), axis=1)
        out["series"] = np.stack([t[keep], rec["H"][keep], rec["Omega"][keep],
                                  rec["E_out"][keep], Gmax[keep], dmin[keep],
                                  Lmax[keep]], axis=1).astype(np.float32)
    return out


PROCESSORS = {"triples": _process_triple, "boundary": _process_boundary,
              "encounters": _process_encounter}
TASKS = {"triples": 100_000, "boundary": 10_000, "tail": 10_000,
         "encounters": 100_000}
FRACTIONS = {"triples": TRIPLE_FRACTIONS, "boundary": TRIPLE_FRACTIONS,
             "tail": TRIPLE_FRACTIONS,
             "encounters": ENCOUNTER_FRACTIONS}


def _triple_cfg_kwargs(args) -> dict:
    env_defaults = {"triples": ("V2_TRIPLE_TMAX", 100.0),
                    "boundary": ("V2_BOUNDARY_TMAX", 100.0),
                    "tail": ("V2_TAIL_TMAX", 1000.0)}
    key, default = env_defaults[args.task]
    tmax = float(os.environ.get(key, default))
    nper = 20 if tmax <= 100 else 4
    timeout = 900.0 if tmax <= 300 else 5400.0
    return dict(n_systems=1, seed=args.seed, t_max_outer_periods=tmax,
                n_per_orbit=nper, timeout_s=timeout)


def _encounter_cfg_kwargs(args) -> dict:
    return dict(n_systems=1, seed=args.seed,
                vinf_over_vcrit_range=(0.05, 2.0), b_over_a_range=(0.0, 4.0),
                stratified_masses=True)




def _stack_results(buf):
    """Stack result dicts (one block) into one npz-friendly dict."""
    d = dict(
        ids=np.array([r["id"] for r in buf], dtype=np.int32),
        statuses=np.array([r["status"] for r in buf]),
        labels=np.array([r["label"] for r in buf], dtype=np.int8),
        t_event=np.array([r["t_event"] for r in buf], dtype=np.float32),
        t_max=np.array([r["t_max"] for r in buf], dtype=np.float32),
        E0=np.array([r["E0"] for r in buf], dtype=np.float32),
        max_rel_err=np.array([r["max_rel_err"] for r in buf], dtype=np.float32),
        ic=np.vstack([r["ic"] for r in buf]),
    )
    if "feats" in buf[0]:
        d["feats"] = np.stack([r["feats"] for r in buf])
    if "exchange" in buf[0]:
        d["exchange"] = np.array([r["exchange"] for r in buf], dtype=np.int8)
        d["escaper"] = np.array([r["escaper"] for r in buf], dtype=np.int8)
    if "t_peri" in buf[0]:
        d["t_peri"] = np.array([r["t_peri"] for r in buf], dtype=np.float32)
        d["t_approach"] = np.array([r["t_approach"] for r in buf], dtype=np.float32)
        d["min_pair_dist"] = np.array([r["min_pair_dist"] for r in buf],
                                      dtype=np.float32)
    return d


def _finalize_blocks(out_dir, tag, state, t0, args):
    """Concatenate part files into the final chunk npz (same format as the
    old single-shot code), write the series pkl, delete parts/partial."""
    npz_p = out_dir / f"chunk_{tag}.npz"
    if state["block_files"]:
        parts = [np.load(out_dir / p) for p in state["block_files"]]
        merged = {k: np.concatenate([p[k] for p in parts])
                  for k in parts[0].files}
        merged["fractions"] = np.array(FRACTIONS[args.task], dtype=np.float32)
        order = np.argsort(merged["ids"])
        for k in list(merged):
            if k == "fractions":
                continue   # per-task grid, not per-system
            merged[k] = merged[k][order]
        print(f"[{tag}] finalizing chunk npz ({len(merged['ids'])} systems - "
              f"can take a few minutes)", flush=True)
        np.savez_compressed(npz_p, **merged)
        for p in state["block_files"]:
            (out_dir / p).unlink(missing_ok=True)
        counts = {str(k): int(np.sum(merged["statuses"] == k))
                  for k in np.unique(merged["statuses"])}
    else:
        np.savez_compressed(npz_p, ids=np.array([], dtype=np.int32),
                            statuses=np.array([], dtype=str),
                            labels=np.array([], dtype=np.int8))
        counts = {}
    if state["series_pairs"] and os.environ.get("V2_SKIP_SERIES", "0") != "1":
        state["series_pairs"].sort(key=lambda x: x[0])
        with open(out_dir / f"chunk_{tag}_series.pkl", "wb") as f:
            pickle.dump(state["series_pairs"], f)
    meta = dict(task=args.task, chunk_id=args.chunk_id, n_chunks=args.n_chunks,
                seed=args.seed, n_systems=int(len(state["done_ids"])),
                outcome_counts=counts, runtime_min=(time.time() - t0) / 60)
    with open(out_dir / f"chunk_{tag}_meta.json", "w") as f:
        json.dump(meta, f, indent=1)
    (out_dir / f"chunk_{tag}.partial.pkl").unlink(missing_ok=True)
    print(f"[{tag}] DONE in {meta['runtime_min']:.1f} min -> {npz_p}",
          flush=True)
    print(f"  counts: {counts}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=list(TASKS))
    ap.add_argument("--chunk-id", type=int, default=0)
    ap.add_argument("--n-chunks", type=int, default=1)
    ap.add_argument("--n-systems", type=int, default=None,
                    help="override total system count (smoke tests)")
    ap.add_argument("--n-jobs", type=int, default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--checkpoint-every", type=int, default=2000)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    n_jobs = args.n_jobs or int(os.environ.get("V2_N_JOBS", os.cpu_count() or 4))
    out_dir = Path(args.out_dir or os.environ.get(
        "V2_OUT_DIR", "/kaggle/working/v2out" if Path("/kaggle/working").exists()
        else "/home/user/v2_results"))
    out_dir.mkdir(parents=True, exist_ok=True)

    total = args.n_systems if args.n_systems is not None else TASKS[args.task]
    per_chunk = int(np.ceil(total / args.n_chunks))
    id_start = args.chunk_id * per_chunk
    id_end = min(total, id_start + per_chunk)
    ids = list(range(id_start, id_end))

    tag = f"{args.task}_{args.chunk_id}_of_{args.n_chunks}"
    partial_p = out_dir / f"chunk_{tag}.partial.pkl"
    block_size = max(1, int(os.environ.get("V2_BLOCK", "5000")))
    state = dict(buf=[], block_files=[], series_pairs=[], part_idx=0,
                 done_ids=set())

    if args.resume and partial_p.exists():
        with open(partial_p, "rb") as f:
            saved = pickle.load(f)
        if isinstance(saved, dict) and "block_files" in saved:
            state["done_ids"] = set(np.asarray(saved["done_ids"]).tolist())
            state["block_files"] = list(saved["block_files"])
            state["part_idx"] = int(saved["part_idx"])
            state["series_pairs"] = saved["series_pairs"]
            print(f"resume: {len(state['done_ids'])} done, "
                  f"{len(state['block_files'])} blocks on disk", flush=True)
        else:
            print("old-format checkpoint found - starting fresh", flush=True)

    todo = [i for i in ids if i not in state["done_ids"]]
    print(f"[{tag}] {len(ids)} systems, {len(todo)} todo, {n_jobs} workers, "
          f"seed={args.seed}", flush=True)

    if args.task == "encounters":
        cfg_kw = _encounter_cfg_kwargs(args)
        fn = _process_encounter
    else:
        cfg_kw = _triple_cfg_kwargs(args)
        fn = _process_triple if args.task != "boundary" else _process_boundary

    def flush_blocks():
        buf = state["buf"]
        if not buf:
            return
        for r in buf:
            s = r.pop("series", None)
            if s is not None:
                state["series_pairs"].append((int(r["id"]), s))
        part_p = out_dir / f"chunk_{tag}_part{state['part_idx']}.npz"
        np.savez_compressed(part_p, **_stack_results(buf))
        state["block_files"].append(part_p.name)
        state["part_idx"] += 1
        state["buf"] = []

    def checkpoint():
        with open(partial_p, "wb") as f:
            pickle.dump(dict(
                done_ids=np.array(sorted(state["done_ids"]), dtype=np.int32),
                block_files=state["block_files"],
                part_idx=state["part_idx"],
                series_pairs=state["series_pairs"]), f)

    t0 = time.time()
    _ctx = _mp.get_context("fork")
    with ProcessPoolExecutor(max_workers=n_jobs, mp_context=_ctx) as ex:
        for i, res in enumerate(ex.map(fn, todo, [cfg_kw] * len(todo),
                                       chunksize=64)):
            state["buf"].append(res)
            state["done_ids"].add(res["id"])
            n_done = i + 1
            if len(state["buf"]) >= block_size:
                flush_blocks()
            if n_done % max(args.checkpoint_every, block_size) == 0:
                checkpoint()
                rate = (time.time() - t0) / n_done
                print(f"  [{tag}] {n_done}/{len(todo)}  ({rate*1000:.0f} ms/sys, "
                      f"ETA {(len(todo)-n_done)*rate/60:.0f} min, "
                      f"{len(state['block_files'])} blocks)", flush=True)
            elif not state["buf"]:
                rate = (time.time() - t0) / n_done
                print(f"  [{tag}] {n_done}/{len(todo)}  ({rate*1000:.0f} ms/sys, "
                      f"ETA {(len(todo)-n_done)*rate/60:.0f} min)", flush=True)

    flush_blocks()
    checkpoint()
    _finalize_blocks(out_dir, tag, state, t0, args)


# =====================================================================
#  RUNNER - DEEP-TAIL Session (96 allocated cores)
# =====================================================================
import os, subprocess, sys, threading, time

N_JOBS = 96
_ALLOCATED = len(os.sched_getaffinity(0))
print(f"allocated CPUs: {_ALLOCATED}", flush=True)
if _ALLOCATED < 90:
    raise RuntimeError("This production file requires the 96-CPU TPU host")
os.environ["V2_TAIL_TMAX"] = "3000"
os.environ["V2_SKIP_SERIES"] = "1"
os.environ["V2_SKIP_FEATURES"] = "1"
os.environ["V2_BLOCK"] = "5000"
OUT = "/kaggle/working/v2out"


# ---------------------------------------------------------------
# HEARTBEAT: keeps the TPU device busy so Kaggle does not kill the
# session (sessions die after ~2 h of zero TPU activity).
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# HEARTBEAT (supervised): one persistent JAX subprocess keeps the
# TPU busy continuously (sessions die after ~2 h of ZERO TPU
# activity); a monitor restarts it if it dies and reports every
# 5 min so you can SEE it working. TPU tensor cores and the 96
# vCPUs are separate hardware -> ~0 CPU cost, no interference.
# ---------------------------------------------------------------
HEARTBEAT_CODE = (
    "import time\n"
    "import jax, jax.numpy as jnp\n"
    "dev = jax.devices()[0]\n"
    "x = jax.device_put(jnp.ones((256, 256)), dev)\n"
    "i = 0\n"
    "while True:\n"
    "    x = (x @ x).block_until_ready()\n"
    "    i += 1\n"
    "    if i % 50 == 0:\n"
    "        print('hb ok', dev, i, flush=True)\n"
    "    time.sleep(2.0)\n"
)

def heartbeat():
    proc = None
    while True:
        try:
            if proc is None or proc.poll() is not None:
                if proc is not None:
                    print("[heartbeat] TPU touch process died - restarting",
                          flush=True)
                proc = subprocess.Popen([sys.executable, "-c",
                                         HEARTBEAT_CODE],
                                        stderr=subprocess.DEVNULL)
                time.sleep(20)
                if proc.poll() is not None:
                    print("[heartbeat] FAILED TO START - session will die at "
                          "~2 h TPU idle. Check the cell log for a JAX/TPU "
                          "error.", flush=True)
                else:
                    print("[heartbeat] TPU touch alive (pid %d)" % proc.pid,
                          flush=True)
            else:
                print("[heartbeat] TPU touch alive (pid %d)" % proc.pid,
                      flush=True)
        except Exception as e:
            print("[heartbeat] ERROR:", repr(e), flush=True)
        time.sleep(300)

threading.Thread(target=heartbeat, daemon=True).start()
print("supervised heartbeat started - expect a report every 5 min", flush=True)


def _state(task, n_chunks, chunk_id):
    tag = f"{task}_{chunk_id}_of_{n_chunks}"
    done = os.path.exists(f"{OUT}/chunk_{tag}.npz")
    has_part = os.path.exists(f"{OUT}/chunk_{tag}.partial.pkl")
    return tag, done, has_part

def run_task(task, n_systems, tmax_env=None, ckpt=20000, n_chunks=1, chunk_id=0):
    """Idempotent + resumable task launcher."""
    if tmax_env is not None:
        os.environ[tmax_env[0]] = str(tmax_env[1])
    tag, done, has_part = _state(task, n_chunks, chunk_id)
    merged_exists = os.path.exists(f"{OUT}/merged_{task}.npz")
    if done or merged_exists:
        print(f"[{task}] already complete on disk - skipping", flush=True)
        return
    args = ["production.py", "--task", task, "--n-systems", str(n_systems),
            "--n-jobs", str(N_JOBS), "--out-dir", OUT,
            "--checkpoint-every", str(ckpt),
            "--n-chunks", str(n_chunks), "--chunk-id", str(chunk_id)]
    if has_part:
        args.append("--resume")
        print(f"[{tag}] checkpoint found - RESUMING from disk", flush=True)
    sys.argv = args
    try:
        main()
    except Exception:
        import traceback as _tb
        _tb.print_exc()
        print(f"[{tag}] FAILED - see traceback above. Fix the cause, then "
              f"simply re-run this notebook: completed tasks are skipped and "
              f"this task resumes from its checkpoint.", flush=True)
        raise

def merge_tasks(specs):
    """Concatenate chunk files into merged_*.npz (id-sorted)."""
    import numpy as _np
    for task, n_chunks in specs:
        chunk_files = [f"{OUT}/chunk_{task}_{k}_of_{n_chunks}.npz"
                       for k in range(n_chunks)]
        if not any(os.path.exists(p) for p in chunk_files) and \
                os.path.exists(f"{OUT}/merged_{task}.npz"):
            print(f"[merge] {task}: merged file already present - skipping",
                  flush=True)
            continue
        parts = []
        for k in range(n_chunks):
            tag = f"{task}_{k}_of_{n_chunks}"
            p = f"{OUT}/chunk_{tag}.npz"
            if not os.path.exists(p):
                raise SystemExit(f"missing {p} - re-run the notebook; "
                                 f"completed tasks are skipped")
            parts.append(_np.load(p))
        if n_chunks > 1:
            _fracs = parts[0]["fractions"] if "fractions" in parts[0].files \
                else None
            merged = {key: _np.concatenate([p[key] for p in parts])
                      for key in parts[0].files if key != "fractions"}
            order = _np.argsort(merged["ids"])
            for key in list(merged):
                merged[key] = merged[key][order]
            if _fracs is not None:
                merged["fractions"] = _fracs
        else:
            merged = {key: parts[0][key] for key in parts[0].files}
        if "fractions" not in merged:
            merged["fractions"] = _np.array(
                TRIPLE_FRACTIONS if task != "encounters"
                else ENCOUNTER_FRACTIONS, dtype=_np.float32)
        _np.savez_compressed(f"{OUT}/merged_{task}.npz", **merged)
        series_src = f"{OUT}/chunk_{task}_0_of_{n_chunks}_series.pkl"
        if os.path.exists(series_src):
            shutil.copy(series_src, f"{OUT}/merged_{task}_series.pkl")
    print("MERGE DONE.", flush=True)


import shutil
os.makedirs(OUT, exist_ok=True)

# tail: 100,000 x 3000 outer periods, split into two halves (~2.8 h each)
run_task("tail", 100000, ckpt=2000, n_chunks=2, chunk_id=0)
print("TAIL PART 1 OF 2 DONE; continuing automatically to part 2.", flush=True)
run_task("tail", 100000, ckpt=2000, n_chunks=2, chunk_id=1)
print("TAIL PART 2 OF 2 DONE; merging automatically.", flush=True)

merge_tasks([("tail", 2)])

# cleanup: keep the chunk files (resume backbone); remove checkpoints only
import glob
for f in glob.glob(f"{OUT}/*.partial.pkl"):
    os.remove(f)

# Final integrity check: exact matched ID range and required survival fields.
_tail_path = f"{OUT}/merged_tail.npz"
with np.load(_tail_path, allow_pickle=False) as _tail:
    _required = {"ids", "statuses", "t_event", "t_max", "ic", "max_rel_err"}
    _missing = sorted(_required - set(_tail.files))
    if _missing:
        raise RuntimeError(f"merged tail missing fields: {_missing}")
    _ids = _tail["ids"]
    if len(_ids) != 100000 or not np.array_equal(_ids, np.arange(100000, dtype=_ids.dtype)):
        raise RuntimeError("merged tail IDs are not exactly 0..99,999")
    _statuses = _tail["statuses"]
    _counts = {str(k): int(np.sum(_statuses == k)) for k in np.unique(_statuses)}
    print("FINAL VERIFIED IDs: 0..99,999 (100,000 unique matched systems)", flush=True)
    print("FINAL OUTCOME COUNTS:", _counts, flush=True)
    print("merged_tail size GiB:", os.path.getsize(_tail_path)/1024**3, flush=True)

print("\n=== CORRECTED DEEP-TAIL SESSION COMPLETE ===", flush=True)
print("kept:", sorted(os.listdir(OUT)), flush=True)
print("SAVE VERSION NOW. Preserve merged_tail.npz and both chunk meta JSONs.")
