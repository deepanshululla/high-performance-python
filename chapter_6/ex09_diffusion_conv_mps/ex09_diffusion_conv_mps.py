"""Chapter 6 - Exercise 9: diffusion as a convolution on the GPU (Example 6-23).

Task: the laplacian (roll up/down/left/right and subtract 4*center) is exactly a
3x3 convolution. GPUs have hardware tuned for convolutions, so express the
laplacian as a `Conv2d` with a circular-padding kernel and compare against the
explicit roll version from ex07 -- both on the MPS GPU.

Kernel note: the book prints [[0,-1,0],[-1,4,-1],[0,-1,0]], which is the NEGATIVE
laplacian (it computes 4*center - neighbors). To match ex07's roll laplacian
(neighbors - 4*center) we use the standard-sign kernel [[0,1,0],[1,-4,1],[0,1,0]]
so the two diffusions produce identical grids.

Takeaway: this is not an algorithm change -- it is the SAME computation routed
through a more optimized, purpose-built GPU kernel. On this machine convolution
beats the roll version at every grid size; the book saw it win only on large CUDA
grids. Either way: prefer already-optimized primitives over hand-assembled ones.

Run: .venv/bin/python chapter_6/ex09_diffusion_conv_mps.py
"""
import time

import torch

GRID = 1024
ITERS = 100


def pick_device():
    if torch.backends.mps.is_available():
        return "mps", torch.mps.synchronize
    if torch.cuda.is_available():
        return "cuda", torch.cuda.synchronize
    return "cpu", lambda: None


# --- explicit roll laplacian (same as ex07) -----------------------------------
def laplacian_roll(g):
    return (torch.roll(g, +1, 0) + torch.roll(g, -1, 0)
            + torch.roll(g, +1, 1) + torch.roll(g, -1, 1) - 4 * g)


def run_roll(n, iters, device):
    g = torch.zeros((n, n), device=device)
    lo, hi = int(n * 0.4), int(n * 0.5)
    g[lo:hi, lo:hi] = 0.005
    for _ in range(iters):
        g = g + 0.1 * laplacian_roll(g)
    return g


# --- convolution laplacian ----------------------------------------------------
def make_conv(device):
    # standard 5-point laplacian kernel: center -4, orthogonal neighbors +1.
    kernel = torch.as_tensor(
        [[0., 1., 0.],
         [1., -4., 1.],
         [0., 1., 0.]]
    ).broadcast_to(1, 1, 3, 3).to(device)
    conv = torch.nn.Conv2d(1, 1, kernel_size=3, bias=False,
                           padding_mode="circular", padding=1).to(device)
    conv.weight = torch.nn.Parameter(kernel)
    return conv


def run_conv(n, iters, device):
    conv = make_conv(device)
    g = torch.zeros((1, 1, n, n), device=device)   # conv wants [batch, channel, H, W]
    lo, hi = int(n * 0.4), int(n * 0.5)
    g[0, 0, lo:hi, lo:hi] = 0.005
    with torch.no_grad():
        for _ in range(iters):
            g = g + 0.1 * conv(g)
    return g[0, 0]


def timed(fn, sync, warmups=2, reps=3):
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
          + ("" if device != "cpu" else "  (NO GPU available -- not a real GPU test)"))

    # Correctness: convolution must reproduce the roll laplacian exactly.
    roll = run_roll(GRID, ITERS, device)
    conv = run_conv(GRID, ITERS, device)
    assert torch.allclose(roll, conv, atol=1e-6), "conv diverged from roll!"
    print(f"Convolution matches the roll laplacian after {ITERS} iters "
          f"(max abs diff {torch.max(torch.abs(roll - conv)).item():.2e})")

    print(f"\nDiffusion on {device}, {ITERS} iterations, by grid size:")
    for n in (256, 1024, 2048):
        t_roll = timed(lambda n=n: run_roll(n, ITERS, device), sync)
        t_conv = timed(lambda n=n: run_conv(n, ITERS, device), sync)
        faster = "conv" if t_conv < t_roll else "roll"
        ratio = max(t_roll, t_conv) / min(t_roll, t_conv)
        print(f"  {n:>4}x{n:<4}: roll {t_roll * 1e3:7.1f} ms   conv {t_conv * 1e3:7.1f} ms   "
              f"-> {faster} faster ({ratio:.2f}x)")
    print("  -> same math, different kernel: the convolution routes the work through")
    print("     purpose-built, heavily optimized GPU code. Prefer optimized primitives")
    print("     over hand-assembled equivalents (algorithmic swaps like this are never")
    print("     done for you automatically -- you have to reach for them).")


if __name__ == "__main__":
    main()
