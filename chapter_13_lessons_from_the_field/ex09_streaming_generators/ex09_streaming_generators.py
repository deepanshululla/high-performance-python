"""ex09 — stream your data: a generator holds one item, a list holds all of them.

Radim Řehůřek built gensim around one habit: "Let your input be accessed and processed one
data point at a time, for a small, constant memory footprint... The Python language supports
this pattern very naturally and elegantly, with its built-in generators — a truly beautiful
problem-tech match. Avoid committing to algorithms and tools that load everything into RAM,
unless you know your data will always remain small." word2vec trains on ~100 billion words;
that obviously can't sit in memory, so the corpus is *streamed* sentence by sentence and the
model updated incrementally.

We reproduce the memory shape of that choice. The task is a word2vec-flavoured reduction:
compute the mean of N embedding-sized vectors. Two ways, anchored to the identical result:

  * materialised — build a Python list of all N vectors, then reduce it. Peak memory holds
                   the whole corpus at once.
  * streamed     — a generator yields one vector at a time into a running accumulator. Peak
                   memory holds a single vector, regardless of N.

We measure peak resident memory (in a fresh process each, via `_rss.py`) and wall-clock. The
point is the memory curve: the list's footprint grows with N; the generator's is flat.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _rss

import numpy as np  # noqa: E402

from _rss import peak_rss_mib  # noqa: E402
from perf import time_s  # noqa: E402

N_VECTORS = 500_000
DIM = 50


def make_vector(i):
    """A deterministic 'embedding' for item i — cheap to compute, so memory is the variable."""
    return np.arange(DIM, dtype=np.float64) + i


def mean_materialised(n=N_VECTORS):
    """Build the whole corpus as a list first, then reduce it (holds all N vectors)."""
    corpus = [make_vector(i) for i in range(n)]      # the entire dataset, live in RAM
    return np.sum(corpus, axis=0) / n


def mean_streamed(n=N_VECTORS):
    """Stream one vector at a time into an accumulator (holds a single vector)."""
    acc = np.zeros(DIM)
    for i in range(n):                               # a generator-style pull, one at a time
        acc += make_vector(i)
    return acc / n


def measure():
    ref = mean_streamed(N_VECTORS)
    assert np.allclose(ref, mean_materialised(N_VECTORS)), "the two paths disagree!"

    mem_mat = peak_rss_mib(mean_materialised, N_VECTORS)
    mem_str = peak_rss_mib(mean_streamed, N_VECTORS)
    t_mat = time_s(lambda: mean_materialised(N_VECTORS), number=1, repeat=2)
    t_str = time_s(lambda: mean_streamed(N_VECTORS), number=1, repeat=2)
    corpus_mib = N_VECTORS * DIM * 8 / 1024**2
    return {
        "n": N_VECTORS, "dim": DIM, "corpus_mib": corpus_mib,
        "materialised": {"rss_mib": mem_mat, "s": t_mat},
        "streamed": {"rss_mib": mem_str, "s": t_str},
        "mem_ratio": mem_mat / max(mem_str, 0.1),
    }


def main():
    m = measure()
    print(f"mean of {m['n']:,} vectors of dim {m['dim']} "
          f"(the raw vectors are ~{m['corpus_mib']:.0f} MiB):\n")
    for name in ("materialised", "streamed"):
        d = m[name]
        print(f"  {name:13}: peak RSS {d['rss_mib']:7.1f} MiB   {d['s']*1e3:7.1f} ms")
    print(f"\n  the list holds the whole corpus; the generator holds one vector "
          f"({m['mem_ratio']:.0f}x less peak RAM)")


if __name__ == "__main__":
    main()
