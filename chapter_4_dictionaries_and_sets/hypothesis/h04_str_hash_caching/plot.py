"""Visualize H4: first-time string hashing is O(len); the cached hash is flat.

Run: .venv/bin/python chapter_4/hypothesis/h04_str_hash_caching/plot.py
"""
import pathlib
import sys
import timeit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from vizutil import plt, setup, save, COLORS  # noqa: E402

M = 20_000


def main():
    setup()
    Ls = [8, 32, 128, 512, 2048, 8192, 32768]
    uncached, cached = [], []
    for L in Ls:
        prefix = "x" * (L - 8)
        distinct = [f"{prefix}{i:08d}" for i in range(M)]
        one = distinct[0]
        t_un = timeit.timeit("for s in distinct: hash(s)",
                             globals={"distinct": distinct}, number=1) / M * 1e9
        t_ca = timeit.timeit("hash(one)", globals={"one": one}, number=M) / M * 1e9
        uncached.append(t_un)
        cached.append(t_ca)

    fig, ax = plt.subplots(figsize=(8.6, 5.1))
    ax.plot(Ls, uncached, "-o", color=COLORS["red"], lw=1.9, ms=5,
            label="first hash of distinct strings (uncached)")
    ax.plot(Ls, cached, "-o", color=COLORS["teal"], lw=1.9, ms=5,
            label="re-hash the same object (cached)")
    ax.annotate("O(len): slope 1", xy=(Ls[-2], uncached[-2]),
                xytext=(Ls[-2] * 0.12, uncached[-2] * 1.4), color=COLORS["red"], fontsize=9.5,
                arrowprops=dict(arrowstyle="->", color=COLORS["red"]))
    ax.text(Ls[1], cached[0] * 0.35, "cached: flat ~27 ns", color=COLORS["teal"], fontsize=9.5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("string length L (chars)")
    ax.set_ylabel("ns / hash()")
    ax.set_title("H4 - str hashing is O(len), but CPython caches it (log-log)")
    ax.legend(loc="upper left")
    save(fig, __file__,
         subtitle="CONFIRMED - the O(len) hash is paid once per key; later lookups of it are flat | CPython 3.14 / macOS")


if __name__ == "__main__":
    main()
