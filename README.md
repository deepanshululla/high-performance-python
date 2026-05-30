# High Performance Python — Julia Set

The canonical Julia-set escape-time example from *High Performance Python* (Gorelick & Ozsvald, O'Reilly), wired up with a profiling and flame-graph toolchain so you can reproduce the book's measurements end-to-end.

## What's here

```
chapter_2/
├── julia_set.py          # pure-Python escape-time loop, @timefn decorator, argparse CLI
├── Dockerfile            # python:3.12-slim + GNU time + graphviz + profiling stack
├── build_flame_html.py   # cProfile .prof → self-contained d3-flame-graph HTML
└── .dockerignore
pyproject.toml            # uv-managed; runtime deps = [] (stdlib only)
                          #   [profiling] group: gprof2dot, snakeviz, flameprof, line-profiler
uv.lock
```

The Julia-set computation itself has **zero runtime dependencies** — the `profiling` group only adds the visualization front-ends.

## Quick start

```bash
uv sync                                  # creates .venv, installs profiling tools
uv run python chapter_2/julia_set.py     # 1000×1000 grid, 300 iterations
```

Custom grid / iteration count:

```bash
uv run python chapter_2/julia_set.py --width 2000 --max-iterations 300
```

The 1000×1000 @ 300-iter run asserts `sum(output) == 33219980` — the book's fixture value.

## Benchmarking

Wall time via `timeit` (5 loops × 5 repeats):

```bash
uv run python -m timeit -v -n 5 -r 5 \
    -s "from chapter_2.julia_set import calc_pure_python" \
    "calc_pure_python(1000, 300)"
```

The `@timefn` decorator in `julia_set.py` also prints per-call timing for the inner loop, so you can separate grid-construction overhead from the escape-time work.

## Profiling

### cProfile (sorted by cumulative time)

```bash
uv run python -m cProfile -s cumulative chapter_2/julia_set.py
uv run python -m cProfile -o chapter_2/julia.prof chapter_2/julia_set.py
```

The cumulative view typically shows `builtins.abs` dominating after the loop body itself — the canonical book finding (~34M calls for the default grid).

### Call-graph PNG (gprof2dot + graphviz)

```bash
uv run gprof2dot -f pstats chapter_2/julia.prof | dot -Tpng -o chapter_2/julia_profile.png
```

### Interactive icicle viewer (snakeviz)

```bash
uv run snakeviz chapter_2/julia.prof
```

### Static SVG flame graph (flameprof)

```bash
uv run flameprof chapter_2/julia.prof > chapter_2/julia_flame.svg
```

### Interactive d3 flame graph (custom builder)

```bash
uv run python chapter_2/build_flame_html.py chapter_2/julia.prof chapter_2/julia_flame_interactive.html
```

Open the resulting HTML in a browser — click to zoom, hover for tooltips, type to search frames.

### Line profiler

Decorate hot functions with `@profile` (line-profiler injects this builtin), then:

```bash
uv run kernprof -l -v chapter_2/julia_set.py
```

## Docker

Reproduces the book's measurements under a clean image with GNU `/usr/bin/time -v` as the entrypoint, so wall time + max RSS + page faults are reported alongside the script output.

```bash
docker build -t hpp-julia chapter_2/
docker run --rm hpp-julia                  # default: 1000×1000, 300 iter
docker run --rm hpp-julia --width 500 --max-iterations 100
```

## Reference

Gorelick, M. & Ozsvald, I. *High Performance Python*, 2nd ed. (O'Reilly, 2020), Chapter 2 — "Profiling to Find Bottlenecks."
