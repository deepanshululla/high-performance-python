# ex03 — The `len([...])` trap

There is a tempting one-liner for counting how many items satisfy a condition:
`len([n for n in data if cond(n)])`. It reads cleanly and gives the right answer.
This exercise puts it head to head with `sum(1 for n in data if cond(n))`, which
returns the identical count, and shows that the two have wildly different memory
profiles. The only visible difference in the source is a pair of square brackets
versus a pair of parentheses — and that single character flips the computation from
materializing the whole filtered list to folding one value at a time.

```bash
.venv/bin/python chapter_5/ex03_len_trap/ex03_len_trap.py   # run the benchmark
.venv/bin/python chapter_5/ex03_len_trap/plot.py            # regenerate the chart
```

Numbers below are from **CPython 3.14.0 / macOS** — magnitudes vary by machine.

## What the benchmark measures

The benchmark counts the matching elements both ways and records time and peak
memory. The times are essentially tied — `len([...])` at about **623.8 ms** and
`sum(1 for ...)` at about **614.1 ms** — because both must visit every element and
test the condition. Memory is where they part: `len([...])` peaks at about
**111.3 MB** because it builds a list of *every match* before counting it, while
`sum(1 for ...)` peaks at about **27.9 KB** because the generator expression emits a
`1` for each match and `sum` immediately folds it into a running total, keeping
nothing.

## Reading the chart

![len([]) vs sum(1 for ()): equal time, huge memory gap](chart.png)

*Identical run time and answer, but `[]` materializes every match (~111 MB) while `()` folds one value at a time (KB) — the only source difference is the brackets.*

The two time bars line up almost exactly, confirming that the counting work is the
same either way. The memory panel, on a log scale, shows the list comprehension's
bar dwarfing the generator's — three to four orders of magnitude apart. The visual
takeaway is that equal time can hide a vast memory difference: the brackets do not
make the program slower, they make it *bigger*, briefly holding the entire matched
collection in RAM only to discard it the instant the count is taken.

## What it means

This is a trap precisely because the wasteful version looks so reasonable. A list
comprehension is the right tool when you need the items, but if all you want is a
*count*, materializing them is pure overhead — you build a collection solely to ask
for its length and then drop it. The generator-expression form is a single
character cheaper to write and `O(1)` in memory instead of `O(matches)`. The habit
worth forming: whenever you find yourself wrapping a comprehension in `len()`,
`sum()`, `any()`, `all()`, `min()`, or `max()`, reach for the parentheses, because
those consumers fold a stream and never need the list at all.

## Five whys

1. **Why does `len([...])` use ~111 MB while `sum(1 for ...)` uses kilobytes?** The list comprehension builds and holds a list of every matching element before `len` reads its size, whereas the generator expression hands `sum` one value at a time.
2. **Why does the list need every match to exist at once?** `len()` is defined on a finished container — it asks an already-built object how many items it holds — so the comprehension must finish materializing before `len` can run.
3. **Why can `sum(1 for ...)` avoid building a container?** `sum` is a fold: it pulls one `1` from the generator, adds it to an accumulator, and lets that `1` be discarded, so only the running total persists.
4. **Why is folding the structurally cheaper way to count?** Counting needs only a single integer of state, and a fold expresses exactly that, whereas materializing-then-measuring expresses far more state than the question requires.
5. **Why does one character of source decide all of this?** `[]` invokes the list constructor, which eagerly collects, while `()` produces a lazy generator object, so the brackets choose between eager storage and lazy streaming.

**Root cause:** `len` measures a built container, forcing `O(matches)` materialization, while `sum` over a generator folds a stream into one accumulator — so the brackets versus parentheses pick eager storage versus lazy streaming.
