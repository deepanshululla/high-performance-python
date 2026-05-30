FROM python:3.12-slim

# `time`     -> GNU /usr/bin/time (-v verbose), matching the host workflow.
# `graphviz` -> the `dot` binary, so gprof2dot can render call-graph PNGs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends time graphviz \
    && rm -rf /var/lib/apt/lists/*

# Profiling & visualization tools (cProfile/pstats are stdlib; these add
# the call-graph, flame-graph, icicle, and line-profiler front-ends).
RUN pip install --no-cache-dir gprof2dot snakeviz flameprof line_profiler

WORKDIR /app
COPY julia_set.py .

# Default: run the Julia set under GNU time's verbose output.
ENTRYPOINT ["/usr/bin/time", "-v", "python3", "julia_set.py"]
