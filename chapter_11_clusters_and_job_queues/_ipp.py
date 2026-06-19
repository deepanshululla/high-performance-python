"""IPython Parallel cluster lifecycle, shared by the ex01-ex03 cluster exercises.

Starting a cluster is not free: `ipcluster` spins up a controller (the hub + the
schedulers) and then N engine processes, each a full IPython kernel that connects
back over ZeroMQ. On this machine that handshake takes several seconds — a cost
worth measuring once (ex01) and then amortising by reusing the same cluster for
every measurement in a script.

`local_cluster(n)` is a context manager that starts n engines, blocks until all n
have connected, yields the connected `Client`, and guarantees teardown. Every
cluster exercise wraps its measurements in one `with` block so the startup cost is
paid once and the engines are always cleaned up, even on an assertion failure.

The book drives the cluster from the `ipcluster start -n 4` CLI plus an
interactive IPython session (Examples 11-1..11-5). We do the same thing
programmatically so it runs as a plain script: `ipyparallel.Cluster(n=...)` is the
API behind that CLI.
"""
import contextlib
import pathlib
import time

import ipyparallel as ipp

HERE = pathlib.Path(__file__).resolve().parent


def prepare_engines(rc):
    """Make the shared `_cluster` module importable inside every engine.

    Engines start in their own working directory and import nothing from this
    repo. IPython Parallel sends a worker function defined in a named module
    *by reference* — the engine re-imports the module and looks the function up —
    so the engines must be able to `import _cluster`. We run a one-line import on
    every engine to put the chapter directory on their path and load the module;
    after this, any `_cluster` callable (`estimate_pi_block`, `pi_block_with_pid`,
    `noop`, `inc`) resolves on the engines. This mirrors the book's
    `dview.sync_imports()` (Example 11-2): the engines must import what the driver
    imported.
    """
    rc[:].execute(
        f"import sys; sys.path.insert(0, {str(HERE)!r}); import _cluster"
    ).get()


@contextlib.contextmanager
def local_cluster(n, return_startup=False):
    """Start n local engines, yield a connected Client (and optionally startup secs).

    Usage:
        with local_cluster(4) as rc:
            rc[:].apply_sync(fn, arg)

        with local_cluster(4, return_startup=True) as (rc, startup_s):
            ...  # startup_s is the wall-clock cost of bringing the cluster up
    """
    t0 = time.perf_counter()
    cluster = ipp.Cluster(n=n)
    rc = cluster.start_and_connect_sync()
    rc.wait_for_engines(n, timeout=60)
    startup_s = time.perf_counter() - t0
    try:
        yield (rc, startup_s) if return_startup else rc
    finally:
        rc.close()
        cluster.stop_cluster_sync()
