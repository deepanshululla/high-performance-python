"""Chart for h01: fork vs spawn — startup cost and global-state inheritance.

Reuses benchmark.run() so the chart shows the same numbers the script prints, then
saves chart.png alongside this file.

Run: .venv/bin/python chapter_10_multiprocessing/hypothesis/h01_fork_vs_spawn/plot.py
"""
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> vizutil

from vizutil import plt, setup, save, COLORS  # noqa: E402

spec = importlib.util.spec_from_file_location("h01_benchmark", HERE / "benchmark.py")
benchmark = importlib.util.module_from_spec(spec)
sys.modules["h01_benchmark"] = benchmark
spec.loader.exec_module(benchmark)

GOOD, RED, SLOW = COLORS["teal"], COLORS["red"], COLORS["gray"]


def main():
    setup()
    r = benchmark.run()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.4, 3.8))

    # Left: pool startup cost (ms).
    methods = benchmark.METHODS
    ms = [r["startup"][m] * 1000 for m in methods]
    bars = axL.bar(methods, ms, color=[GOOD, RED])
    for b in bars:
        axL.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.02,
                 f"{b.get_height():.0f} ms", ha="center", va="bottom", fontsize=9)
    axL.set_ylabel("pool startup (ms)")
    axL.set_title(f"(A) startup: spawn {r['spawn_over_fork']:.1f}x slower")

    # Right: what the child inherits (42 = parent's mutation, 0 = re-imported default).
    seen = [r["inherit"][m] for m in methods]
    colors = [GOOD if v == 42 else RED for v in seen]
    bars = axR.bar(methods, seen, color=colors)
    axR.axhline(42, color=SLOW, ls="--", lw=1, label="parent set it to 42")
    for b, v in zip(bars, seen):
        tag = "inherited" if v == 42 else "LOST"
        axR.text(b.get_x() + b.get_width() / 2, max(v, 1) + 1,
                 f"{v}\n{tag}", ha="center", va="bottom", fontsize=8)
    axR.set_ylim(0, 50)
    axR.set_ylabel("value child sees in shared global")
    axR.legend(fontsize=8)
    axR.set_title("(B) global-state inheritance")

    fig.suptitle("h01 fork vs spawn — the book assumes fork; macOS gives spawn",
                 fontsize=12, fontweight="bold")
    save(fig, __file__,
         subtitle=f"VERDICT: {r['verdict']} — spawn is slower to start AND loses "
                  "the parent's globals; every shared-state exercise forces fork.")


if __name__ == "__main__":
    main()
