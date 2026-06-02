"""Chapter 4 - Exercise 6: good hash vs bad hash vs list (Example 4-9).

Task: build a set over all 676 two-letter strings three ways -- BadHash
(returns 42), GoodHash (perfect two-letter hash), and a plain list -- then time
membership for "zz".

Takeaway: with BadHash every key collides into one probe chain, so membership
walks all 676 entries plus per-probe hash/eq overhead -- slower even than the
plain list's bare linear scan. A degenerate hash turns O(1) back into O(n).

Run: .venv/bin/python chapter_4/ex06_good_bad_hash.py
"""
import string
import sys
import timeit


class BadHash(str):
    def __hash__(self):
        return 42


class GoodHash(str):
    def __hash__(self):
        # optimized twoletter_hash: distinct value per lowercase pair
        return ord(self[1]) + 26 * ord(self[0]) - 2619


def main():
    bad, good, lst = set(), set(), []
    for a in string.ascii_lowercase:
        for b in string.ascii_lowercase:
            bad.add(BadHash(a + b))
            good.add(GoodHash(a + b))
            lst.append(a + b)

    g = {"bad": bad, "good": good, "lst": lst, "BadHash": BadHash, "GoodHash": GoodHash}
    t_bad = min(timeit.repeat("BadHash('zz') in bad", globals=g, number=1_000_000))
    t_good = min(timeit.repeat("GoodHash('zz') in good", globals=g, number=1_000_000))
    t_list = min(timeit.repeat("'zz' in lst", globals=g, number=1_000_000))

    print("Time (1,000,000 membership tests of 'zz'):")
    print(f"  good_dict: {t_good:7.4f}s   (baseline)")
    print(f"  list:      {t_list:7.4f}s   ({t_list / t_good:5.1f}x slower than good)")
    print(f"  bad_dict:  {t_bad:7.4f}s   ({t_bad / t_good:5.1f}x slower than good)")
    print("  -> bad hash is even slower than a plain list scan")

    # Memory: all three hold 676 entries -- the cost of a bad hash is purely TIME,
    # not space. The sets are the same size whether the hash is good or terrible.
    print(f"\nMemory (676 entries): good_set {sys.getsizeof(good)} B, "
          f"bad_set {sys.getsizeof(bad)} B, list {sys.getsizeof(lst)} B")
    print("  -> a degenerate hash wrecks lookup TIME while occupying identical space")


if __name__ == "__main__":
    main()
