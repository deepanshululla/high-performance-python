"""Chart for h01: tuning vs algorithmic change on the keyword-matching task.

Reuses benchmark.run() so the chart shows the numbers the script prints, then saves chart.png
alongside this file.

Run: .venv/bin/python chapter_13_lessons_from_the_field/hypothesis/h01_reframe_vs_microopt/plot.py
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

GRAY, RED, TEAL, BLUE = COLORS["gray"], COLORS["red"], COLORS["teal"], COLORS["blue"]


def main():
    setup()
    r = benchmark.run()
    labels = benchmark.LABELS
    kind = benchmark.KIND
    speedups = [r["speedups"][k] for k in labels]
    palette = {"baseline": GRAY, "micro-opt": RED, "algorithmic": TEAL}
    colors = [palette[kind[k]] for k in labels]

    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    x = range(len(labels))
    bars = ax.bar(x, speedups, color=colors)
    ax.set_yscale("log")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{k}\n({kind[k]})" for k in labels], fontsize=9)
    ax.set_ylabel("speedup vs naive (log)")
    for b, s in zip(bars, speedups):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.15,
                f"{s:,.0f}x" if s >= 10 else f"{s:.1f}x", ha="center", va="bottom", fontsize=9)
    # The 10x line separating Rawlinson's two bands.
    ax.axhline(10, color=BLUE, ls="--", lw=1.2)
    ax.text(len(labels) - 0.5, 11, "10x — the band boundary", ha="right", va="bottom",
            fontsize=8, color=BLUE)
    ax.set_title("h01 — tuning gives ~1x; the order-of-magnitude wins are all algorithmic")

    sp = r["speedups"]
    verdict = "CONFIRMED" if r["confirmed"] else "OVERTURNED"
    save(fig, __file__, subtitle=(
        f"VERDICT: {verdict} — genuine tuning {sp['tuned']:.1f}x (no gain); "
        f"combined-regex {sp['combined']:,.0f}x and Aho-Corasick {sp['reframe']:,.0f}x both change "
        f"the algorithm. The one-liner is algorithmic in disguise."))


if __name__ == "__main__":
    main()
