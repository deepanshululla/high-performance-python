"""ex09 — a real OCR pipeline: render (CPU) -> OCR with `claude -p` (I/O) -> analyze (CPU).

This takes the chapter's CPU+I/O lesson off the synthetic delay-server and onto a real,
three-stage workload. Each page of a PDF is rasterized to an image (CPU), transcribed by a real
`claude -p --model haiku` call (I/O — a separate process, seconds per page), and the transcript
is analyzed (CPU). We run the whole document two ways — strictly serial, and as an async
pipeline that overlaps many OCR calls — and compare against the serial baseline.

Because the OCR stage is a real LLM call, the timings are **single-run and nondeterministic**:
they depend on the model, the network, and the machine, and will differ every run. We capture
one real run into `results.json`, and the chart + README are built from that. The reproducible
lesson is the *shape* — OCR I/O dominates, so overlapping it is almost the whole game — not the
exact seconds.

Run a real capture (spends tokens):
    .venv/bin/python chapter_9_asynchronous_io/ex09_ocr_pipeline/ex09_ocr_pipeline.py --pages 6 --concurrency 4
"""
import argparse
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root
sys.path.insert(0, str(HERE.parents[0]))   # chapter dir

import _ocr  # noqa: E402

PDF = HERE / "sample.pdf"
RENDER_DIR = HERE / "pages"            # gitignored scratch for rendered PNGs
RESULTS = HERE / "results.json"


def aggregate(pages):
    """Merge per-page stats into a document-level summary."""
    total_words = sum(p["stats"]["words"] for p in pages)
    total_code = sum(p["stats"]["code_tokens"] for p in pages)
    merged = collections.Counter()
    for p in pages:
        merged.update(dict(p["stats"]["top_terms"]))
    return {
        "total_words": total_words,
        "total_code_tokens": total_code,
        "doc_top_terms": merged.most_common(10),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=6, help="number of pages from the front")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--model", default=_ocr.OCR_MODEL)
    args = parser.parse_args()
    _ocr.OCR_MODEL = args.model

    page_indices = list(range(args.pages))
    print(f"OCR pipeline: {args.pages} pages of {PDF.name}, model={args.model}")

    print("  running serial baseline (render -> OCR -> analyze, in sequence)...")
    serial = _ocr.run_serial(PDF, page_indices, RENDER_DIR)
    print(f"    serial total: {serial['total']:.1f}s  "
          f"(OCR {serial['stages']['ocr']:.1f}s, render {serial['stages']['render']:.2f}s, "
          f"analyze {serial['stages']['analyze']:.3f}s)")

    print(f"  running async pipeline (concurrency={args.concurrency})...")
    asy = _ocr.run_async(PDF, page_indices, RENDER_DIR, concurrency=args.concurrency)
    print(f"    async total: {asy['total']:.1f}s")

    speedup = serial["total"] / asy["total"]
    agg = aggregate(serial["pages"])
    out = {
        "pdf": PDF.name, "n_pages": args.pages, "model": args.model,
        "serial": {"total": serial["total"], "stages": serial["stages"]},
        "async": {"total": asy["total"], "concurrency": args.concurrency},
        "speedup": speedup,
        "aggregate": agg,
    }
    RESULTS.write_text(json.dumps(out, indent=2))

    io_share = 100 * serial["stages"]["ocr"] / serial["total"]
    print(f"\n  speedup (serial / async): {speedup:.2f}x")
    print(f"  OCR I/O was {io_share:.0f}% of serial time")
    print(f"  document: {agg['total_words']} words, {agg['total_code_tokens']} code-ish tokens")
    print(f"  top terms: {', '.join(t for t, _ in agg['doc_top_terms'][:6])}")
    print(f"  wrote {RESULTS.name}")


if __name__ == "__main__":
    main()
