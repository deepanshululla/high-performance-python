"""Chapter 6 - Exercise 7: GPU diffusion + precision on Apple Metal (Examples 6-20, 6-21).

Task: port the numpy diffusion to PyTorch and run it on the GPU, then repeat the
precision experiment ON the GPU. Compare against the CPU.

The book targets NVIDIA/CUDA (`device='cuda'`). This machine is Apple Silicon, so
we use PyTorch's **MPS** (Metal) backend instead -- the lessons about parallel
speedup and the precision knob carry over; the CUDA-specific transfer-cost lesson
does NOT (see ex08).

Takeaway:
  * GPUs win big on parallel linear algebra: the diffusion grid update is
    embarrassingly parallel, so the GPU leaves the CPU far behind.
  * Lower precision is a performance *knob* on the GPU: float16 is FASTER than
    float32 here -- the exact opposite of the CPU (ex06), where float16 is ~8x
    SLOWER for lack of native instructions.

GPU timing MUST synchronize: MPS/CUDA ops are async, so we call synchronize()
before reading the clock, and we warm up first (the first call pays compile cost).

Run: .venv/bin/python chapter_6/ex07_diffusion_mps.py
"""
import time

import numpy as np
import torch

GRID = 1024
ITERS = 200


def pick_device():
    if torch.backends.mps.is_available():
        return "mps", torch.mps.synchronize
    if torch.cuda.is_available():
        return "cuda", torch.cuda.synchronize
    return "cpu", lambda: None       # no GPU -> still runs, just not a real GPU test


# --- numpy CPU reference ------------------------------------------------------
def laplacian_np(g):
    return (np.roll(g, +1, 0) + np.roll(g, -1, 0)
            + np.roll(g, +1, 1) + np.roll(g, -1, 1) - 4 * g)


def run_np(n, iters):
    g = np.zeros((n, n))
    lo, hi = int(n * 0.4), int(n * 0.5)
    g[lo:hi, lo:hi] = 0.005
    for _ in range(iters):
        g = g + 0.1 * laplacian_np(g)
    return g


# --- torch (GPU) port: same algorithm, numpy->torch + .to(device) -------------
def laplacian_t(g):
    return (torch.roll(g, +1, 0) + torch.roll(g, -1, 0)
            + torch.roll(g, +1, 1) + torch.roll(g, -1, 1) - 4 * g)


def run_t(n, iters, device):
    g = torch.zeros((n, n), device=device)
    lo, hi = int(n * 0.4), int(n * 0.5)
    g[lo:hi, lo:hi] = 0.005
    for _ in range(iters):
        g = g + 0.1 * laplacian_t(g)
    return g


def timed(fn, sync, warmups=1, reps=3):
    for _ in range(warmups):
        fn()
        sync()
    best = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        sync()
        best = min(best, time.perf_counter() - t)
    return best


def main():
    device, sync = pick_device()
    print(f"Using device: {device}"
          + ("" if device != "cpu" else "  (NO GPU available -- this is NOT a real GPU test)"))

    # Correctness: the torch port matches numpy.
    ref = run_np(GRID, ITERS)
    got = run_t(GRID, ITERS, device).cpu().numpy()
    assert np.allclose(ref, got, atol=1e-8), "torch port diverged from numpy!"
    print(f"torch port matches numpy after {ITERS} iters (max abs diff {np.max(np.abs(ref - got)):.2e})")

    t_cpu = timed(lambda: run_np(GRID, ITERS), lambda: None, warmups=0, reps=2)
    t_gpu = timed(lambda: run_t(GRID, ITERS, device), sync)
    print(f"\nDiffusion {GRID}x{GRID}, {ITERS} iterations:")
    print(f"  numpy (CPU):   {t_cpu * 1e3:8.1f} ms")
    print(f"  torch ({device}): {t_gpu * 1e3:8.1f} ms   -> ~{t_cpu / t_gpu:.1f}x faster on GPU")

    # Precision knob ON the GPU: float16 should be FASTER than float32.
    print(f"\nPrecision on {device} (a*a + a, 4096x4096):")
    base = None
    for dt in (torch.float32, torch.float16):
        a = torch.rand(4096, 4096, dtype=dt, device=device)
        sync()
        t = timed(lambda a=a: a * a + a, sync, warmups=3, reps=20)
        if base is None:
            base = t
        print(f"  {str(dt).replace('torch.', ''):8}: {t * 1e3:7.3f} ms   ({base / t:.2f}x vs float32)")
    print("  -> on the GPU, float16 is FASTER (more values per transfer, native low-precision")
    print("     compute). Contrast ex06: on the CPU float16 was ~8x SLOWER. Precision is a")
    print("     speed knob on the GPU but a penalty on the CPU.")


if __name__ == "__main__":
    main()
