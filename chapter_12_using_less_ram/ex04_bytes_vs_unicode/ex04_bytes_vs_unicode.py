"""ex04 — what a Python string actually costs, and PEP 393's flexible width.

Since Python 3.3 (PEP 393) a `str` does not store every character in a fixed number
of bytes. CPython inspects the widest character in the string and picks the *smallest*
representation that fits: 1 byte per character if every character is Latin-1, 2 bytes
if the widest is in the Basic Multilingual Plane, and 4 bytes if there is an astral
character (emoji, rare scripts). So an all-ASCII string is as cheap per character as a
`bytes` object, but a single emoji anywhere in the string quadruples the per-character
cost of the *whole* string.

We build a 100-million-character string out of four different characters and weigh each
one's peak resident memory, plus a `bytes` baseline. The per-character cost should step
1 → 1 → 2 → 4 bytes as the character widens, which is PEP 393 made visible.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir -> _mem

from _mem import peak_rss_mib  # noqa: E402

N = 100_000_000   # 100M characters, the book's scale

# (label, single character) — chosen to land in each PEP 393 storage class.
CASES = [
    ("ascii  'a'", "a"),       # Latin-1: 1 byte/char
    ("latin1 'é'", "é"),  # still Latin-1: 1 byte/char
    ("bmp    'Σ'", "Σ"),  # Basic Multilingual Plane: 2 bytes/char
    ("astral '😀'", "\U0001f600"),  # astral plane: 4 bytes/char
]


def build_str(char, n=N):
    """A str of n copies of `char`; its width is chosen by the widest char (here, one)."""
    return char * n


def build_bytes(n=N):
    """A bytes object of n copies of b'a' — always 1 byte/char, the baseline."""
    return b"a" * n


def kind_probes():
    """getsizeof of tiny strings, showing the empty-shell + per-char-width steps."""
    return {
        "'' (empty)": sys.getsizeof(""),
        "'a' (latin1)": sys.getsizeof("a"),
        "'Σ' (ucs2)": sys.getsizeof("Σ"),
        "'😀' (ucs4)": sys.getsizeof("\U0001f600"),
    }


def measure(n=N):
    """Return {label: (peak MiB, bytes/char)} for each string case plus bytes."""
    out = {}
    for label, char in CASES:
        mib = peak_rss_mib(build_str, char, n)
        out[label] = (mib, mib * 1024 * 1024 / n)
    mib_b = peak_rss_mib(build_bytes, n)
    out["bytes  b'a'"] = (mib_b, mib_b * 1024 * 1024 / n)
    return out


def main():
    print("getsizeof of tiny strings (empty shell, then per-character width steps):")
    for label, nbytes in kind_probes().items():
        print(f"  {label:16}: {nbytes} bytes")

    print(f"\npeak RSS to build a {N:,}-character sequence:")
    for label, (mib, bpc) in measure().items():
        print(f"  {label:14}: {mib:7.1f} MiB   (~{bpc:.1f} bytes/char)")
    print("\nPEP 393: the whole string pays for its widest character — one emoji "
          "makes every character cost 4 bytes.")


if __name__ == "__main__":
    main()
