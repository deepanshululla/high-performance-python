"""Visualize H2: set-lookup time degrades smoothly as hash entropy drops.

Run: .venv/bin/python chapter_4/hypothesis/h02_collision_entropy_curve/plot.py
"""
import pathlib
import sys
import timeit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import benchmark as B  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402


def main():
    setup()
    keys = [f"key-{i:06d}" for i in range(B.N)]
    bits_list = [64, 20, 16, 12, 10, 8, 6, 4, 2, 1, 0]
    buckets, ns = [], []
    for bits in bits_list:
        Cls = B.make_masked_class(bits)
        items = [Cls(k) for k in keys]
        s = set(items)
        distinct = len({hash(x) for x in items})
        number = 3 if bits <= 6 else 30
        t = timeit.timeit("for k in items: k in s",
                          globals={"items": items, "s": s}, number=number)
        buckets.append(distinct)
        ns.append(t / number / B.N * 1e9)

    fig, ax = plt.subplots(figsize=(8.6, 5.1))
    ax.plot(buckets, ns, "-o", color=COLORS["violet"], lw=1.9, ms=6)
    ax.axvline(B.N, color=COLORS["gray"], ls="--", lw=1)
    ax.text(B.N * 1.15, min(ns) * 1.1, f"buckets = keys\n({B.N:,})", color=COLORS["gray"],
            fontsize=9.5)
    ax.annotate("plateau: ~O(1)\n(a bucket per key)", xy=(buckets[1], ns[1]),
                xytext=(buckets[1] * 0.06, ns[1] * 2.4), color=COLORS["teal"], fontsize=9.5,
                arrowprops=dict(arrowstyle="->", color=COLORS["teal"]))
    ax.annotate("all collide: ~O(n)\n(ex06's bad hash)", xy=(buckets[-1], ns[-1]),
                xytext=(buckets[-1] * 2, ns[-1] * 0.5), color=COLORS["red"], fontsize=9.5,
                arrowprops=dict(arrowstyle="->", color=COLORS["red"]))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("distinct hash buckets  (<- more entropy   |   less entropy ->)")
    ax.set_ylabel("ns / membership test")
    ax.set_title(f"H2 - Lookup cost vs hash entropy ({B.N:,} keys, log-log)")
    ax.invert_xaxis()  # entropy decreases left-to-right (matches the degradation story)
    save(fig, __file__,
         subtitle="CONFIRMED - smooth slide from O(1) to O(n) as buckets collapse below key count | CPython 3.14 / macOS")


if __name__ == "__main__":
    main()
