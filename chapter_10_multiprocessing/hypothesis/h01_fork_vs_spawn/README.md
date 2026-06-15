# h01 — fork vs spawn: the start method the book assumes vs the one macOS gives you

> **Verdict: CONFIRMED.** On this machine the default start method is **spawn**, not the **fork**
> the book implicitly assumes. spawn is several times slower to start a pool, and — more
> consequentially — it silently breaks the "share state through a module global" pattern that
> ex07's flags and ex08's shared array rely on. A forked child inherits the parent's mutated
> globals; a spawned child re-imports the module and sees only its import-time defaults.

## The hypothesis

The book was written on Linux, where `multiprocessing` defaults to `fork`: a new process is a
copy-on-write clone of the parent, so anything the parent set up — including module globals — is
simply present in the child. CPython 3.14 on macOS defaults to `spawn` instead: each worker is a
brand-new interpreter that re-imports your module from scratch. We predicted two consequences and
let the measurements decide the verdict:

* **(A) spawn is slower to start a pool**, because re-importing everything per worker is more work
  than cloning.
* **(B) spawn loses the parent's globals.** We set a module-level `SHARED_FLAG["value"]` to 42
  *after* import, then ask a child what it sees. fork should report 42 (inherited); spawn should
  report 0 (the re-imported default).

## What it measures

A module global is mutated to 42 in the parent, then read back from a child under each start
method; separately, the wall-clock cost of standing up an 8-worker pool is timed under each:

| start method | pool startup (best of 5) | child sees in shared global |
| --- | ---: | ---: |
| fork | ~10 ms | **42** — inherited |
| spawn | ~50–330 ms | **0** — re-imported default, mutation lost |

(The startup gap swings from ~5x to ~25x depending on machine load and how much the module imports
— spawn re-imports numpy and friends every time — but fork is always the faster one. The
inheritance result, 42 vs 0, is deterministic.)

## What we found

**Both predictions hold, so the verdict is CONFIRMED.** fork stands up a pool in about ten
milliseconds because it clones the running parent; spawn takes several to tens of times longer
because each of the eight workers boots a fresh interpreter and re-imports the module tree. That is
the visible, benign half of the difference — a one-time startup tax.

**The consequential half is (B): spawn quietly breaks global-state sharing.** The forked child sees
42 because it is a clone of the parent *after* the mutation; the spawned child sees 0 because it
re-ran the module's top-level code (`SHARED_FLAG = {"value": 0}`) and never ran the parent's later
mutation. This is exactly the mechanism behind ex07 and ex08: those exercises stash a `RawValue`,
an `mmap` block, or a filled numpy array in a module global and rely on the workers inheriting it.
Under the default spawn method, the workers would inherit *nothing* — ex08's worker would assert
`main_nparray[idx, 0] == 42` against a freshly re-imported empty array and crash, and ex07's flag
would never be visible to the pool. Nothing warns you; the code that "works in the book" simply
produces wrong results or asserts out.

**That is why every shared-state exercise in this chapter forces `mp.get_context("fork")`** (see
`_mp.py`). It reproduces the book's behaviour on a machine whose default would otherwise silently
diverge from it. The honest caveat: fork on macOS carries its own warnings (it is unsafe to fork a
process that has already spawned threads, which is why Python flipped the default), so the right
production move is usually to write spawn-safe code — pass shared objects as explicit arguments,
or use a `Pool` initializer — rather than to force fork. We force fork here because the goal is to
study the book's examples faithfully, not to ship them.

## Reading the chart

![h01 chart](chart.png)

Left panel: pool startup in milliseconds — the tiny teal fork bar against the towering red spawn
bar. Right panel: what the child sees in the shared global, against a dashed line at 42 (the value
the parent set). fork's teal bar reaches the line ("inherited"); spawn's bar sits at the floor
("LOST"). The left panel is the convenience cost; the right panel is the correctness trap.

## Run

```bash
.venv/bin/python chapter_10_multiprocessing/hypothesis/h01_fork_vs_spawn/benchmark.py   # numbers + verdict
.venv/bin/python chapter_10_multiprocessing/hypothesis/h01_fork_vs_spawn/plot.py        # regenerate chart.png
```

## 5 Whys

1. **Why does a spawned child see 0 instead of the parent's 42?** spawn boots a new interpreter
   that re-imports the module, re-running `SHARED_FLAG = {"value": 0}` and never replaying the
   parent's later mutation.
2. **Why does a forked child see 42?** fork clones the parent process *after* the mutation, so the
   child starts life with the already-mutated global in place.
3. **Why does this break ex07 and ex08?** They share a flag or array through a module global and
   count on the workers inheriting it — which only fork does; under spawn the workers get empty
   defaults.
4. **Why is spawn slower to start a pool?** Each worker is a fresh interpreter that must re-import
   the whole module tree (numpy included), where fork merely copies the already-loaded parent.
5. **Why did Python make spawn the default on macOS anyway?** Forking a process that has already
   created threads is unsafe and crashes in subtle ways; spawn avoids that whole class of bug, at
   the cost of speed and inherited state.

**Root cause:** fork and spawn differ in whether the child inherits the parent's post-import memory;
the book's global-sharing examples depend on inheritance, so they only work under fork — making the
start method a correctness dependency, not just a performance knob, on any machine that defaults to
spawn.
