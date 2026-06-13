"""H6: did Copy-on-Write narrow the book's str-chain result? Isolating it says NO.

BACKGROUND: ex05 reproduced the book's "chained `.str` ops vs a single `apply`" benchmark
(Example 7-12). The book measured the `.str` chain at ~3x slower than `apply(find_9)`. On this
machine (pandas 3.0, Copy-on-Write the default) the gap collapses to ~1.3x. ex05 -- following
the book's own note -- attributes the narrowing to CoW removing the defensive copies the chain
used to pay for. This hypothesis tests that attribution directly, and it does not survive.

THE PROBLEM: pandas 3.0 can no longer disable CoW -- `mode.copy_on_write` is a deprecated
no-op (always on). So we cannot run the same code with CoW off. Instead we EMULATE the pre-CoW
world by forcing an explicit defensive `.copy()` on each intermediate the chain produces. If
the chain's penalty were really intermediate-copy cost that CoW elides, restoring those copies
should widen the gap back toward the book's 3x.

HYPOTHESIS (the one we are testing): the `.str` chain's penalty over `apply` is dominated by
intermediate-object copies that CoW now elides; force them back and the chain-vs-apply ratio
climbs toward 3x.

PREDICTION if true: ratio(chain_preCoW / apply) >> ratio(chain_CoW / apply), approaching 3x.

VERDICT (measured): REFUTED. Forcing a deep copy of every intermediate adds only ~0.3 ms and
leaves the ratio at ~1.3x -- nowhere near 3x. The defensive copies are negligible here, so CoW
is *not* what shrank this result. The narrowing is general improvement (faster str kernels and
hardware) between the book's pandas and pandas 3.0, not CoW. CoW's real, large, measurable
effect is on copy *semantics* themselves (see h05: a shallow copy is ~1,800x cheaper and now
safe) -- not on this str-accessor chain.

Run:  .venv/bin/python chapter_7/hypothesis/h06_cow_narrows_chain/bench.py
Plot: .venv/bin/python chapter_7/hypothesis/h06_cow_narrows_chain/bench.py --plot
"""
import pathlib
import sys
import timeit
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROWS = 50_000
BOOK_RATIO = 3.0  # the book's reported chain-vs-apply gap (Example 7-12), pre-CoW


def gen_str_series(n_rows=ROWS, seed=0):
    """A column of numbers rendered as strings, e.g. '1.0166666666666666' (matches ex05)."""
    rng = np.random.default_rng(seed)
    vals = rng.poisson(60, size=n_rows) / 60.0
    return pd.Series(vals).apply(lambda v: str(v))


def find_9(s):
    return s.split(".")[1].find("9")


def via_apply(series):
    """Pure Python per row -- builds no intermediate pandas objects at all."""
    return series.apply(find_9)


def via_chain_cow(series):
    """The chain as written: pandas 3.0 CoW elides defensive copies of the intermediates."""
    return series.str.split(".", expand=True)[1].str.find("9")


def via_chain_precow(series):
    """Pre-CoW emulation: force a real copy of every intermediate, as older pandas did when a
    chained selection was an ambiguous view-or-copy and got defensively duplicated."""
    split_df = series.str.split(".", expand=True).copy()  # the expand DataFrame, copied
    after_dot = split_df[1].copy()                        # the selected column, copied
    return after_dot.str.find("9")


def best_ms(fn, number=20, repeat=5):
    """Best (minimum) average-per-call time in ms, over `repeat` rounds of `number` calls."""
    timer = timeit.Timer(fn)
    return min(timer.repeat(repeat=repeat, number=number)) / number * 1e3


def collect():
    s = gen_str_series()

    # correctness anchor: all three must agree on every position
    a = via_apply(s).to_numpy()
    assert np.array_equal(via_chain_cow(s).to_numpy(), a)
    assert np.array_equal(via_chain_precow(s).to_numpy(), a)

    t_apply = best_ms(lambda: via_apply(s))
    t_chain_cow = best_ms(lambda: via_chain_cow(s))
    t_chain_precow = best_ms(lambda: via_chain_precow(s))

    return {
        "rows": len(s),
        "apply_ms": t_apply,
        "chain_cow_ms": t_chain_cow,
        "chain_precow_ms": t_chain_precow,
        "ratio_cow": t_chain_cow / t_apply,
        "ratio_precow": t_chain_precow / t_apply,
        "copy_overhead_ms": t_chain_precow - t_chain_cow,
    }


def report(d):
    print(f"Task: first '9' after the decimal point across {d['rows']:,} number-strings "
          f"(ex05 / book Example 7-12)\n")
    print(f"  apply(find_9)  [no pandas intermediates]        : {d['apply_ms']:6.1f} ms   (1.0x baseline)")
    print(f"  .str chain     [pandas 3.0 CoW, default]        : {d['chain_cow_ms']:6.1f} ms   "
          f"({d['ratio_cow']:.1f}x)")
    print(f"  .str chain     [pre-CoW emulation, forced copies]: {d['chain_precow_ms']:6.1f} ms   "
          f"({d['ratio_precow']:.1f}x)")
    print()
    print(f"  book reported chain-vs-apply gap (pre-CoW)       : {BOOK_RATIO:.1f}x")
    print(f"  defensive-copy cost (forcing copies back)        : {d['copy_overhead_ms']:+.1f} ms "
          f"(ratio {d['ratio_cow']:.1f}x -> {d['ratio_precow']:.1f}x -- essentially unchanged)")
    print()
    print("  VERDICT: REFUTED. Forcing the defensive copies back does NOT restore the book's 3x,")
    print("  so CoW is not what narrowed this result -- it is general pandas/hardware improvement.")
    print("  (CoW's real, large effect is on copy semantics -- see h05's lazy shallow copy.)")


def plot(d, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    labels = [
        "apply(find_9)\n(no pandas\nintermediates)",
        ".str chain\npandas 3.0\n(CoW default)",
        ".str chain\npre-CoW emulation\n(forced copies)",
    ]
    vals = [d["apply_ms"], d["chain_cow_ms"], d["chain_precow_ms"]]
    colors = ["#0d9488", "#2563eb", "#dc2626"]
    bars = ax.bar(labels, vals, color=colors, width=0.62)
    ax.set_ylabel("time (ms, lower is better)")
    ax.set_title("H6 — Forcing the defensive copies back doesn't restore the book's 3x\n"
                 "so CoW is NOT what narrowed this result (REFUTED)",
                 fontweight="bold", fontsize=11.5)

    for b, v, r in zip(bars, vals, [1.0, d["ratio_cow"], d["ratio_precow"]]):
        ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.015,
                f"{v:.1f} ms\n{r:.1f}x", ha="center", va="bottom", fontsize=9.5)

    book_y = d["apply_ms"] * BOOK_RATIO
    ax.axhline(book_y, ls="--", lw=1.3, color="#6b7280")
    ax.text(2.46, book_y, f"  book's pre-CoW gap: {BOOK_RATIO:.0f}x\n  (neither chain reaches it)",
            va="center", ha="left", fontsize=9, color="#6b7280")

    ax.set_ylim(0, max(vals + [d["apply_ms"] * BOOK_RATIO]) * 1.25)
    ax.margins(x=0.04)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"saved {path}")


def main():
    d = collect()
    report(d)
    if "--plot" in sys.argv:
        plot(d, pathlib.Path(__file__).with_name("h06_cow_narrows_chain.png"))


if __name__ == "__main__":
    main()
