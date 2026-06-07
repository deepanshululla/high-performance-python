"""H3: numexpr's advantage over numpy grows with EXPRESSION LENGTH.

HYPOTHESIS: numexpr wins by fusing a whole expression into one cache-aware pass,
eliminating the temporaries numpy materializes between each operation. So the more
operations in the expression (the more temporaries avoided), the bigger numexpr's
edge -- at a FIXED array size.

PREDICTION: speedup(numexpr/numpy) increases monotonically as the expression grows.

VERDICT (measured): CONFIRMED, cleanly monotonic. This qualifies ex11: numexpr's
win is not only about grid-vs-cache size -- it also scales with how many
intermediate arrays numpy is forced to allocate and re-traverse.

Run:  .venv/bin/python chapter_6/hypothesis/h3_numexpr_expression_length/bench.py
Plot: .venv/bin/python chapter_6/hypothesis/h3_numexpr_expression_length/bench.py --plot
"""
import pathlib
import sys
import time

import numexpr as ne
import numpy as np

N = 2048


def best(fn, reps=5):
    best_t = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        best_t = min(best_t, time.perf_counter() - t)
    return best_t


def collect():
    a, b, c, d, e = (np.random.rand(N, N) for _ in range(5))
    env = {"a": a, "b": b, "c": c, "d": d, "e": e}   # ne.evaluate resolves names from
    # the caller frame, which a timing closure hides -- so pass them explicitly.
    cases = [
        ("a+b", lambda: a + b),
        ("a*b+c", lambda: a * b + c),
        ("a*b+c*d-e", lambda: a * b + c * d - e),
        ("a*b+c*d-e+a*c", lambda: a * b + c * d - e + a * c),
    ]
    exprs, ops, np_ms, ne_ms = [], [], [], []
    for expr, npfn in cases:
        assert np.allclose(npfn(), ne.evaluate(expr, local_dict=env)), expr
        exprs.append(expr)
        ops.append(sum(expr.count(o) for o in "+-*"))
        np_ms.append(best(npfn) * 1e3)
        ne_ms.append(best(lambda expr=expr: ne.evaluate(expr, local_dict=env)) * 1e3)
    return {"exprs": exprs, "ops": ops, "numpy": np_ms, "numexpr": ne_ms,
            "speedup": [n / x for n, x in zip(np_ms, ne_ms)], "threads": ne.nthreads}


def report(data):
    print(f"Fixed array size {N}x{N}; varying expression length "
          f"(numexpr threads={data['threads']}):\n")
    print(f"{'expression':<16}{'ops':>4}  {'numpy':>9}  {'numexpr':>9}  speedup")
    for expr, ops, tn, tx, sp in zip(data["exprs"], data["ops"], data["numpy"],
                                     data["numexpr"], data["speedup"]):
        print(f"{expr:<16}{ops:>4}  {tn:6.2f} ms  {tx:6.2f} ms  {sp:.2f}x")
    print("\n-> numexpr's edge grows with expression length: each extra operation is")
    print("   another temporary numpy must allocate and re-walk, but that numexpr fuses")
    print("   into its single cache-aware pass. Complexity matters, not just size (ex11).")


def plot(data, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = range(len(data["exprs"]))
    fig, ax = plt.subplots(figsize=(9, 4.6))
    w = 0.38
    ax.bar([i - w / 2 for i in x], data["numpy"], w, color="#1f77b4", label="numpy")
    ax.bar([i + w / 2 for i in x], data["numexpr"], w, color="#ff7f0e", label="numexpr")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{e}\n({o} ops)" for e, o in zip(data["exprs"], data["ops"])], fontsize=9)
    ax.set_ylabel("time (ms)")
    ax.set_title(f"H3 — numexpr's edge grows with expression length ({N}² float64)",
                 fontweight="bold")
    ax.legend(loc="upper left")
    ax.grid(True, axis="y", alpha=0.3)

    ax2 = ax.twinx()
    ax2.plot(list(x), data["speedup"], "D-", color="#2ca02c", label="speedup")
    ax2.set_ylabel("numexpr speedup (×)", color="#2ca02c")
    ax2.tick_params(axis="y", labelcolor="#2ca02c")
    ax2.set_ylim(0, max(data["speedup"]) * 1.3)
    for xi, sp in zip(x, data["speedup"]):
        ax2.text(xi, sp + 0.08, f"{sp:.2f}×", ha="center", color="#2ca02c", fontsize=10, fontweight="bold")

    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"saved {path}")


def main():
    data = collect()
    report(data)
    if "--plot" in sys.argv:
        plot(data, pathlib.Path(__file__).with_name("h3_numexpr_expression_length.png"))


if __name__ == "__main__":
    main()
