# Chapter 3 — Lists and Tuples: Practice Exercises

Runnable drills for *High Performance Python (3rd ed.)*, Chapter 3. Each script is
self-contained: read the docstring for the task, try it yourself, then run the
reference implementation. Every script self-reports **time** (`timeit`) and
**memory** (`tracemalloc` peak, via the shared `perf.py` helper).

All numbers below are from **CPython 3.14.0 / macOS** — yours will differ, and
that variance is itself part of the lesson. tracemalloc peaks measure Python-heap
allocations (smaller than RSS) but isolate the allocation each exercise cares about.

```bash
.venv/bin/python chapter_3/ex02_binary_search.py
```

**Core idea:** position *is* address. Contiguous, uniform-stride memory gives `O(1)`
indexing and `O(log n)` search on sorted data — at the cost of an eventual `O(n)`
resize-and-copy that lists amortize via overallocation. Tuples drop the headroom
and bookkeeping in exchange for immutability.

---

## `ex02_binary_search.py`

`O(log n)` binary search vs the `O(n)` linear scan that `list.index` performs.

- **Time** (1,000,000 elements, worst-case miss): `linear_search` **19,494 µs** vs
  `binary_search` **0.79 µs** → **~24,800× faster**.
- **Memory:** both `O(1)` auxiliary — no copies. The entire win is fewer comparisons
  (~20 probes vs scanning all 1,000,000), not space.

**Learning:** order is what lets binary search throw away half the range per step.
`list.index` has no order to exploit, so it stays linear.

---

## `ex03_bisect_vs_dict.py`

A single `bisect` lookup vs building a `set` then querying — time *and* the memory price of `O(1)`.

- **Time:** `bisect` lookup **0.197 µs**; build a set + 1 query **57.6 ms**
  (build is **~293,000×** a lookup); prebuilt set membership **0.028 µs** (~7× faster than bisect).
- **Memory** (1,000,000 ints): sorted list **7.6 MB** vs `set` **32.0 MB** → the hash
  table costs **~4.2×** the memory (it's kept mostly empty).

**Learning:** the `set`/`dict` trades memory *and* an `O(n)` build for flat `O(1)`
lookups. Worth it only when enough queries amortize both costs; otherwise `bisect`
on already-sorted data wins on time *and* space.

---

## `ex04_find_closest.py`

Nearest-value lookup with `bisect`, keeping the list sorted via `bisect.insort`.

- **Time** (1,000,000-element sorted list): `insort` (keep sorted) **101.6 µs** —
  `O(n)`, it shifts elements; `find_closest` (search) **0.20 µs** — `O(log n)`.
- **Memory:** `O(1)` auxiliary — `insort` mutates in place, the search allocates nothing.

**Learning:** keeping a list sorted is the expensive part (`O(n)` per insert); once
sorted, every lookup is cheap (`O(log n)`). Use `insort` so you never re-sort.

---

## `ex05_overallocation.py`

Reverse-engineer CPython's growth formula `M = (N + (N>>3) + 6) & ~3`.

- **Memory:** predicted capacity `M`=4 (N=1), 16 (N=9), 1,125,004 (N=1M). Observed
  realloc jumps confirm tiny lists over-reserve (1 item → capacity 4). Same 1,000
  ints: **8,856 B** grown by `append` vs **8,056 B** built with `list()` (~800 B reclaimed).
- **Time + memory** (build 1,000,000 ints): append loop **26.1 ms / peak 38.6 MB** vs
  `list(range(..))` **16.3 ms / peak 38.1 MB** → **~2× faster** and slightly leaner.

**Learning:** overallocation makes `append` amortized `O(1)` but leaves dead headroom;
it only fires on `append`, so a direct `list()`/comprehension-recast is both faster
to build and tighter in memory.

---

## `ex06_memory_comp_list_tuple.py`

The "48 MB" experiment: 200,000 small collections of 9 ints, three ways.

- **Memory:** comprehension **88.82 MB** → `list([...])` **79.22 MB** (1.12×) →
  `tuple([...])` **76.02 MB** (1.17×).
- **Time** (per built sample): comprehension **1,309 ns**, `list()` **1,338 ns**,
  `tuple()` **1,356 ns** — all within noise; here the story is memory, not speed.

**Learning:** two memory savings stack — `list()` drops append headroom, `tuple`
additionally drops the resize-bookkeeping word. Multiplied across millions of tiny
collections, immutability pays for itself.

---

## `ex07_instantiation_timing.py`

How fast — and how large — is a list vs a tuple?

- **Time:** tuple literal **4.32 ns** vs list literal **38.29 ns** → **~8.9× faster**.
  Past the freelist the advantage *reverses*: `tuple(range(30))` **190 ns** vs
  `list(range(30))` **134 ns**.
- **Memory** (size-10 container): list **136 B** vs tuple **128 B** → tuple saves **8 B**/object.

**Learning:** immutable tuples ≤ size 20 come off CPython's freelist (no kernel
round-trip), so literals are far cheaper and slightly smaller. Beyond size 20
there's no freelist — measure before assuming "tuple is always faster."

---

## `ex09_custom_ordering.py`

Make a custom object sortable + binary-searchable with `functools.total_ordering`.

- **Time:** native `a < b` (`__lt__`) **164.8 ns** vs `total_ordering`-derived
  `a >= b` **193.6 ns** — the derived comparator adds a little call indirection.
- **Memory:** `O(1)` — ordering adds *methods*, not per-instance state.

**Learning:** without `__eq__`/`__lt__`, objects compare by memory address (sorting
is meaningless). `total_ordering` fills in the rest for a small per-call cost —
enough to plug into `sorted` and `bisect`.

---

Companion notes: `Chapter 3 Lists And tuples.md` in the Obsidian vault.
