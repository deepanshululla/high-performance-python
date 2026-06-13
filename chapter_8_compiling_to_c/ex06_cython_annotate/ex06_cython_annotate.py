"""Chapter 8 - Exercise 6: reading the Cython annotation report (`cython -a`) as data.

Task: the chapter calls the annotation report "your targeting system" -- run `cython -a`
and Cython emits an HTML file that shades each line by how much it calls back into the
Python virtual machine (yellow = lots of VM, white = pure C). The eye-balling version is
in the book; here we parse the per-line *score* Cython embeds in that HTML
(`class="cython line score-N"`) so the shading becomes a number you can assert on.

We annotate two versions of the Julia loop -- `plain` (unannotated) and `typed` (cdef C
scalars + expanded math) -- and show the score collapse on exactly the lines that matter:
the inner-loop `while` and the `z = z*z + c` update, run tens of millions of times. The
outer-loop setup lines stay shaded in both, which is the chapter's other point: shaded
lines outside tight loops don't cost much, so don't waste effort whitening them.

Run: .venv/bin/python chapter_8_compiling_to_c/ex06_cython_annotate/ex06_cython_annotate.py
"""
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
PYX = HERE.parent / "annot.pyx"
HTML = HERE.parent / "annot.html"

# Source-text markers for the hot inner-loop lines (run ~30M times per grid).
INNER_MARKERS = ("while ", "z = z * z + c", "n += 1", "z.real")


def annotate():
    """Run `cython -a annot.pyx`, producing annot.html (the report the chapter views)."""
    subprocess.run([sys.executable, "-m", "cython", "-a", str(PYX),
                    "-o", str(HERE.parent / "annot.c")], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def parse_scores():
    """Return {source_line_no: vm_score} from the annotation HTML.

    Cython tags each source line `<pre class="cython line score-N" ...>N: code</pre>`,
    where the leading N (before the colon) is the line number and score-N is how many
    calls into the CPython API that line generates -- its 'shadedness'.
    """
    html = HTML.read_text()
    scores = {}
    # Each source line: <pre class="cython line score-N" ...>+<span class="">LINENO</span>: ...
    # (The expanded C uses `cython code score-N` in single quotes, which this won't match.)
    pat = r'class="cython line score-(\d+)"[^>]*>\+?<span class="">(\d+)</span>:'
    for m in re.finditer(pat, html):
        score, lineno = int(m.group(1)), int(m.group(2))
        scores[lineno] = score
    return scores


def function_ranges(src_lines):
    """Map 'plain'/'typed' to the (start, end) source-line range of each def."""
    starts = {}
    for i, line in enumerate(src_lines, start=1):
        if line.startswith("def plain"):
            starts["plain"] = i
        elif line.startswith("def typed"):
            starts["typed"] = i
    ordered = sorted(starts.items(), key=lambda kv: kv[1])
    ranges = {}
    for idx, (name, start) in enumerate(ordered):
        end = ordered[idx + 1][1] - 1 if idx + 1 < len(ordered) else len(src_lines)
        ranges[name] = (start, end)
    return ranges


def is_inner(text):
    return any(marker in text for marker in INNER_MARKERS)


def collect():
    """Build a per-function breakdown of VM scores: inner-loop vs the rest."""
    annotate()
    scores = parse_scores()
    src_lines = PYX.read_text().splitlines()
    ranges = function_ranges(src_lines)

    result = {}
    for name, (start, end) in ranges.items():
        inner = outer = 0
        hottest = (0, "")
        for lineno in range(start, end + 1):
            sc = scores.get(lineno, 0)
            text = src_lines[lineno - 1].strip()
            if not text or text.startswith(("#", '"""', "def ")):
                continue
            if is_inner(text):
                inner += sc
            else:
                outer += sc
            if sc > hottest[0]:
                hottest = (sc, text)
        result[name] = {"inner": inner, "outer": outer, "total": inner + outer,
                        "hottest": hottest}
    return result


def main():
    r = collect()
    print("Cython annotation scores (VM-interaction per line, summed). Lower = whiter = "
          "more C, less Python VM.\n")
    print(f"  {'version':8s} {'inner-loop':>11s} {'outer/setup':>12s} {'total':>7s}")
    for name in ("plain", "typed"):
        d = r[name]
        print(f"  {name:8s} {d['inner']:11d} {d['outer']:12d} {d['total']:7d}")
        print(f"           hottest line: score {d['hottest'][0]:<3d} `{d['hottest'][1]}`")

    pi, ti = r["plain"]["inner"], r["typed"]["inner"]
    po, to = r["plain"]["outer"], r["typed"]["outer"]
    assert ti < pi, "typing must whiten the inner loop"
    print()
    print(f"  Inner loop: {pi} -> {ti}  ({pi - ti} fewer VM interactions on the >30M-times lines).")
    print(f"  Outer/setup: {po} -> {to}  (still shaded in both -- and that's fine, it runs ~1M times).")
    print("\n  The targeting lesson: typing crushed the inner-loop score (where time lives);")
    print("  the leftover outer-loop shading is the chapter's 'don't bother' zone.")
    print(f"\n  Open the report yourself: {HTML}")


if __name__ == "__main__":
    main()
