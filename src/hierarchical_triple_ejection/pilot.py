#!/usr/bin/env python3
"""v2 pilot run: triples (causal windows) + encounters (flagship app)
+ the periastron false-positive test. Outputs to v2_results/."""
import sys, time, json
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v2 import TripleConfig, simulate_triple, triple_outcome_counts
from v2 import EncounterConfig, simulate_encounter, encounter_outcome_counts
from v2.features import extract_window_features
from v2.causal import run_causal_experiment, print_causal_table, FRACTIONS

OUT = Path("/home/user/v2_results")
OUT.mkdir(exist_ok=True)


def run_triples(n, tmax=30.0, n_per_orbit=20):
    cfg = TripleConfig(n_systems=n, seed=42, t_max_outer_periods=tmax,
                       n_per_orbit=n_per_orbit)
    recs = []
    t0 = time.time()
    for sid in range(n):
        recs.append(simulate_triple(sid, cfg))
        if (sid + 1) % 100 == 0:
            print(f"  triples {sid+1}/{n}  ({time.time()-t0:.0f}s)")
    print("  triple outcome counts:", triple_outcome_counts(recs))
    return recs, cfg


def run_encounters(n):
    cfg = EncounterConfig(n_systems=n, seed=7,
                          vinf_over_vcrit_range=(0.1, 2.5),
                          b_over_a_range=(0.0, 4.0))
    recs = []
    t0 = time.time()
    for sid in range(n):
        recs.append(simulate_encounter(sid, cfg))
        if (sid + 1) % 100 == 0:
            print(f"  encounters {sid+1}/{n}  ({time.time()-t0:.0f}s)")
    print("  encounter outcome counts:", encounter_outcome_counts(recs))
    return recs, cfg


def periastron_false_positive_test(recs):
    """Torque spike ratios: stable vs ejected triples (window = first 80%
    of the trajectory, i.e. before ejection is resolved)."""
    from v2.features import _torque_norms
    stats = {"stable": [], "ejected": []}
    for r in recs:
        key = "ejected" if r["status"] == "ejected" else "stable"
        n = len(r["t"])
        if n < 10:
            continue
        nmax = int(round(n * 0.8))
        L = r["L_pair"][:nmax]; t = r["t"][:nmax]
        G = _torque_norms(L, t)
        med = np.median(G, axis=0) + 1e-30
        stats[key].append(float(np.max(G) / np.mean(med)))
    out = {}
    for k, v in stats.items():
        v = np.array(v)
        out[k] = dict(n=len(v), median_spike=float(np.median(v)),
                      p90=float(np.percentile(v, 90)),
                      max_spike=float(np.max(v)))
    if len(stats["stable"]) and len(stats["ejected"]):
        s90 = np.percentile(stats["stable"], 90)
        e_med = np.median(stats["ejected"])
        out["overlap_frac"] = float(np.mean(np.array(stats["stable"]) > e_med))
        out["separation"] = float(s90 / max(e_med, 1e-30))
    return out


def main():
    t_start = time.time()
    print("=" * 70)
    print("V2 PILOT: causal windows on triples + encounter flagship + spike test")
    print("=" * 70)

    # ---------- triples ----------
    print("\n[1/3] IAS15 triples ...")
    trecs, _ = run_triples(400, tmax=30.0, n_per_orbit=20)
    with open(OUT / "triples_pilot_meta.json", "w") as f:
        json.dump({"counts": triple_outcome_counts(trecs)}, f, indent=1)
    arr = np.empty(len(trecs), dtype=object)
    arr[:] = trecs
    np.save(OUT / "triples_pilot_records.npy", arr, allow_pickle=True)

    print("\n[2/3] causal window experiment (ejected vs not; physical horizons) ...")
    rows = run_causal_experiment(trecs, lambda r: int(r["status"] == "ejected"),
                                 anchor="tmax_frac")
    print_causal_table(rows)
    with open(OUT / "causal_triples_pilot.json", "w") as f:
        json.dump(rows, f, indent=1)

    print("\n[3a/3] periastron false-positive test ...")
    spike = periastron_false_positive_test(trecs)
    print(json.dumps(spike, indent=1))
    with open(OUT / "spike_test_pilot.json", "w") as f:
        json.dump(spike, f, indent=1)

    # ---------- encounters ----------
    print("\n[3b/3] binary-single encounters ...")
    erecs, _ = run_encounters(400)
    earr = np.empty(len(erecs), dtype=object)
    earr[:] = erecs
    np.save(OUT / "encounters_pilot_records.npy", earr, allow_pickle=True)
    with open(OUT / "encounters_pilot_meta.json", "w") as f:
        json.dump({"counts": encounter_outcome_counts(erecs)}, f, indent=1)

    print("\n[3c/3] encounter causal experiment (exchange vs not; pre-periastron horizons) ...")
    erows = run_causal_experiment(erecs, lambda r: int(r["outcome"] == "exchange"),
                                  anchor="peri_frac")
    print_causal_table(erows)
    with open(OUT / "causal_encounters_pilot.json", "w") as f:
        json.dump(erows, f, indent=1)

    print(f"\nTOTAL PILOT TIME: {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
