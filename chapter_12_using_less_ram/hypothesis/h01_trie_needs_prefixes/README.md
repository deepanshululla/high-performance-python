# h01 — Does a trie's RAM win over a set come from shared prefixes?

ex05 showed a loaded `marisa_trie` costing about 57x less RAM than a `set` of the same two million
tokens. That is a spectacular saving, but the book is careful to qualify it: the trie's benefit
"depends on your data's structure," because a trie compresses by folding *shared prefixes* into single
branches. If that is where the win comes from, then data with no shared structure should erase most of
it. This hypothesis tests that claim directly.

**Hypothesis.** The trie's RAM advantage over a set is largely due to shared prefixes. On
high-entropy random tokens — 16 hexadecimal characters that almost never share even a leading
character — the trie has nothing to fold, so its advantage over a set should shrink dramatically
compared to the prefix-heavy case.

The experiment changes exactly one thing. Both token distributions (`prefixed` and `random`, from the
shared `_tokens.py`) use the same count (2,000,000) and the same length (16 characters); only the
*structure* differs. We measure the loaded-trie and set footprints as peak RSS in a fresh process for
each, and compare the advantage ratios. The verdict is data-driven: the hypothesis is CONFIRMED if the
random-token advantage is less than half the prefixed-token advantage.

## What it measures

2,000,000 unique 16-character tokens, peak RSS in a fresh process:

| distribution | set | trie (loaded) | trie advantage |
| --- | ---: | ---: | ---: |
| prefixed (shared fronts) | 248.7 MiB | 4.4 MiB | **56.6x** |
| random (high entropy) | 248.8 MiB | 19.0 MiB | **13.1x** |

## What we found — VERDICT: CONFIRMED

**Removing the shared prefixes shrinks the trie's advantage 4.3x — from 56.6x down to 13.1x.** The
set is unmoved (248.7 vs 248.8 MiB): a hash set stores each string as its own Python object regardless
of structure, so its footprint depends only on the count and length, not on what the strings look
like. The trie is where all the movement is: it costs 4.4 MiB when the tokens share a small pool of
leading prefixes and 19.0 MiB — over four times more — when they don't. That difference *is* the
prefix compression. With shared fronts, millions of tokens collapse into a handful of common branches;
with random fronts, the tree fans out almost immediately and there is little to fold. The hypothesis
holds: most of the trie's headline RAM win on prefix-rich data comes from prefix sharing.

**But the more interesting part is what the hypothesis got slightly wrong.** The trie does *not* lose
its advantage on random data — it still beats the set 13x. That residual win has nothing to do with
prefixes: a `set` pays Python's per-object tax on every string (an object header, a hash, a length,
the characters), whereas the trie stores the raw character bytes in one compact LOUDS-encoded
structure with no per-string Python object at all. So a trie actually offers *two* independent
savings: a structural one from folding shared prefixes (the 4.3x measured here) and a representational
one from storing bytes instead of `str` objects (the 13x that survives on random data). The book
emphasises the first; this experiment surfaces the second. The practical reading is that a trie is
worth trying whenever you hold a large static set of strings — and an outright winner when those
strings also share structure.

## Reading the chart

![h01 chart](chart.png)

Two panels. The left shows set and trie footprints side by side for each distribution: the two set
bars are the same height (structure-blind), while the trie bar jumps from tiny (prefixed) to several
times taller (random) — the visual of prefix compression switching off. The right reduces it to the
advantage ratio: a tall ~57x bar for prefixed beside a ~13x bar for random, captioned with the
4.3x shrink and the verdict.

## Run

```bash
.venv/bin/python chapter_12_using_less_ram/hypothesis/h01_trie_needs_prefixes/benchmark.py
.venv/bin/python chapter_12_using_less_ram/hypothesis/h01_trie_needs_prefixes/plot.py
```

Each footprint is measured in its own spawned process; the script also writes `tokens_*.marisa` files
to disk for the load measurements (gitignored). Expect ~15 s.

## 5 Whys

1. **Why does the trie use 4x more RAM on random tokens than on prefixed ones?** With shared prefixes
   the trie folds millions of common leading characters into a few branches; with random fronts every
   token diverges almost immediately, so the tree fans out and stores far more edges.
2. **Why is the set's footprint unchanged between the two distributions?** A hash set stores each
   string as a separate Python object keyed by its hash, and that cost depends only on the number and
   length of strings — not on whether they share characters.
3. **Why does the trie still beat the set 13x even with no shared prefixes?** The trie stores raw
   character bytes in one compact structure, while the set pays Python's per-object overhead (header,
   hash, length) on every single string — a representational saving independent of prefix sharing.
4. **Why does the hypothesis count as CONFIRMED if the trie still wins on random data?** Because the
   claim was about the *advantage shrinking*, and it does — by 4.3x — showing that prefix sharing
   accounts for most of the trie's extra win on structured data, exactly as predicted.
5. **Why does this matter when choosing a container?** Because it tells you *when* a trie pays off: any
   large static string set benefits from the per-object saving, but the dramatic 50x+ wins require
   data with genuinely shared structure — so you should benchmark on your own tokens, as the book
   insists.

**Root cause:** A trie saves memory two ways — by storing bytes instead of Python `str` objects (a
flat win on any string set) and by folding shared prefixes into shared branches (a win that scales
with how much structure the data has). Stripping the shared structure removes only the second saving,
which is why the advantage shrinks ~4x yet never disappears.
