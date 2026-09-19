# combine_chunks.py - VERBOSE chunk combiner (Step 3, Cell B)
# Turns chunk_*.npz (+ series pkl) into merged_*.npz for session_b.py.
# Prints progress BEFORE every slow step so silence is impossible.
#
# Env overrides (optional):
#   V2_CHUNKS_DIR   input folder (default /kaggle/input/v2chunks)
#   V2_MERGED_DIR   output folder (default /kaggle/working/merged)
import os, sys, time
import numpy as np

SRC = os.environ.get("V2_CHUNKS_DIR", "/kaggle/input/v2chunks")
DST = os.environ.get("V2_MERGED_DIR", "/kaggle/working/merged")
os.makedirs(DST, exist_ok=True)

TRIPLE_FRACS = [0.05,0.1,0.15,0.2,0.3,0.4,0.5,0.6,0.75,0.9,1.0]
ENC_FRACS = [0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.55,
             0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95,1.0]

print("=== COMBINE START ===", flush=True)
print("SRC =", SRC, "| exists:", os.path.exists(SRC), flush=True)
if not os.path.exists(SRC):
    print("ERROR: input dataset folder not found.", flush=True)
    print("Fixes: (1) right panel -> Input -> Datasets -> add the dataset", flush=True)
    print("       (2) check the dataset name matches V2_CHUNKS_DIR", flush=True)
    print("       (3) if you uploaded files directly, set SRC to their folder", flush=True)
    raise SystemExit(1)

files = sorted(os.listdir(SRC))
print("input files (%d):" % len(files), flush=True)
for f in files:
    p = os.path.join(SRC, f)
    if os.path.isfile(p):
        print("   ", f, round(os.path.getsize(p)/1e6, 1), "MB", flush=True)

def merge_one(task, chunk_files, fracs):
    missing = [f for f in chunk_files if not os.path.exists(os.path.join(SRC, f))]
    if missing:
        print(f"[{task}] MISSING: {missing} - skipping", flush=True)
        return False
    parts = []
    for f in chunk_files:
        t0 = time.time()
        print(f"[{task}] loading {f} ...", flush=True)
        parts.append(np.load(os.path.join(SRC, f)))
        print(f"[{task}]   loaded in {time.time()-t0:.0f}s", flush=True)
    t0 = time.time()
    print(f"[{task}] concatenating ...", flush=True)
    merged = {k: np.concatenate([p[k] for p in parts])
              for k in parts[0].files if k != "fractions"}
    order = np.argsort(merged["ids"])
    for k in list(merged):
        merged[k] = merged[k][order]
    merged["fractions"] = np.array(fracs, dtype=np.float32)
    out_p = os.path.join(DST, f"merged_{task}.npz")
    print(f"[{task}] writing {out_p} (uncompressed for fast analysis reads) ...", flush=True)
    np.savez(out_p, **merged)
    # copy the FIRST chunk's series pkl if present
    series_src = os.path.join(SRC, chunk_files[0].replace(".npz", "_series.pkl"))
    if os.path.exists(series_src):
        import shutil
        shutil.copy(series_src, os.path.join(DST, f"merged_{task}_series.pkl"))
        print(f"[{task}] series pkl copied", flush=True)
    print(f"[{task}] DONE: {len(merged['ids'])} systems in {time.time()-t0:.0f}s", flush=True)
    return True

ok = merge_one("encounters", ["chunk_encounters_0_of_1.npz"], ENC_FRACS)
ok = merge_one("boundary",   ["chunk_boundary_0_of_1.npz"],   TRIPLE_FRACS) or ok
ok = merge_one("triples",    ["chunk_triples_0_of_2.npz",
                              "chunk_triples_1_of_2.npz"],    TRIPLE_FRACS) or ok
# optional old tail from the first run
merge_one("tail", ["chunk_tail_0_of_1.npz"], TRIPLE_FRACS)

print("=== COMBINE DONE ===", flush=True)
print("merged:", sorted(os.listdir(DST)), flush=True)
