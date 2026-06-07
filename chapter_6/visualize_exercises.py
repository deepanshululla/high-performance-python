"""Generate a chart for every Chapter 6 exercise and tile them into a dashboard.

Each exercise lives in its own folder (chapter_6/exNN_name/exNN_name.py). This
driver imports each module by path, REUSES its functions to measure the key
comparison, saves `chart.png` into that folder, then assembles
`exercises_dashboard.png` here.

Run: .venv/bin/python chapter_6/visualize_exercises.py
     .venv/bin/python chapter_6/visualize_exercises.py --only ex07   # one exercise
"""
import importlib.util
import pathlib
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
C = {"py": "#7f7f7f", "np": "#1f77b4", "np2": "#17becf", "gpu": "#2ca02c",
     "bad": "#d62728", "warn": "#ff7f0e", "alt": "#9467bd"}


def load(folder):
    path = HERE / folder / f"{folder}.py"
    spec = importlib.util.spec_from_file_location(folder, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def best(fn, reps=3, warmup=0, sync=None):
    for _ in range(warmup):
        fn()
        if sync:
            sync()
    b = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        if sync:
            sync()
        b = min(b, time.perf_counter() - t)
    return b


def barlabels(ax, bars, fmt="{:.1f}", dy=1.02):
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h * dy, fmt.format(h),
                ha="center", va="bottom", fontsize=8)


# ---------------------------------------------------------------- per exercise
def ex01(ax):
    m = load("ex01_list_vs_numpy_norm")
    N = 1_000_000
    py = list(range(N))
    npv = np.arange(N)
    cases = [("python\nloop", lambda: m.norm_square_list(py), C["py"]),
             ("list\ncomp", lambda: m.norm_square_list_comprehension(py), C["py"]),
             ("numpy\nv*v+sum", lambda: m.norm_square_numpy(npv), C["np"]),
             ("numpy\ndot", lambda: m.norm_square_numpy_dot(npv), C["gpu"])]
    times = [best(fn, reps=3) * 1e3 for _, fn, _ in cases]
    bars = ax.bar([c[0] for c in cases], times, color=[c[2] for c in cases])
    ax.set_yscale("log"); ax.set_ylabel("time (ms, log)")
    ax.set_title("ex01 — norm² four ways (1M elems)")
    barlabels(ax, bars, "{:.2f}")


def ex02(ax):
    m = load("ex02_diffusion_python_vs_numpy")
    n, it = m.GRID, m.ITERS
    cases = [("python\n(alloc/iter)", lambda: m.run_py(it, n), C["py"]),
             ("python\n(prealloc)", lambda: m.run_py_prealloc(it, n), C["py"]),
             ("numpy", lambda: m.run_np(it, n), C["np"])]
    times = [best(fn, reps=2) * 1e3 for _, fn, _ in cases]
    bars = ax.bar([c[0] for c in cases], times, color=[c[2] for c in cases])
    ax.set_yscale("log"); ax.set_ylabel("time (ms, log)")
    ax.set_title(f"ex02 — diffusion {n}² ×{it}: Python vs numpy")
    barlabels(ax, bars, "{:.1f}")


def ex03(ax):
    sizes = (5, 100, 1024, 2048)
    oop, ip = [], []
    for n in sizes:
        a, b = np.random.random((2, n, n))
        reps = 2000 if n <= 100 else 50
        oop.append(best(lambda a=a, b=b: a + b, reps=reps) * 1e6)
        ip.append(best(lambda a=a, b=b: a.__iadd__(b), reps=reps) * 1e6)
    x = range(len(sizes)); w = 0.38
    ax.bar([i - w / 2 for i in x], oop, w, color=C["bad"], label="out-of-place a=a+b")
    ax.bar([i + w / 2 for i in x], ip, w, color=C["gpu"], label="in-place a+=b")
    ax.set_yscale("log"); ax.set_xticks(list(x)); ax.set_xticklabels([f"{n}²" for n in sizes])
    ax.set_ylabel("time (µs, log)"); ax.set_title("ex03 — in-place vs out-of-place")
    ax.legend(fontsize=8)


def ex04(ax):
    m = load("ex04_numpy_diffusion_memory")
    n, it = m.GRID, m.ITERS
    cases = [("naive\n(alloc/iter)", lambda: m.run_naive(it, n), C["bad"]),
             ("in-place\n(scratch)", lambda: m.run_inplace(it, n), C["gpu"])]
    times = [best(fn, reps=2) * 1e3 for _, fn, _ in cases]
    bars = ax.bar([c[0] for c in cases], times, color=[c[2] for c in cases])
    ax.set_ylabel("time (ms)"); ax.set_title(f"ex04 — numpy allocations ({n}² ×{it})")
    barlabels(ax, bars)


def ex05(ax):
    m = load("ex05_roll_vs_roll_add")
    n, it = m.GRID, m.ITERS
    cases = [("np.roll\nlaplacian", lambda: m.run(m.laplacian_roll, it, n), C["np"]),
             ("custom\nroll_add", lambda: m.run(m.laplacian_roll_add, it, n), C["warn"])]
    times = [best(fn, reps=2) * 1e3 for _, fn, _ in cases]
    bars = ax.bar([c[0] for c in cases], times, color=[c[2] for c in cases])
    ax.set_ylabel("time (ms)")
    ax.set_title(f"ex05 — np.roll vs custom roll_add ({n}² ×{it})")
    barlabels(ax, bars)


def ex06(ax):
    N = 2048
    cases = [("float64", np.float64, C["np"]), ("float32", np.float32, C["gpu"]),
             ("float16", np.float16, C["bad"])]
    times = []
    for _, dt, _ in cases:
        a = np.random.rand(N, N).astype(dt)
        times.append(best(lambda a=a: a * a + a, reps=5) * 1e3)
    bars = ax.bar([c[0] for c in cases], times, color=[c[2] for c in cases])
    ax.set_yscale("log"); ax.set_ylabel("time (ms, log)")
    ax.set_title(f"ex06 — CPU precision a*a+a ({N}²)")
    barlabels(ax, bars, "{:.2f}")


def _device():
    import torch
    if torch.backends.mps.is_available():
        return "mps", torch.mps.synchronize
    if torch.cuda.is_available():
        return "cuda", torch.cuda.synchronize
    return "cpu", lambda: None


def ex07(ax):
    m = load("ex07_diffusion_mps")
    dev, sync = _device()
    n, it = m.GRID, m.ITERS
    t_cpu = best(lambda: m.run_np(n, it), reps=2) * 1e3
    t_gpu = best(lambda: m.run_t(n, it, dev), reps=3, warmup=1, sync=sync) * 1e3
    bars = ax.bar(["numpy\nCPU", f"torch\n{dev}"], [t_cpu, t_gpu], color=[C["np"], C["gpu"]])
    ax.set_ylabel("time (ms)")
    ax.set_title(f"ex07 — diffusion CPU vs GPU ({n}² ×{it})")
    barlabels(ax, bars)
    ax.text(0.5, 0.92, f"GPU ~{t_cpu / t_gpu:.0f}× faster", transform=ax.transAxes,
            ha="center", fontsize=9, color=C["gpu"], fontweight="bold")


def ex08(ax):
    import torch
    m = load("ex08_when_not_gpu")
    dev, _ = _device()
    torch.manual_seed(0)
    A = (torch.rand(1000) * 1000).int().clamp(min=1)
    A_np, A_g = A.numpy(), A.to(dev)
    tgt = 200_000
    t_cpu = best(lambda: m.task(A_np, tgt), reps=10) * 1e6
    t_gpu = best(lambda: m.task(A_g, tgt), reps=3) * 1e6
    bars = ax.bar(["numpy\nCPU", f"torch\n{dev}"], [t_cpu, t_gpu], color=[C["np"], C["bad"]])
    ax.set_yscale("log"); ax.set_ylabel("time (µs, log)")
    ax.set_title("ex08 — sequential walk: CPU wins")
    barlabels(ax, bars, "{:.0f}")
    ax.text(0.5, 0.92, f"CPU ~{t_gpu / t_cpu:.0f}× faster", transform=ax.transAxes,
            ha="center", fontsize=9, color=C["bad"], fontweight="bold")


def ex09(ax):
    m = load("ex09_diffusion_conv_mps")
    dev, sync = _device()
    sizes = (256, 1024, 2048)
    roll, conv = [], []
    for n in sizes:
        roll.append(best(lambda n=n: m.run_roll(n, 100, dev), reps=2, warmup=1, sync=sync) * 1e3)
        conv.append(best(lambda n=n: m.run_conv(n, 100, dev), reps=2, warmup=1, sync=sync) * 1e3)
    x = range(len(sizes)); w = 0.38
    ax.bar([i - w / 2 for i in x], roll, w, color=C["np"], label="roll")
    ax.bar([i + w / 2 for i in x], conv, w, color=C["gpu"], label="conv")
    ax.set_xticks(list(x)); ax.set_xticklabels([f"{n}²" for n in sizes])
    ax.set_ylabel("time (ms)"); ax.set_title(f"ex09 — roll vs convolution ({dev})")
    ax.legend(fontsize=8)


def ex10(ax):
    import torch
    dev, sync = _device()
    N = 4096
    a = torch.rand(N, N, device=dev)
    b = torch.rand(N, N, device=dev)
    ah, bh = a.half(), b.half()

    def amp():
        with torch.autocast(device_type=dev):
            torch.mm(a, b)
    t32 = best(lambda: torch.mm(a, b), reps=20, warmup=5, sync=sync) * 1e3
    tac = best(amp, reps=20, warmup=5, sync=sync) * 1e3
    th = best(lambda: torch.mm(ah, bh), reps=20, warmup=5, sync=sync) * 1e3
    bars = ax.bar(["float32", "autocast", "manual\n.half()"], [t32, tac, th],
                  color=[C["np"], C["warn"], C["gpu"]])
    ax.set_ylabel("time (ms)")
    ax.set_title(f"ex10 — matmul precision/AMP ({N}², {dev})")
    barlabels(ax, bars, "{:.2f}")


def ex11(ax):
    m = load("ex11_numexpr_crossover")
    sizes = (256, 512, 1024, 2048)
    npt, net = [], []
    for n in sizes:
        npt.append(best(lambda n=n: m.run_numpy(n, 50), reps=2) * 1e3)
        net.append(best(lambda n=n: m.run_numexpr(n, 50), reps=2) * 1e3)
    x = range(len(sizes))
    ax.plot(x, npt, "o-", color=C["np"], label="numpy")
    ax.plot(x, net, "s-", color=C["warn"], label="numexpr")
    ax.set_xticks(list(x)); ax.set_xticklabels([f"{n}²" for n in sizes])
    ax.set_ylabel("time (ms)"); ax.set_title("ex11 — numexpr cache crossover")
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)


def ex12(ax):
    m = load("ex12_scipy_cautionary")
    sizes = (256, 512, 1024, 2048)
    cust, sci = [], []
    for n in sizes:
        cust.append(best(lambda n=n: m.run_custom(n, 50), reps=2) * 1e3)
        sci.append(best(lambda n=n: m.run_scipy(n, 50), reps=2) * 1e3)
    x = range(len(sizes)); w = 0.38
    ax.bar([i - w / 2 for i in x], cust, w, color=C["gpu"], label="custom roll")
    ax.bar([i + w / 2 for i in x], sci, w, color=C["bad"], label="scipy.laplace")
    ax.set_xticks(list(x)); ax.set_xticklabels([f"{n}²" for n in sizes])
    ax.set_ylabel("time (ms)"); ax.set_title("ex12 — scipy is SLOWER (cautionary tale)")
    ax.legend(fontsize=8)


EXERCISES = [
    ("ex01_list_vs_numpy_norm", ex01), ("ex02_diffusion_python_vs_numpy", ex02),
    ("ex03_inplace_vs_outofplace", ex03), ("ex04_numpy_diffusion_memory", ex04),
    ("ex05_roll_vs_roll_add", ex05), ("ex06_float_precision_cpu", ex06),
    ("ex07_diffusion_mps", ex07), ("ex08_when_not_gpu", ex08),
    ("ex09_diffusion_conv_mps", ex09), ("ex10_amp_bfloat16", ex10),
    ("ex11_numexpr_crossover", ex11), ("ex12_scipy_cautionary", ex12),
]


def save_one(folder, fn):
    fig, ax = plt.subplots(figsize=(6, 4))
    fn(ax)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out = HERE / folder / "chart.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"saved {out}")


def main():
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]

    todo = [(f, fn) for f, fn in EXERCISES if only is None or only in f]
    for folder, fn in todo:
        try:
            save_one(folder, fn)
        except Exception as e:
            print(f"  WARN {folder}: {type(e).__name__}: {e}")

    if only:
        return
    # dashboard: tile all 12 saved charts (4 rows x 3 cols)
    import matplotlib.image as mpimg
    fig, axes = plt.subplots(4, 3, figsize=(20, 22))
    for ax, (folder, _) in zip(axes.flat, EXERCISES):
        ax.axis("off")
        png = HERE / folder / "chart.png"
        if png.exists():
            ax.imshow(mpimg.imread(png))
    fig.suptitle("Chapter 6 — Exercises (Apple M1 Max, CPython 3.14, numpy 2.4, torch 2.12/MPS)",
                 fontsize=18, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.99))
    out = HERE / "exercises_dashboard.png"
    fig.savefig(out, dpi=100)
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
