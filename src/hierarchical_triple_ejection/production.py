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
from __future__ import annotations

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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v2.core import TripleConfig, simulate_triple, sample_triple_ic, make_triple_sim
from v2.encounters import EncounterConfig, simulate_encounter
from v2.features import extract_window_features

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
        ic=_ic_vec(rec["ic"]),
        feats=feats,
    )
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
        feats=np.stack([r["feats"] for r in buf]),
    )
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


if __name__ == "__main__":
    main()
