# Chapter 6 — Matrix and Vector Computation: Practice Exercises

Runnable drills for *High Performance Python (3rd ed.)*, Chapter 6. Each script
self-reports **time** (`timeit`) and, where relevant, **memory** (`tracemalloc`
peak, via the shared `perf.py`) — so the wins are visible without an external
profiler.

The chapter's running example is the **2D diffusion equation**. These exercises
follow its optimization arc: pure Python → numpy → fewer allocations →
specialization → precision → **GPU**. ex01–ex06 use **numpy only**; ex07–ex08 use
**PyTorch on Apple's Metal (MPS) GPU** (`uv pip install torch`). The chapter's
`numexpr` and `scipy` sections need libraries not installed here — see the note at
the end.

Numbers below are from **CPython 3.14.0 / numpy 2.4 / macOS (Apple Silicon)** —
yours will differ, sometimes a lot (cache sizes and CPU instruction sets change
the story, as the exercises call out).

```bash
.venv/bin/python chapter_6/ex01_list_vs_numpy_norm.py
```

**Core idea:** runtime is governed by *how fast data reaches the compute unit*,
not how fast it computes. Python lists store pointers (scattered data, no
vectorization); numpy stores contiguous typed blocks and runs specialized C. The
fastest code is code you don't run — and every "optimization" must be benchmarked,
never assumed.

**Verified learnings** (measured on this machine — Apple M1 Max, CPython 3.14, numpy 2.4, torch 2.12 / MPS):

1. **Contiguous + typed + specialized beats general + boxed.** numpy is ~50× faster
   than pure Python on the *identical* diffusion algorithm (ex02); fusing operations
   to avoid temporaries wins again (`dot`, ex01).
2. **Allocation is a kernel round-trip, worse than a cache miss.** Preallocate scratch
   and use in-place ops; in-place beat out-of-place at *every* array size here (ex03/ex04).
   *Caveat: isolate the op when timing — allocating inside the timed call hides the effect.*
3. **Specialization isn't automatically a win — benchmark it.** A hand-rolled `roll_add`
   was *slower* than modern `np.roll` here, contradicting the book (ex05). This is the
   chapter's cautionary tale, reproduced.
4. **Precision is a speed knob on the GPU but a penalty on the CPU.** float16 is ~1.7×
   *faster* than float32 on the MPS GPU (ex07) yet ~8× *slower* than float64 on the CPU
   (ex06) — the CPU lacks native float16 instructions.
5. **GPUs win on parallel bulk math, lose on sequential/branchy work.** MPS ran the
   diffusion ~10× faster than the CPU (ex07), but the CPU was ~2,600× faster on a
   data-dependent walk (ex08). *Apple's unified memory means the book's CUDA
   "transfer is the #1 killer" lesson only partly applies — see ex08.*

---

## `ex01_list_vs_numpy_norm.py`

Norm-squared `sum(v*v)` four ways: Python loop, list comprehension, `numpy v*v + sum`, `numpy.dot`.

- **Time** (1,000,000 elements): loop **33.6 ms**, list-comp **30.5 ms**,
  `numpy v*v+sum` **0.75 ms** (~45×), `numpy.dot` **0.35 ms** (~97×).
- **Memory:** `numpy.dot` **peak 5.3 KB** vs list-comp **38.6 MB** (the comp
  materializes a whole `[v*v for v]` list).

**Learning:** numpy issues far fewer instructions over a contiguous typed buffer;
`dot` fuses multiply+sum into one pass, so it never allocates the `v*v` temporary.

---

## `ex02_diffusion_python_vs_numpy.py`

The 2D diffusion benchmark, three ways: pure Python (fresh grid each iter), pure
Python with a preallocated scratch buffer + swap (Example 6-6), and numpy + `roll`.

- **Time** (128×128, 50 iters): pure Python **165.9 ms**, prealloc **161.1 ms**
  (~1.03× — one fewer grid allocation/iter), numpy **3.1 ms** → **~53×**.
- The pure-Python preallocation win is *marginal*: it removes an allocation but
  can't fix pointer fragmentation, which is the real cost.
- All three grids verified identical (`max abs diff ~1e-18`).

**Learning:** the Python grid is a list of lists of *pointers* — the floats are
scattered across RAM, so every cell access is two pointer lookups and nothing
vectorizes (the von Neumann bottleneck). Preallocation only shaves the allocation
overhead; numpy's one contiguous typed block feeds vectorized C. Same math, ~53× apart.

---

## `ex03_inplace_vs_outofplace.py`

`a += b` vs `a = a + b`: `id()` proof + timing the operation in isolation across sizes.

- **`id()`:** in-place keeps the same buffer; out-of-place rebinds to a new array (directly verified).
- **Time** (inputs built once, *not* re-timed): **in-place wins at every size** —
  5×5 **1.10×**, 100×100 **1.24×**, 1024×1024 **1.23×**, 2048×2048 **1.10×**.

**Learning:** out-of-place allocates a fresh result array every call (a minor page
fault — a kernel round-trip, worse than a cache miss); in-place reuses the buffer.
The book notes out-of-place *can* win for tiny in-cache arrays (freer
vectorization) — a hardware-dependent effect that **did not reproduce here**.
*Methodology note: the arrays must be built outside the timed call; allocating
them inside it swamps the very difference you're measuring and turns the result
into noise.*

---

## `ex04_numpy_diffusion_memory.py`

Naive numpy diffusion (allocates temporaries each iter) vs a preallocated scratch buffer + in-place ops + reference swap.

- **Time** (512×512, 200 iters): naive **130.7 ms** vs in-place **121.3 ms** (~1.08×).
- **Memory:** naive **peak 8.0 MB** vs in-place **6.0 MB**.

**Learning:** preallocating once and using `+=`/`copyto` removes per-iteration
temporaries → fewer minor page faults and no pipeline stalls. The grid swap is a
cheap reference rename, not a copy. (Note: `np.roll` *still* allocates 4
temporaries — ex05 tries to remove those.)

---

## `ex05_roll_vs_roll_add.py`

Specialize `np.roll` into a custom in-place `roll_add` (fancy indexing, no temporary). **A cautionary tale.**

- **Correctness:** `test_roll_add` proves it matches `np.roll` for every ±1 shift/axis.
- **Time** (512×512, 300 iters): `np.roll` laplacian **186 ms** vs custom **222 ms** →
  custom is **~1.2× SLOWER here**.

**Learning:** the book measured a ~7% *win* from this specialization. On modern,
heavily optimized numpy the hand-rolled version's extra Python-level statements can
cost more than the temporaries they avoid — so it **loses** here. This is exactly
the chapter's lesson: **hypothesize, then benchmark.** Never assume specialized
code is faster, and weigh any win against the readability you give up.

---

## `ex06_float_precision_cpu.py`

`a*a + a` on a 2048×2048 array as float64 / float32 / float16 — the CPU half of the precision experiment.

- **Time:** float64 **2.40 ms**, float32 **1.22 ms** (~2× faster),
  float16 **18.3 ms** (**~7.6× SLOWER** than float64).

**Learning:** lower precision is *not* automatically faster on a CPU. float32 wins
(less data on the bus, native instructions), but the CPU has **no native float16
instructions**, so numpy up-converts every element — making float16 far slower. On
a GPU this flips (ex07): float16 is *faster* because the silicon was built to trade
precision for throughput.

---

## `ex07_diffusion_mps.py` *(GPU)*

Port the diffusion to PyTorch and run it on the **MPS** (Apple Metal) GPU; repeat the precision test on the GPU.

- **Diffusion** (1024×1024, 200 iters): numpy CPU **667 ms** vs torch MPS **69 ms** → **~9.7× faster on GPU** (port matches numpy to `2e-9`).
- **Precision on GPU** (`a*a+a`, 4096²): float16 **0.66 ms** vs float32 **1.13 ms** → float16 **1.7× faster**.

**Learning:** GPUs win big on parallel linear algebra. And float16 is *faster* on
the GPU — the **exact opposite** of ex06's CPU result (where float16 was ~8×
slower). Precision is a speed knob on the GPU, a penalty on the CPU. *(The book
targets NVIDIA/CUDA; this is Apple MPS, so magnitudes differ — but the lessons
hold. GPU timing must `synchronize()` and warm up, since ops are async.)*

---

## `ex08_when_not_gpu.py` *(GPU)*

The flip side (Example 6-25): a sequential, branch-heavy walk where each step needs the previous result.

- **Time** (321 dependent steps): numpy CPU **45.5 µs** vs torch MPS **118 ms** → **CPU ~2,600× faster**.

**Learning:** a GPU has thousands of *slow* cores; a CPU has a few *fast* ones.
With no parallelism to exploit, the GPU loses badly — and reading tensor elements
one-by-one (`A[i]`) forces a tiny CPU↔GPU sync every step. Use the GPU for bulk
vectorized math (ex07), never for sequential, data-dependent, branchy code. *(This
is also the closest Apple Silicon gets to the book's CUDA "transfer is the #1
killer" lesson: unified memory makes a one-shot `.to()` cheap, but per-element
syncs in a hot loop are still ruinous.)*

---

## `ex09_diffusion_conv_mps.py` *(GPU)*

Express the laplacian as a 3×3 **convolution** (`Conv2d`, circular padding) vs the explicit roll version — both on MPS (Example 6-23).

- **Correctness:** conv reproduces the roll laplacian to `9e-10` (standard-sign
  kernel `[[0,1,0],[1,-4,1],[0,1,0]]` — the book prints the *negated* kernel).
- **Time** (100 iters): conv beats roll at **every** size — 256² **1.70×**,
  1024² **1.59×**, 2048² **1.84×**.

**Learning:** this is *not* an algorithm change — it's the same computation routed
through a purpose-built, heavily optimized GPU kernel. (The book saw conv win only
on large CUDA grids; on MPS it wins everywhere.) Such algorithmic swaps to optimized
primitives are never done for you automatically — you have to reach for them.

---

## `ex10_amp_bfloat16.py` *(GPU)*

`float16` vs `bfloat16` trade-off (Example 6-22) + Automatic Mixed Precision (Example 6-26).

- **finfo:** both 2 bytes; `float16` max **65 504**, resolution 0.001 — `bfloat16`
  max **3.4e38** (float32-like range), resolution 0.01. Same size, range-vs-precision split.
- **autocast gotcha:** inside `autocast`, `mm(float32, float32)` returns **float16**.
- **Speed** (matmul 4096²): float32 **21.1 ms**, autocast **20.2 ms** (1.04×),
  manual `.half()` **19.8 ms** (1.07×).

**Learning:** `bfloat16` trades precision for range (deep learning favors range).
autocast auto-selects per-op precision — but its *speed* benefit is hardware-
dependent: **near-zero on this MPS GPU** (Apple's float16 matmul ≈ float32),
versus the book's ~3× on CUDA. The portable part is the mechanics, not the speedup —
**measure on your hardware.**

---

## `ex11_numexpr_crossover.py`

`numexpr.evaluate("out*0.1 + grid", out=out)` vs the plain numpy combine, swept across grid sizes (Examples 6-18, 6-19).

- **Time** (50 iters): numexpr is a **net loss** until the arrays overflow cache —
  256² **1.67× slower**, 512² **1.24× slower**, 1024² **1.10× slower**, then it
  **overtakes** numpy at **2048²**.

**Learning:** numexpr compiles the whole expression into one cache-aware, fused,
multi-threaded pass. But the compile + chunking + thread overhead isn't repaid while
the data still fits in the last-level cache — it only wins once two grids no longer
fit (~1000²+ doubles), where its cache-juggling avoids the memory-bandwidth stalls
that hurt plain numpy. A textbook size-dependent "optimization": benchmark before trusting.

---

## `ex12_scipy_cautionary.py`

`scipy.ndimage.laplace(mode="wrap")` as a drop-in laplacian vs the specialized roll version (Examples 6-27, 6-28). **The chapter's cautionary tale.**

- **Correctness:** scipy's wrap laplacian is *numerically identical* to ours — a fair fight.
- **Time** (50 iters): scipy is **slower at every size, and the gap widens** —
  256² **2.60×**, 512² **3.54×**, 1024² **3.83×**, 2048² **4.41× slower**.

**Learning:** the obvious-sounding optimization ("it's a well-known image library,
surely it's faster") is a **regression**. scipy's filter is fully general (any
dimension, any boundary mode, any footprint), so it issues far more instructions and
branches than code that does exactly one thing. Hypothesize, then **measure** — every time.

---

## `bench_summary.py` — the summary tables (6-1 / 6-2)

A grid-size sweep that times **every** available implementation and prints a runtime
table + a speedup-vs-pure-Python table, reproducing the chapter's two summary tables.

```bash
.venv/bin/python chapter_6/bench_summary.py             # defaults: 50 iters, 64–512
.venv/bin/python chapter_6/bench_summary.py 50 64,128,256,512,1024
```

Sample (50 iters, MPS) — speedup vs pure Python (`~` = baseline extrapolated):

| impl | 64² | 128² | 256² | 512² | 1024² |
| --- | ---: | ---: | ---: | ---: | ---: |
| numpy | 31.2× | 52.1× | 78.7× | ~84.4× | ~66.2× |
| numpy+inplace | 31.0× | 53.9× | 81.2× | ~88.4× | ~76.3× |
| numpy+roll_add | 46.7× | 57.2× | 69.8× | ~72.7× | ~70.0× |
| numpy+numexpr | 7.7× | 23.4× | 45.2× | ~67.1× | **~77.2×** |
| numpy+scipy | 33.1× | 37.7× | 29.5× | ~27.2× | ~21.5× |
| torch (mps) | 4.8× | 27.0× | 109.4× | ~296.7× | ~623.1× |
| torch+conv (mps) | 4.4× | 27.3× | 147.1× | ~444.2× | ~928.6× |

**Learning:** the book's three performance bands reappear — pure Python at the
bottom, numpy/CPU in the middle, GPU on top. Read across the rows for the chapter's
whole story at once: **numexpr** starts terrible (7.7×) and climbs past plain numpy
by 1024² (the cache crossover); **scipy** is the lone CPU method that *declines* with
size (the cautionary tale); the **GPU** loses at tiny grids (launch overhead) then
runs away (conv 928× at 1024²). *Honesty notes baked in:* iterations are
fewer than the book's 1,000 (ratios stay comparable); pure Python is measured to
256² and **extrapolated** (`~`) above (it's cleanly O(n²·iters)); GPU is MPS, not CUDA.

---

### Not reproduced here (platform, not libraries)

All of the chapter's *library* examples are now covered — numpy, numexpr (ex11),
scipy (ex12), and PyTorch/GPU (ex07–ex10) are all project dependencies. What remains
unreproduced is **platform-bound profiler output**, not lessons:

- **`perf stat` counters** (cache-misses, page-faults, IPC, branch-misses) — `perf`
  is Linux-only; macOS can't run it. These scripts substitute `timeit` + `tracemalloc`
  (time + memory). The *lessons* those counters teach — fragmentation,
  allocations-as-faults, branch cost — are demonstrated through timing/memory deltas.
- **`kernprof`/`line_profiler` line tables** and **`torch.utils.bottleneck`** — these
  are profiler *outputs*, not benchmarks; line-profiler is installed if you want to run
  `kernprof -l -v` on any script yourself.

Companion notes: `Chapter 6 Matrix and Vector Computation.md` in the Obsidian vault.
