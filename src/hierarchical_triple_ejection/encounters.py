"""Binary-single encounters (flagship application): same diagnostics, causal
question = predict exchange/ionization/flyby BEFORE closest approach.

Setup (G=1 units): binary (bodies 0,1) with semi-major axis a=1 at the origin,
incoming single (body 2) launched from R0 with velocity v_inf and impact
parameter b. Diagnostics use the ORIGINAL binary identity for H(t) throughout
(label-agnostic, causal-safe).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import time

import numpy as np
import rebound

from .core import hierarchy_metric, pair_diagnostics, bound_pair_id, escape_energy

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
