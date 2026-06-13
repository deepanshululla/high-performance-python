"""H6: elementwise ops don't scale with threads; BLAS matmul does.

HYPOTHESIS: numpy's elementwise ufuncs (a+b) are single-threaded and memory-bandwidth
bound, so adding threads won't help. Matrix multiply (a@b) dispatches to a threaded
BLAS, so it should speed up with more threads.

PREDICTION: a+b time ~unchanged from 1 to N threads; a@b time drops with N.

VERDICT (measured): CONFIRMED, dramatically. a+b is identical at 1 vs 8 threads;
a@b nearly halves. Thread count must be set BEFORE numpy imports its BLAS, so this
script re-launches itself as subprocesses with the thread-count environment variables
set (OMP/OPENBLAS/VECLIB/MKL), then runs one measurement per child.

Run:  .venv/bin/python chapter_6/hypothesis/h6_threading_elementwise_vs_matmul/bench.py
Plot: .venv/bin/python chapter_6/hypothesis/h6_threading_elementwise_vs_matmul/bench.py --plot
"""
import os
import pathlib
import subprocess
import sys
import time

THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
               "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS")
THREAD_COUNTS = (1, 2, 4, 8)
N = 4096


def run_worker():
    """Child mode: measure a+b and a@b once with whatever thread count is in effect."""
    import numpy as np

    def best(fn, reps=5):
        b = float("inf")
        for _ in range(reps):
            t = time.perf_counter()
            fn()
            b = min(b, time.perf_counter() - t)
        return b

    a = np.random.rand(N, N)
    b = np.random.rand(N, N)
    t_add = best(lambda: a + b, reps=10)
    t_mm = best(lambda: a @ b)
    print(f"{t_add * 1e3:.4f} {t_mm * 1e3:.4f}")   # machine-readable: add_ms mm_ms


def measure(threads):
    env = dict(os.environ)
    for var in THREAD_VARS:
        env[var] = str(threads)
    env["H6_WORKER"] = "1"
    out = subprocess.run([sys.executable, __file__], env=env,
                         capture_output=True, text=True, check=True)
    add_ms, mm_ms = (float(x) for x in out.stdout.split())
    return add_ms, mm_ms


def collect():
    threads, add, mm = [], [], []
    for t in THREAD_COUNTS:
        a, m = measure(t)
        threads.append(t)
        add.append(a)
        mm.append(m)
    return {"threads": threads, "add": add, "mm": mm}


def report(data):
    print(f"{N}x{N} float64: elementwise a+b vs matmul a@b, by BLAS thread count.")
    print("(each row is a fresh subprocess with the thread env vars pinned)\n")
    print(f"{'threads':>8}  {'a+b (elementwise)':>18}  {'a@b (matmul)':>14}")
    for t, a, m in zip(data["threads"], data["add"], data["mm"]):
        print(f"{t:>8}  {a:15.2f} ms  {m:11.1f} ms")
    a1, a8 = data["add"][0], data["add"][-1]
    m1, m8 = data["mm"][0], data["mm"][-1]
    print(f"\n  a+b: 1 -> 8 threads = {a1 / a8:.2f}x  (essentially flat: doesn't thread)")
    print(f"  a@b: 1 -> 8 threads = {m1 / m8:.2f}x  (BLAS parallelizes the matmul)")
    print("\n-> elementwise work is memory-bandwidth bound and single-threaded in numpy;")
    print("   matmul is compute-bound and farmed out to a multithreaded BLAS.")


def plot(data, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    th = data["threads"]
    # normalize each series to its 1-thread time -> "speedup vs 1 thread"
    add_sp = [data["add"][0] / v for v in data["add"]]
    mm_sp = [data["mm"][0] / v for v in data["mm"]]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    ax.plot(th, add_sp, "o-", color="#1f77b4", label="a+b (elementwise)")
    ax.plot(th, mm_sp, "s-", color="#d62728", label="a@b (matmul)")
    ax.plot(th, th, ":", color="gray", label="ideal linear")
    ax.set_xticks(th)
    ax.set_xlabel("BLAS threads")
    ax.set_ylabel("speedup vs 1 thread")
    ax.set_title("Only matmul scales with threads")
    ax.legend()
    ax.grid(True, alpha=0.3)

    x = range(len(th))
    w = 0.38
    ax2.bar([i - w / 2 for i in x], data["add"], w, color="#1f77b4", label="a+b")
    ax2.bar([i + w / 2 for i in x], data["mm"], w, color="#d62728", label="a@b")
    ax2.set_yscale("log")
    ax2.set_xticks(list(x))
    ax2.set_xticklabels([f"{t}t" for t in th])
    ax2.set_ylabel("time (ms, log)")
    ax2.set_title("Absolute time (note the scale gap)")
    ax2.legend()
    ax2.grid(True, axis="y", alpha=0.3)

    fig.suptitle(f"H6 — elementwise doesn't thread; matmul does ({N}² float64)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"saved {path}")


def main():
    if os.environ.get("H6_WORKER"):
        run_worker()
        return
    data = collect()
    report(data)
    if "--plot" in sys.argv:
        plot(data, pathlib.Path(__file__).with_name("h6_threading.png"))


if __name__ == "__main__":
    main()
