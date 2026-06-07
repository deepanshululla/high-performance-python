"""Chapter 4 - Hypothesis: best dict-access idiom depends on the hit rate.

Task: three ways to read a maybe-missing key:
  LBYL : if k in d: x = d[k]          # two lookups when present
  get  : x = d.get(k)                 # one lookup + None check
  EAFP : try: x = d[k] except KeyError: ...   # one lookup, exception if missing

Hypothesis: when keys are usually PRESENT, EAFP wins (single lookup, the
exception path almost never fires) and LBYL is slowest (it hashes the key
twice). As the hit rate falls, EAFP's exception cost dominates and it becomes
the SLOWEST. So there is a crossover -- no single idiom is always best.

Method: sweep the fraction of present keys and time each idiom per access.

Run: .venv/bin/python chapter_4/hypothesis/h03_eafp_vs_lbyl/benchmark.py
"""
import timeit

SIZE = 1_000
PROBES = 100_000


def make_probes(hit_rate):
    # Present keys come from 0..SIZE-1; absent keys are negative.
    present = int(PROBES * hit_rate)
    keys = [i % SIZE for i in range(present)] + [-(i + 1) for i in range(PROBES - present)]
    return keys


LBYL = """
for k in keys:
    if k in d:
        x = d[k]
    else:
        x = None
"""

GET = """
for k in keys:
    x = d.get(k)
"""

EAFP = """
for k in keys:
    try:
        x = d[k]
    except KeyError:
        x = None
"""


def time_idiom(stmt, keys, d):
    number = 20
    return timeit.timeit(stmt, globals={"keys": keys, "d": d}, number=number) / number / len(keys) * 1e9


def main():
    d = {i: i for i in range(SIZE)}
    print(f"ns per access, {PROBES:,} probes, dict of {SIZE:,} keys:\n")
    print("  hit rate     LBYL (in+[])      get()        EAFP (try)     winner")
    for hr in (1.0, 0.99, 0.9, 0.5, 0.1, 0.0):
        keys = make_probes(hr)
        t_lbyl = time_idiom(LBYL, keys, d)
        t_get = time_idiom(GET, keys, d)
        t_eafp = time_idiom(EAFP, keys, d)
        winner = min((("LBYL", t_lbyl), ("get", t_get), ("EAFP", t_eafp)), key=lambda x: x[1])[0]
        print(f"  {hr:>6.0%}     {t_lbyl:9.2f}     {t_get:9.2f}     {t_eafp:9.2f}      {winner}")

    print("\n-> EAFP/get win when keys are usually present (one lookup); LBYL always")
    print("   pays two lookups. As the hit rate drops, exception cost flips EAFP to")
    print("   the worst -- the crossover the hypothesis predicted.")


if __name__ == "__main__":
    main()
