"""Visualize H3: `x in list` time is linear in the target's position.

Run: .venv/bin/python chapter_3/hypothesis/h03_membership_position/plot.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import benchmark as B  # noqa: E402
from vizutil import plt, setup, save, COLORS  # noqa: E402


def main():
    setup()
    Ns = [1_000, 10_000, 100_000, 1_000_000]
    series = {
        "front (x=0)": (COLORS["teal"], lambda _N: 0),
        "middle (x=N/2)": (COLORS["blue"], lambda N: N // 2),
        "end (x=N-1)": (COLORS["amber"], lambda N: N - 1),
        "absent (x=-1)": (COLORS["red"], lambda _N: -1),
    }

    fig, ax = plt.subplots(figsize=(8.2, 5))
    for label, (color, target_of) in series.items():
        ys = []
        for N in Ns:
            data = list(range(N))
            number = max(10, 5_000_000 // N)
            reps = number * 50 if "front" in label else number
            ys.append(B.time_in(data, target_of(N), reps))
        ax.plot(Ns, ys, "-o", color=color, lw=1.8, ms=5, label=label)

    # Reference O(n) slope.
    ax.plot(Ns, [Ns[i] / Ns[-1] * 7000 for i in range(len(Ns))], "--",
            color=COLORS["gray"], lw=1, label="O(n) reference")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("list size N")
    ax.set_ylabel("microseconds / lookup")
    ax.set_title("H3 - `x in list` cost vs target position (log-log)")
    ax.legend(loc="upper left")
    ax.text(1.2e4, 0.02, "front: flat ~O(1)", color=COLORS["teal"], fontsize=9.5)
    ax.text(1.5e3, 1500, "end / absent: slope 1 = O(n)\n(10x N -> 10x time)",
            color=COLORS["red"], fontsize=9.5)
    save(fig, __file__,
         subtitle="CONFIRMED - membership is a linear scan; the miss is worst-case | CPython 3.14 / macOS")


if __name__ == "__main__":
    main()
