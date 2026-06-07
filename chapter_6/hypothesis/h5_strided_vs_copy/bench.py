"""H5: copying a strided view to contiguous first can be FASTER than operating on
the view -- but only if you reuse the contiguous buffer enough to amortize the copy.

HYPOTHESIS: A non-contiguous view (e.g. a[::2]) forces strided memory access, which
is less cache/SIMD-friendly. So `np.ascontiguousarray(view)` once, then operating on
the contiguous copy, should beat operating on the view directly -- IF the op is
repeated, so the one-time copy is amortized.

PREDICTION: for a single op, the view wins (copy overhead not repaid); for repeated
ops, copy-once wins.

VERDICT (measured): CONFIRMED, with a modest margin on this machine. The crossover is
real but small -- M1's large caches and fast memory make strided access cheap, so the
copy only just pays off. On a machine with a tighter cache the win would be larger.

Run:  .venv/bin/python chapter_6/hypothesis/h5_strided_vs_copy/bench.py
Plot: .venv/bin/python chapter_6/hypothesis/h5_strided_vs_copy/bench.py --plot
"""
import pathlib
import sys
import time

import numpy as np

N = 8192


def best(fn, reps=7):
    best_t = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        best_t = min(best_t, time.perf_counter() - t)
    return best_t


def collect():
    a = np.random.rand(N, N)
    view = a[::2]                          # every other row: a non-contiguous view
    assert not view.flags["C_CONTIGUOUS"]
    assert np.isclose((view * view).sum(), (np.ascontiguousarray(view) ** 2).sum())

    single_view = best(lambda: (view * view).sum()) * 1e3
    single_copy = best(lambda: (np.ascontiguousarray(view) ** 2).sum()) * 1e3

    def rep_view():
        return sum((view * view).sum() for _ in range(5))

    def rep_copy():
        c = np.ascontiguousarray(view)
        return sum((c * c).sum() for _ in range(5))

    five_view = best(rep_view) * 1e3
    five_copy = best(rep_copy) * 1e3
    return {"view_shape": view.shape,
            "single": {"view": single_view, "copy": single_copy},
            "five": {"view": five_view, "copy": five_copy}}


def report(data):
    print(f"view a[::2]: shape {data['view_shape']}, non-contiguous\n")
    s, f = data["single"], data["five"]
    print("single op  ((v*v).sum()):")
    print(f"  strided view:   {s['view']:7.2f} ms")
    print(f"  copy + op:      {s['copy']:7.2f} ms   -> "
          f"{'copy wins' if s['copy'] < s['view'] else 'view wins'} "
          f"({max(s.values()) / min(s.values()):.2f}x)")
    print("\n5 ops (one copy amortized):")
    print(f"  strided view:   {f['view']:7.2f} ms")
    print(f"  copy-once + op: {f['copy']:7.2f} ms   -> "
          f"{'copy wins' if f['copy'] < f['view'] else 'view wins'} "
          f"({max(f.values()) / min(f.values()):.2f}x)")
    print("\n-> a single op can't repay the copy, so the view wins; once you reuse the")
    print("   contiguous buffer, the copy amortizes and wins. The crossover is the point.")


def plot(data, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = ["single op\n(copy used once)", "5 ops\n(copy amortized)"]
    view = [data["single"]["view"], data["five"]["view"]]
    copy = [data["single"]["copy"], data["five"]["copy"]]
    x = range(len(groups))
    w = 0.36
    fig, ax = plt.subplots(figsize=(8, 4.6))
    bv = ax.bar([i - w / 2 for i in x], view, w, color="#d62728", label="strided view")
    bc = ax.bar([i + w / 2 for i in x], copy, w, color="#2ca02c", label="copy-to-contiguous")
    ax.set_xticks(list(x))
    ax.set_xticklabels(groups)
    ax.set_ylabel("time (ms, lower is better)")
    ax.set_title("H5 — strided view vs copy-then-compute (8192² → a[::2])", fontweight="bold")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    for bars in (bv, bc):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1,
                    f"{b.get_height():.1f}", ha="center", va="bottom", fontsize=9)
    # annotate the winner of each group
    for i, (v, c) in enumerate(zip(view, copy)):
        win = "view wins" if v < c else "copy wins"
        ax.text(i, max(v, c) * 1.12, win, ha="center", fontweight="bold",
                color=("#d62728" if v < c else "#2ca02c"))
    ax.set_ylim(0, max(view + copy) * 1.25)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"saved {path}")


def main():
    data = collect()
    report(data)
    if "--plot" in sys.argv:
        plot(data, pathlib.Path(__file__).with_name("h5_strided_vs_copy.png"))


if __name__ == "__main__":
    main()
