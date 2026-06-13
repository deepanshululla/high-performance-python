"""H4: GPU batching is nearly free until the cores saturate.

HYPOTHESIS: A GPU has thousands of cores; a single 512x512 convolution uses only a
fraction of them. So running a BATCH of B independent convolutions as one op should
cost roughly the same as one -- the per-item time should collapse as B grows, until
the batch is big enough to saturate the hardware.

PREDICTION: per-item time drops sharply with B, then flattens at saturation.

VERDICT (measured): CONFIRMED. Per-item time fell ~18x from batch 1 to 256, flatting
out as the cores fill. This confirms the aside in ex09 (GPUs eat batches with little
penalty) and explains why deep-learning throughput is measured in samples/sec at a
tuned batch size, not single-example latency.

Requires a GPU (MPS/CUDA); degrades to a note on CPU.

Run:  .venv/bin/python chapter_6/hypothesis/h4_gpu_batching/bench.py
Plot: .venv/bin/python chapter_6/hypothesis/h4_gpu_batching/bench.py --plot
"""
import pathlib
import sys
import time

import torch

BATCHES = (1, 4, 16, 64, 256)
GRID = 512


def pick_device():
    if torch.backends.mps.is_available():
        return "mps", torch.mps.synchronize
    if torch.cuda.is_available():
        return "cuda", torch.cuda.synchronize
    return "cpu", lambda: None


def make_conv(device):
    kernel = torch.as_tensor(
        [[0., 1., 0.], [1., -4., 1.], [0., 1., 0.]]
    ).broadcast_to(1, 1, 3, 3).to(device)
    conv = torch.nn.Conv2d(1, 1, 3, bias=False, padding_mode="circular", padding=1).to(device)
    conv.weight = torch.nn.Parameter(kernel)
    return conv


def timed(fn, sync, warmups=3, reps=5):
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


def collect():
    device, sync = pick_device()
    if device == "cpu":
        return {"device": device}
    conv = make_conv(device)
    totals, per_item = [], []
    for B in BATCHES:
        g = torch.rand(B, 1, GRID, GRID, device=device)
        with torch.no_grad():
            t = timed(lambda g=g: conv(g), sync)
        totals.append(t * 1e3)
        per_item.append(t / B * 1e3)
    return {"device": device, "batches": list(BATCHES), "total": totals, "per_item": per_item}


def report(data):
    if data["device"] == "cpu":
        print("No GPU available -- batching has no parallel cores to fill, so this")
        print("hypothesis is GPU-specific. Install/enable MPS or CUDA to see it.")
        return
    print(f"Using device: {data['device']}\n")
    print(f"{GRID}x{GRID} convolution, varying batch size B:")
    print(f"{'batch':>6}  {'total':>10}  {'per-item':>10}")
    base = data["per_item"][0]
    for B, tot, per in zip(data["batches"], data["total"], data["per_item"]):
        print(f"{B:>6}  {tot:8.2f} ms  {per:8.3f} ms   ({base / per:4.1f}x cheaper/item)")
    print("\n-> per-item cost collapses as the batch fills idle cores, then flattens at")
    print("   saturation. Batching is how you actually feed a GPU -- confirms ex09's aside.")


def plot(data, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if data["device"] == "cpu":
        print("no GPU -> nothing to plot")
        return
    b = data["batches"]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    ax.plot(b, data["per_item"], "o-", color="#9467bd")
    ax.set_xscale("log", base=2)
    ax.set_xticks(b)
    ax.set_xticklabels(b)
    ax.set_xlabel("batch size")
    ax.set_ylabel("per-item time (ms)")
    ax.set_title("Per-item cost collapses with batch")
    ax.grid(True, alpha=0.3)
    for xi, yi in zip(b, data["per_item"]):
        ax.text(xi, yi + max(data["per_item"]) * 0.02, f"{yi:.3f}", ha="center", fontsize=8)

    ax2.plot(b, data["total"], "s-", color="#8c564b")
    ax2.set_xscale("log", base=2)
    ax2.set_xticks(b)
    ax2.set_xticklabels(b)
    ax2.set_xlabel("batch size")
    ax2.set_ylabel("total time (ms)")
    ax2.set_title(f"{data['batches'][-1]}× the work for "
                  f"~{data['total'][-1] / data['total'][0]:.0f}× the time")
    ax2.grid(True, alpha=0.3)

    fig.suptitle(f"H4 — GPU batching is ~free until saturation ({GRID}² conv, {data['device']})",
                 fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"saved {path}")


def main():
    data = collect()
    report(data)
    if "--plot" in sys.argv:
        plot(data, pathlib.Path(__file__).with_name("h4_gpu_batching.png"))


if __name__ == "__main__":
    main()
