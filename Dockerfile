# Built on the official uv image so the in-container environment is identical
# to the host one created by `uv sync` — dependencies come from pyproject.toml
# + uv.lock, not from a duplicated `pip install` list.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# `time`     -> GNU /usr/bin/time (-v verbose), matching the host workflow.
# `graphviz` -> the `dot` binary, so gprof2dot can render call-graph PNGs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends time graphviz \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (cached layer) — only invalidated when the
# lockfile or pyproject changes, not when source files do.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Then copy the actual source. Edits to julia_set.py reuse the dep layer.
COPY chapter_2/ chapter_2/

# Make `uv run` skip its sync/check step on every invocation.
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_FROZEN=1

# Default: run the Julia set under GNU time's verbose output.
ENTRYPOINT ["/usr/bin/time", "-v", "uv", "run", "python", "chapter_2/julia_set.py"]
