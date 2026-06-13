"""Chapter 6 - Exercise 8: when NOT to use the GPU (Example 6-25).

Task: run a deliberately sequential, branch-heavy task -- walk an array where each
step's index is the previous element's value, until the running sum hits a target
-- on the CPU (numpy) vs the GPU (torch). Each step depends on the last, so there
is nothing to parallelize.

Takeaway: a GPU has thousands of SLOW cores; a CPU has a few FAST ones. When the
work is one dependent step at a time, the many-cores advantage evaporates and the
GPU loses badly -- here numpy is dramatically faster. Worse, indexing a GPU tensor
element-by-element (`A[i]`) forces a tiny CPU<->GPU sync on every step, so the GPU
version pays a transfer penalty thousands of times.

This is also the closest we get on Apple Silicon to the book's CUDA "transfer is
the #1 killer" lesson: because Apple has *unified memory*, a one-shot `.to()` copy
is cheap, but per-element syncs in a hot loop are still ruinous.

Run: .venv/bin/python chapter_6/ex08_when_not_gpu.py
"""
import time

import torch


def pick_device():
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def task(A, target, cap=10_000_000):
    """Walk A: add A[i] to a running total and jump to index A[i], until the total
    reaches target. Purely sequential -- step k+1 needs step k's result. `cap`
    guards against a pathological non-terminating walk."""
    result = 0
    i = 0
    n = 0
    while result < target:
        result += int(A[i])
        i = int(A[i])
        n += 1
        if n >= cap:
            break
    return n


def main():
    device = pick_device()
    print(f"Using device: {device}"
          + ("" if device != "cpu" else "  (NO GPU available -- comparison is degenerate)"))

    torch.manual_seed(0)
    N = 1000
    # values in [1, N) -> always a valid index AND result strictly grows (no 0 ->
    # no infinite loop). target is large enough to force a long dependent walk.
    A_cpu = (torch.rand(N) * N).int().clamp(min=1)
    A_np = A_cpu.numpy()
    A_gpu = A_cpu.to(device)

    target = 200_000
    # Same input, same answer on both devices.
    n_cpu = task(A_np, target)
    n_gpu = task(A_gpu, target)
    assert n_cpu == n_gpu, (n_cpu, n_gpu)
    print(f"Both reach target in {n_cpu} sequential steps (identical walk).")

    def bench(A, reps):
        for _ in range(2):              # warmup
            task(A, target)
        best = float("inf")
        for _ in range(reps):
            t = time.perf_counter()
            task(A, target)
            best = min(best, time.perf_counter() - t)
        return best

    t_cpu = bench(A_np, reps=20)
    t_gpu = bench(A_gpu, reps=5)        # GPU is slow here -- fewer reps
    print(f"\nSequential branchy task (N={N}, target={target:,}, {n_cpu} steps):")
    print(f"  numpy (CPU):   {t_cpu * 1e6:9.1f} us/run")
    print(f"  torch ({device}): {t_gpu * 1e6:9.1f} us/run   -> CPU is ~{t_gpu / t_cpu:.0f}x faster")
    print("  -> the GPU loses by a wide margin: the work can't parallelize, and every")
    print("     element read off the GPU tensor forces a tiny sync. Use the GPU for")
    print("     bulk vectorized math (ex07), not sequential, data-dependent, branchy code.")


if __name__ == "__main__":
    main()
