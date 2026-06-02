# Chapter 4 — Dictionaries and Sets: Practice Exercises

Runnable drills for *High Performance Python (3rd ed.)*, Chapter 4. Each script
self-reports **time** (`timeit`) and **memory** (`tracemalloc` peak / `sys.getsizeof`,
via the shared `perf.py`).

Numbers below are from **CPython 3.14.0 / macOS** — yours will differ.

```bash
.venv/bin/python chapter_4/ex01_hash_mask.py
```

**Core idea:** `O(1)` is a *promise conditional on a high-entropy hash*. The key is
hashed then masked into a bucket; collisions are resolved by a perturbed probe that
folds in high-order bits. A degenerate hash collapses the table back to an `O(n)`
linear scan.

---

## `ex01_hash_mask.py`

`hash(key) & (size-1)` by hand; why `Rome`/`Barcelona` collide in an 8-bucket table.

- **Time:** `hash(key) & mask` = **55.2 ns/op** — `O(1)`, one bitwise AND (plus the
  string hash itself, which is `O(len)`).
- **Memory:** `O(1)` — the index is *computed*, nothing is stored to find it.

**Learning:** masking keeps only the low bits, so keys sharing low bits collide
even though their full hashes differ.

---

## `ex02_set_vs_list_unique.py`

Uniqueness via a growing list vs a set.

- **Time** (speedup widens with N): **44×** (1,000) → **199×** (5,000) → **718×** (20,000).
- **Memory** (N=20,000 peak): list method **1.1 MB** vs set method **3.4 MB**.

**Learning:** the list scans a growing "seen" list per name (`O(n²)`-ish); the set's
`O(1)` `add` makes it a single `O(n)` pass — for ~3× the memory. The time gap widens
because one cost scales with data size and the other stays flat.

---

## `ex03_dict_vs_bisect.py`

Lookup: `dict` `O(1)` vs list+`bisect` `O(log n)`, with the memory price.

- **Time:** dict stays flat; `bisect` grows — ratio **5.2× → 7.0× → 7.7×** as N goes
  1k → 100k → 1M.
- **Memory** (N=1,000,000): list+bisect (names+numbers) **16.1 MB** vs dict **29.3 MB**.

**Learning:** the dict buys flat `O(1)` lookup by spending ~2× the memory on a hash
table; `bisect` buys lower memory at `O(log n)`. Pick per your lookup volume.

---

## `ex04_probing_trace.py`

Implement the perturbed probe sequence; trace collisions, a lookup-miss, and tombstone-on-delete.

- **Time:** a lookup costs *one probe per collision in the chain* — `O(1)` amortized
  with a good hash, `O(n)` worst case if everything collides (see `ex06`).
- **Memory:** the table is `O(n)` buckets, deliberately kept ≤ 2/3 full; deletion
  leaves a tombstone (no immediate reclaim).

**Learning:** probing makes a bucket's meaning depend on its neighbours, so deletion
must leave a tombstone — `NULL` would terminate the chain early and lose keys stored
past the deleted slot.

---

## `ex05_point_hash.py`

Content-based `__hash__`/`__eq__` so a `set` deduplicates value-equal objects.

- **Time:** content `__hash__` = **100.8 ns/op** (it hashes the `(x, y)` tuple), vs the
  trivial `id`-based default.
- **Memory:** `O(1)` per object — correctness (dedup) is the goal, not speed.

**Learning:** a custom hash must stay `O(1)`, or every `set`/`dict` operation inherits
its cost. Defining `__eq__` without `__hash__` makes the class unhashable.

---

## `ex06_good_bad_hash.py`

`BadHash` (all keys → 42) vs `GoodHash` (perfect) vs a plain list — the cost of a bad hash.

- **Time** (1,000,000 membership tests of `"zz"`): good_dict **0.172 s** (baseline),
  list **5.29 s** (**30.7×**), bad_dict **9.46 s** (**54.9×**).
- **Memory** (676 entries): good_set and bad_set are **identical** (32,984 B); list 6,136 B.

**Learning:** a degenerate hash wrecks lookup *time* (collapses to `O(n)` linear probing,
even slower than a list) while occupying the *same* space. The damage is all in time.

---

## `ex07_twoletter_hash.py`

Why a perfect hash is collision-free at one table size but not another.

- **Memory/structure:** 676 two-letter keys → 676 distinct hashes. **0 collisions** at
  table size 2048 and 1024, but **164 collisions** at 512.
- **Time implication:** zero collisions → every lookup is a single probe (`O(1)`);
  collisions lengthen probe chains.

**Learning:** "ideal" is relative to the mask. You must know both the value range and
the table size to design a collision-free hash.

---

## `ex08_resizing.py`

Resize arithmetic, the shrink quirk, and amortized-insert timing.

- **Memory:** size classes 8/16/32/…; N=1039 → 2048-bucket table. The 2nd-ed book's
  shrink-on-insert **does NOT happen** on CPython 3.14 (stays **36,952 B** after
  popping 999 of 1000 and inserting); `dict.copy()` rebuilds to **224 B**.
- **Time:** building a 100,000-key dict = **35.9 ns/insert**; 1,000,000-key = **38.2 ns/insert**
  — flat across sizes despite `O(n)` resizes at each power-of-two boundary → amortized `O(1)`.

**Learning:** rare `O(n)` resizes spread across many `O(1)` inserts keep the average
at `O(1)`. And re-profile across CPython versions — the shrink behaviour changed.

---

## `ex09_int_hash.py`

The integer-hash identity and where finiteness creates collisions.

- **Time/Memory:** `O(1)` — pure bit math, no allocation.
- **Result:** `5` and `501` collide in an 8-bucket table (both → 5) but not in 1024.

**Learning:** `hash(int) == int` (in range), so an infinite table never collides;
the finite *mask* is what reintroduces collisions.

---

> `ex08` is a live demonstration of the chapter's own closing warning — *always
> re-profile performance assumptions across CPython versions.*

Companion notes: `Chapter 4 Dictionaries and Sets.md` in the Obsidian vault.
