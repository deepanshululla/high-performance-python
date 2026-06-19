# h01 — IPython Parallel vs multiprocessing.Pool on one machine

**Hypothesis:** On a single machine, `multiprocessing.Pool` matches or beats IPython Parallel, and
the gap widens as tasks get finer-grained — so IPython Parallel's value is *remote* engines and
*interactive* control, not local speed.

ex01 showed IPython Parallel estimating pi at about 6.7× on eight engines — the very same speedup
Chapter 10 got from a bare `multiprocessing.Pool`. That raises the obvious question: on one machine,
is there any *performance* reason to pay for IPython Parallel's machinery — a controller, ZeroMQ
transport, per-task scheduling — over a plain Pool? This experiment holds the workload identical (the
same total darts, the same `estimate_pi_block`) and runs it both ways at two granularities, timing
warm compute with startup excluded, plus the one-time startup of each.

## Prediction

1. **Startup**: a Pool is far cheaper to create than a cluster of engine kernels — Pool wins by a
   large margin.
2. **Coarse-grained work** (a few big tasks): roughly a **tie** — both just run eight interpreters
   flat out, and per-task overhead is negligible against seconds of compute.
3. **Fine-grained work** (many small tasks): the **Pool wins**, because every task in IPython
   Parallel is a ZeroMQ round-trip through the scheduler (the latency tax ex02 measured), while a
   Pool ships work over cheap local pipes with chunking.

## What we measured

| | Pool | IPython | IPP / Pool |
| --- | ---: | ---: | ---: |
| startup | ~0.01 s | ~7.0 s | **~590×** |
| coarse (8 tasks) | ~1.14 s | ~1.24 s | ~1.09× |
| fine (256 tasks) | ~1.19 s | ~1.45 s | ~1.23× |

A correctness anchor asserts every variant's pi estimate is real, so none can look fast by computing
less.

## Verdict: CONFIRMED

**The Pool starts hundreds of times faster and is never slower on compute — it ties on coarse work
and pulls ahead as the work gets finer-grained.** Creating a Pool of eight workers is essentially
instantaneous (~10 ms — eight `fork`s); bringing up an IPython cluster of eight engines takes about
seven seconds, because each engine is a full kernel process that has to boot and connect back to the
controller over ZeroMQ. That ~590× startup gap is the dominant, utterly reproducible result.

On warm compute the two are close, exactly as predicted. With eight big tasks they effectively tie
(~1.09×): both are running eight Python interpreters on eight cores, the per-task overhead is a
rounding error against a second of compute, and there is nothing for the cluster layer to add. Slice
the *same* total work into 256 small tasks and the Pool's lead grows to ~1.23×, because now the
per-task cost matters: IPython routes every one of the 256 tasks through its scheduler as a ZeroMQ
message, while the Pool ships them over local pipes in chunks. The fine-grained margin is modest and
a little noisy run to run — the robust, repeatable facts are the enormous startup gap and that the
Pool is never the slower choice.

So for purely local, share-nothing parallelism, there is no speed reason to reach for IPython
Parallel — the Pool is simpler, starts instantly, and is at least as fast. That is *not* a knock on
IPython Parallel; it is a statement about what it is *for*. Its machinery exists to do things a Pool
fundamentally cannot: run engines on *other machines*, push and pull data among them interactively,
debug a live engine, and drive a cluster from a notebook. You pay the seven-second startup and the
per-task latency to buy reach and interactivity, and on a single laptop you are paying for reach you
are not using. The book reaches for IPython Parallel in a *research-cluster* setting for exactly
those reasons — and the chapter's whole framing ("exhaust one machine first") is the other side of
this coin: if one machine suffices, the Pool is the right tool.

## Reading the chart

![h01 chart](chart.png)

The left panel (log scale) is the startup cost: a sliver for the Pool, a tower for IPython — the
~590× gap. The right panel is warm compute, grouped by granularity: the coarse bars are nearly equal
(the tie), and the fine bars show the Pool pulling ahead (its lower per-task overhead). The verdict
caption restates it: Pool starts vastly faster and is never slower locally, so IPython Parallel's
value lives in remote engines and interactivity.

## Run

```bash
.venv/bin/python chapter_11_clusters_and_job_queues/hypothesis/h01_ipython_vs_pool/benchmark.py
.venv/bin/python chapter_11_clusters_and_job_queues/hypothesis/h01_ipython_vs_pool/plot.py
```

The startup gap and the coarse-work tie reproduce strongly; the fine-grained margin is small and
varies with scheduling noise, which is itself the honest point — the decisive, repeatable difference
is startup, not warm throughput.

## 5 Whys

1. **Why does the Pool start ~590× faster?** A Pool just `fork`s worker processes (near-instant on
   this machine), while an IPython cluster boots a controller plus eight full engine kernels that
   each connect back over ZeroMQ — seconds of process startup and handshaking.
2. **Why do they tie on coarse-grained work?** With only eight big tasks, both run eight interpreters
   on eight cores and the per-task communication is negligible next to a second of compute, so the
   wall-clock is set by the cores, not the framework.
3. **Why does the Pool pull ahead on fine-grained work?** Each of the 256 small tasks costs IPython a
   ZeroMQ round-trip through its scheduler, whereas the Pool ships tasks over local pipes in chunks —
   so IPython pays more overhead exactly when there are more tasks.
4. **Why use IPython Parallel at all, then?** Because it does what a Pool cannot: run engines on
   remote machines, move data among them interactively, and let you debug a live cluster from a
   notebook — capabilities, not local speed.
5. **Why does this matter?** It validates the chapter's opening advice — exhaust one machine first;
   the simpler local tool (a Pool) is as fast and starts instantly, so you move to a cluster for
   reach, resilience, and interactivity, not to make local work faster.

**Root cause:** IPython Parallel and `multiprocessing.Pool` both run N interpreters on N cores, so
their warm compute is the same; the cluster layer adds a large fixed startup and a per-task ZeroMQ
cost that can only *lose* to a Pool locally — which is why its payoff is remote engines and
interactive control, the things a Pool cannot provide.
