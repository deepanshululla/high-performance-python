"""Chapter 4 - Hypothesis: string hashing is O(len), but CPython caches it.

Task: ch4 says a dict's O(1) promise is conditional on the hash being O(1) --
yet hashing a *string* is O(len). The resolution: CPython computes a str's hash
once and caches it inside the object, so only the FIRST hash pays O(len).

Hypothesis:
  - Hashing N *distinct* strings of length L (each hashed for the first time)
    costs ~O(L) per string -- time grows with L.
  - Hashing ONE string N times is flat ~O(1) regardless of L -- the cached hash.

Method: per length L, compare "first hash of each of many distinct strings" vs
"repeat-hash one string".

Run: .venv/bin/python chapter_4/hypothesis/h04_str_hash_caching/benchmark.py
"""
import timeit

M = 20_000  # distinct strings per length


def main():
    print("ns per hash() -- first-time (uncached) vs repeated (cached):\n")
    print("     len L      uncached (distinct)     cached (one obj)     ratio")
    for L in (8, 64, 512, 4096, 32768):
        # Distinct length-L strings: a fixed prefix + zero-padded index keeps len == L.
        prefix = "x" * (L - 8)
        distinct = [f"{prefix}{i:08d}" for i in range(M)]
        one = distinct[0]
        # Force each distinct string to be hashed exactly once (uncached path).
        t_uncached = timeit.timeit("for s in distinct: hash(s)",
                                   globals={"distinct": distinct}, number=1) / M * 1e9
        # The same object: first hash caches it, the rest are free.
        t_cached = timeit.timeit("hash(one)", globals={"one": one}, number=M) / M * 1e9
        print(f"  {L:>8,}     {t_uncached:14.1f}        {t_cached:12.2f}     {t_uncached/t_cached:6.1f}x")

    print("\n-> uncached hashing scales with string length (O(len)); the cached hash")
    print("   is flat and tiny. A dict pays O(len) once per key on insert/first lookup,")
    print("   then every later lookup of that same object is genuinely O(1).")


if __name__ == "__main__":
    main()
