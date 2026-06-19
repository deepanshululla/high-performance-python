"""ex03 — three ways to ask "how big is this object?", and why they disagree.

`sys.getsizeof(obj)` is the built-in, and it has a famous trap: for a container it
reports only the cost of the *container shell*, not its contents. An empty list is
56 bytes and every element adds 8 more — the 8-byte pointer — regardless of how big
the pointed-at objects are. So `getsizeof` of a million-element list of long byte
strings still reports only ~8 MB, wildly undercounting the truth.

`pympler.asizeof` walks the whole object graph and adds up everything it can reach,
giving a far more honest deep size (though it is slow and still only a best guess for
objects that allocate behind C libraries). And the ground truth is the process RSS —
what the operating system actually handed out — which is what `%memit` (and our
`_mem.py`) measures.

We line all three up against a list of 10 million integers. `getsizeof` sees only the
pointer array; `asizeof` and the real RSS see the pointer array *plus* the 10 million
`int` objects it points at, and land ~5x higher.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _mem

from pympler.asizeof import asizeof  # noqa: E402

from _mem import peak_rss_mib  # noqa: E402

N = 10_000_000   # the book's 1e7; asizeof must walk all of them, so this is the slow part
MIB = 1024 * 1024


def build_list(n=N):
    """A list of n distinct ints — pointer array plus n separate int objects."""
    return [x for x in range(n)]


def primitive_probes():
    """getsizeof of small objects, illustrating shell-only / per-element growth."""
    return {
        "int 0": sys.getsizeof(0),
        "int 2**30": sys.getsizeof(2 ** 30),         # crosses into a wider int
        "bytes b''": sys.getsizeof(b""),
        "bytes b'abc'": sys.getsizeof(b"abc"),
        "list []": sys.getsizeof([]),
        "list [1, 2]": sys.getsizeof([1, 2]),
        "list [b'x'*99]": sys.getsizeof([b"x" * 99]),  # one big element, still +8
    }


def measure(n=N):
    """Return the three size estimates (MiB) for a list of n ints."""
    lst = build_list(n)
    shell = sys.getsizeof(lst) / MIB           # container shell only
    deep = asizeof(lst) / MIB                  # deep walk of the whole graph
    del lst
    rss = peak_rss_mib(build_list, n)          # the OS's truth, fresh process
    return {"getsizeof (shell)": shell, "asizeof (deep)": deep, "RSS (truth)": rss}


def main():
    print("getsizeof on small objects (note: it measures the shell, not the contents):")
    for label, nbytes in primitive_probes().items():
        print(f"  {label:18}: {nbytes} bytes")

    print(f"\nsizing a list of {N:,} ints three ways:")
    m = measure()
    for label, mib in m.items():
        print(f"  {label:20}: {mib:7.1f} MiB")
    under = m["RSS (truth)"] / m["getsizeof (shell)"]
    print(f"\ngetsizeof undercounts the real footprint by ~{under:.1f}x — it counts the "
          f"{N:,} pointers but not the {N:,} int objects they point to.")


if __name__ == "__main__":
    main()
