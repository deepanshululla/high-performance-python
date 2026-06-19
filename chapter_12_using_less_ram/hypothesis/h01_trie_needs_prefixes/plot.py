"""Chart for h01: a trie's RAM win shrinks when its tokens stop sharing prefixes.

Reuses benchmark.run() so the chart shows the numbers the script prints, then saves
chart.png alongside this file.

Run: .venv/bin/python chapter_12_using_less_ram/hypothesis/h01_trie_needs_prefixes/plot.py
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

GOOD, RED, SLOW, OK = COLORS["teal"], COLORS["red"], COLORS["gray"], COLORS["blue"]


def main():
    setup()
    r = benchmark.run()
    kinds = benchmark.KINDS
    import numpy as np
    x = np.arange(len(kinds))

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(8.6, 3.9))

    # Left: set vs trie RAM for each distribution.
    set_mib = [r["by_kind"][k]["set_mib"] for k in kinds]
    trie_mib = [r["by_kind"][k]["trie_mib"] for k in kinds]
    axL.bar(x - 0.2, set_mib, 0.4, color=SLOW, label="set")
    axL.bar(x + 0.2, trie_mib, 0.4, color=GOOD, label="trie (loaded)")
    axL.set_xticks(x)
    axL.set_xticklabels(kinds)
    axL.set_ylabel("peak RSS (MiB)")
    axL.legend()
    axL.set_title("(A) set is flat; trie grows when prefixes vanish")

    # Right: the trie's advantage ratio, prefixed vs random.
    advs = [r["by_kind"][k]["advantage"] for k in kinds]
    bars = axR.bar(kinds, advs, color=[GOOD, RED])
    for b in bars:
        axR.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.02,
                 f"{b.get_height():.0f}x", ha="center", va="bottom", fontsize=10)
    axR.set_ylabel("trie advantage (set MiB / trie MiB)")
    axR.set_title(f"(B) advantage shrinks {r['shrink']:.1f}x without shared prefixes")

    verdict = "CONFIRMED" if r["confirmed"] else "OVERTURNED"
    save(fig, __file__,
         subtitle=f"VERDICT: {verdict} — the trie's RAM win is largely from shared "
                  f"prefixes ({r['pref_adv']:.0f}x prefixed vs {r['rand_adv']:.0f}x random)")


if __name__ == "__main__":
    main()
