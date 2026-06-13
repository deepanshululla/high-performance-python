"""Shared OCR-pipeline machinery: render a PDF page, OCR it with real `claude -p`, analyze it.

This is the chapter's "real" CPU+I/O workload, as opposed to the synthetic delay-server in
`_server.py`. Each page flows through three stages with genuinely different performance
characters:

1. `render_page`  — rasterize one PDF page to a PNG with pypdfium2. **CPU-bound**: it runs in
   Python/C, holds the GIL, and finishes in tens of milliseconds.
2. `ocr_page` / `ocr_page_async` — shell out to `claude -p --model haiku` to transcribe the
   image. **I/O-bound**: the work happens in a separate process (and across the network to the
   model), so the calling thread/event loop is free while it runs. This is the slow stage,
   seconds per page.
3. `analyze_text` — count words, characters, unique terms, and code-ish tokens in the
   transcript. **CPU-bound** and light.

Because stage 2 is a real LLM call, every number it produces is **single-run and
nondeterministic** — it depends on the model, the network, and the machine. We capture one real
run into a `results.json` and build the charts/READMEs from that, rather than re-calling the
model on every `viz`/`smoke`. The reproducible lesson is the *structure* (how much of the serial
OCR wait an async pipeline can hide), not the exact seconds.

The verified invocation is `echo "<prompt>" | claude -p --model haiku --allowedTools Read`; the
prompt references the PNG by absolute path and Claude reads it with its Read tool.
"""
import asyncio
import collections
import pathlib
import re
import subprocess
import time

import pypdfium2 as pdfium

OCR_MODEL = "haiku"
RENDER_SCALE = 2.0   # 2x gives ~1440px-wide pages — enough for clean OCR
CPU_ROUNDS = 3       # repeats of the heavy analysis pass; the knob for CPU-per-page
VOCAB_SIZE = 700     # analysis vocabulary is padded/truncated to this (~3s CPU/page at rounds=3)
_PROMPT = (
    "Transcribe ALL text visible in the image file at {png}. "
    "Output only the raw transcribed text with no commentary, headers, or markdown fences."
)


def render_page(pdf_path, page_idx, out_dir, scale=RENDER_SCALE):
    """CPU stage: rasterize one PDF page to a PNG and return its path."""
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"page_{page_idx:03d}.png"
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        img = pdf[page_idx].render(scale=scale).to_pil()
        img.save(png)
    finally:
        pdf.close()
    return str(png)


def _claude_argv(png_path):
    # Prompt is passed as a positional arg (not stdin): a CPU-busy event loop can stall a
    # subprocess's stdin long enough to trip claude's "no stdin in 3s" timeout, so we avoid
    # stdin entirely and close it.
    return ["claude", "-p", _PROMPT.format(png=png_path),
            "--model", OCR_MODEL, "--allowedTools", "Read"]


def ocr_page(png_path):
    """I/O stage (synchronous): transcribe a PNG with `claude -p`. Used by the serial runner."""
    proc = subprocess.run(
        _claude_argv(png_path), stdin=subprocess.DEVNULL,
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p failed: {proc.stderr[:200]}")
    return proc.stdout.strip()


async def ocr_page_async(png_path):
    """I/O stage (async): same call via create_subprocess_exec so many run concurrently."""
    proc = await asyncio.create_subprocess_exec(
        *_claude_argv(png_path),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p failed: {err.decode()[:200]}")
    return out.decode().strip()


_WORD = re.compile(r"[A-Za-z][A-Za-z'-]+")
_CODEISH = re.compile(r"[{}();=<>]|\bconst\b|\blet\b|\bimport\b|\buseState\b|\buseEffect\b")


def _levenshtein(a, b):
    """Classic DP edit distance — deliberately pure Python so it holds the GIL."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def _build_vocab(words, size):
    """A stable-size vocabulary from the transcript: real words padded with char-trigrams.

    OCR'd pages vary wildly in length (a title page vs. a dense code page), which would make
    a text-size-driven CPU stage swing all over. Padding to a fixed `size` with character
    n-grams keeps the analysis cost steady per page while staying derived from the real text.
    """
    vocab = list(dict.fromkeys(w.lower() for w in words))   # unique, order-preserving
    if len(vocab) >= size:
        return vocab[:size]
    blob = "".join(words).lower() or "reactbestpractices"
    grams = [blob[i:i + 3] for i in range(len(blob) - 2)]
    i = 0
    while len(vocab) < size and grams:
        vocab.append(grams[i % len(grams)] + str(i))   # keep them distinct
        i += 1
    return vocab[:size]


def analyze_text(text, cpu_rounds=None, vocab_size=None):
    """CPU stage: real keyword-cluster analysis (all-pairs edit distance), heavy on purpose.

    Beyond the light stats, we compute pairwise Levenshtein similarity across a fixed-size
    vocabulary and count near-duplicate term pairs (typos / variants / shared stems). This is
    O(V^2 * L) pure-Python work — a genuine, GIL-holding CPU load that stands in for the kind of
    analysis you might run on extracted text, and whose cost is tunable via `cpu_rounds`.
    """
    cpu_rounds = CPU_ROUNDS if cpu_rounds is None else cpu_rounds
    vocab_size = VOCAB_SIZE if vocab_size is None else vocab_size
    words = _WORD.findall(text)
    lower = [w.lower() for w in words]
    freq = collections.Counter(lower)

    vocab = _build_vocab(words, vocab_size)
    near_dupes = 0
    for _ in range(cpu_rounds):
        near_dupes = 0
        for i in range(len(vocab)):
            vi = vocab[i]
            for j in range(i + 1, len(vocab)):
                vj = vocab[j]
                d = _levenshtein(vi, vj)
                if d <= max(1, min(len(vi), len(vj)) // 3):
                    near_dupes += 1
    return {
        "chars": len(text),
        "words": len(words),
        "unique_words": len(freq),
        "code_tokens": len(_CODEISH.findall(text)),
        "avg_word_len": round(sum(len(w) for w in words) / max(1, len(words)), 2),
        "near_dupe_pairs": near_dupes,
        "top_terms": freq.most_common(8),
    }


# --- pipeline runners ------------------------------------------------------------------------

def process_page_blocking(args):
    """Whole pipeline for ONE page, fully blocking — the unit of work for pure multiprocessing.

    A top-level function (picklable) so `ProcessPoolExecutor`/`multiprocessing.Pool` can run it
    in a worker. Each worker does its own render (CPU), its own blocking `claude -p` (I/O — note
    the worker simply waits during it, no overlap *within* the worker), and its own analyze
    (CPU). Parallelism comes entirely from running several pages in several processes at once.
    """
    pdf_path, idx, render_dir = args
    png = render_page(pdf_path, idx, render_dir)
    text = ocr_page(png)
    return {"page": idx, "stats": analyze_text(text)}


def run_serial(pdf_path, page_indices, render_dir):
    """Baseline: render -> OCR -> analyze each page strictly in sequence."""
    stages = {"render": 0.0, "ocr": 0.0, "analyze": 0.0}
    per_page = []
    t0 = time.perf_counter()
    for idx in page_indices:
        a = time.perf_counter()
        png = render_page(pdf_path, idx, render_dir)
        b = time.perf_counter()
        text = ocr_page(png)
        c = time.perf_counter()
        stats = analyze_text(text)
        d = time.perf_counter()
        stages["render"] += b - a
        stages["ocr"] += c - b
        stages["analyze"] += d - c
        per_page.append({"page": idx, "stats": stats})
    total = time.perf_counter() - t0
    return {"mode": "serial", "total": total, "stages": stages, "pages": per_page}


async def _handle_page(pdf_path, idx, render_dir, sem):
    png = render_page(pdf_path, idx, render_dir)     # CPU (holds GIL; serializes vs other CPU)
    async with sem:
        text = await ocr_page_async(png)             # I/O (overlaps other pages' OCR)
        await asyncio.sleep(0)
    stats = analyze_text(text)                        # CPU
    return {"page": idx, "stats": stats}


async def _run_async(pdf_path, page_indices, render_dir, concurrency):
    sem = asyncio.Semaphore(concurrency)
    tasks = [_handle_page(pdf_path, idx, render_dir, sem) for idx in page_indices]
    return await asyncio.gather(*tasks)


def run_async(pdf_path, page_indices, render_dir, concurrency=4):
    """Async pipeline: OCR subprocesses overlap across pages, bounded by `concurrency`."""
    t0 = time.perf_counter()
    pages = asyncio.run(_run_async(pdf_path, page_indices, render_dir, concurrency))
    total = time.perf_counter() - t0
    return {"mode": f"async(c={concurrency})", "total": total,
            "concurrency": concurrency, "pages": pages}
