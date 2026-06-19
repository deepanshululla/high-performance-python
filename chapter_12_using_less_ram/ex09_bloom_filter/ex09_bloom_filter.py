"""ex09 — Bloom filters: "have I seen this?" with a controllable error rate.

A Bloom filter answers set membership in a fixed bit array. To add an item it hashes
it k ways and sets those k bits; to test an item it checks whether all k of its bits are
set. This gives a one-sided guarantee: if any bit is unset the item is *definitely* new
(no false negatives), but if all k happen to be set the item *might* be new — a false
positive from bits other items turned on. The bit-array size and k are chosen from the
capacity and the target false-positive rate, so you dial in the error you can tolerate.

We confirm the no-false-negatives guarantee, measure the empirical false-positive rate
against the configured target, and watch what the book warns about: a Bloom filter is
sized for a capacity, and pushing past it makes the error balloon as the array fills.
That motivates the scaling Bloom filter, which chains tightening-error sub-filters so it
keeps its error bound as it grows — which we measure against a plain filter overfilled.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _pds

from _pds import BloomFilter, ScalingBloomFilter  # noqa: E402

NONMEMBER_BASE = 1_000_000_000   # query keys guaranteed never added


def sizing(capacity=50_000, error=0.0005):
    """Reproduce the book's sizing: 50k items at 0.05% -> ~791,015 bits, 11 hashes."""
    bf = BloomFilter(capacity, error)
    return {"capacity": capacity, "error": error,
            "num_bits": bf.num_bits, "num_hashes": bf.num_hashes,
            "num_bytes": bf.num_bytes()}


def _empirical_fp(bf, n_queries=50_000):
    """Fraction of never-added keys the filter wrongly reports as present."""
    fp = sum(1 for i in range(NONMEMBER_BASE, NONMEMBER_BASE + n_queries)
             if str(i) in bf)
    return fp / n_queries


def no_false_negatives(capacity=50_000, error=0.005):
    """Every added member must test present — the Bloom filter's hard guarantee."""
    bf = BloomFilter(capacity, error)
    for i in range(capacity):
        bf.add(str(i))
    found = sum(1 for i in range(capacity) if str(i) in bf)
    return found / capacity


def fp_vs_fill(capacity=50_000, error=0.005, fills=(0.25, 0.5, 0.75, 1.0, 1.5, 2.0)):
    """Build a fixed-size filter, fill it to each fraction of capacity, measure FP."""
    rows = []
    for fill in fills:
        bf = BloomFilter(capacity, error)
        n_added = int(capacity * fill)
        for i in range(n_added):
            bf.add(str(i))
        rows.append({"fill": fill, "n_added": n_added,
                     "fp_rate": _empirical_fp(bf)})
    return rows


def scaling_vs_plain(capacity=10_000, error=0.005, overfill=5):
    """Overfill a plain filter vs a scaling filter; the scaling one holds its error."""
    n = capacity * overfill
    plain = BloomFilter(capacity, error)
    scaling = ScalingBloomFilter(capacity, error)
    for i in range(n):
        plain.add(str(i))
        scaling.add(str(i))
    return {
        "target": error, "n_added": n, "capacity": capacity,
        "plain_fp": _empirical_fp(plain),
        "scaling_fp": _empirical_fp(scaling),
        "plain_bytes": plain.num_bytes(), "scaling_bytes": scaling.num_bytes(),
    }


def measure():
    return {
        "sizing": sizing(),
        "no_false_negatives": no_false_negatives(),
        "fp_vs_fill": fp_vs_fill(),
        "scaling": scaling_vs_plain(),
    }


def main():
    m = measure()
    s = m["sizing"]
    print(f"Sizing a Bloom filter for {s['capacity']:,} items at {s['error']:.2%} error:")
    print(f"  needs {s['num_bits']:,} bits ({s['num_bytes']:,} bytes) and "
          f"{s['num_hashes']} hash functions")
    print(f"  (independent of how big each item is — only the count matters)\n")

    print(f"No false negatives: {m['no_false_negatives']:.1%} of added members found "
          f"(must be 100%).\n")

    print("False-positive rate vs how full the filter is (target 0.5%):")
    print(f"  {'fill':>6} {'added':>8} {'FP rate':>10}")
    for r in m["fp_vs_fill"]:
        flag = "" if r["fill"] <= 1.0 else "  <- overfilled"
        print(f"  {r['fill']:6.2f} {r['n_added']:8,} {r['fp_rate']:9.2%}{flag}")

    sc = m["scaling"]
    print(f"\nOverfilling {sc['n_added']:,} items into a {sc['capacity']:,}-capacity "
          f"filter (target {sc['target']:.2%}):")
    print(f"  plain filter   FP {sc['plain_fp']:6.2%}  ({sc['plain_bytes']:,} bytes)")
    print(f"  scaling filter FP {sc['scaling_fp']:6.2%}  ({sc['scaling_bytes']:,} bytes)")
    print("  the plain filter saturates; the scaling filter adds sub-filters to hold "
          "its error bound.")


if __name__ == "__main__":
    main()
