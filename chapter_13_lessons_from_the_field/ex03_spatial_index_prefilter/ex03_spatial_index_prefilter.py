"""ex03 — approximate-then-exact: a spatial index turns O(N) geometry into a quick lookup.

David Rawlinson's example: intersect every dwelling on a national map against query regions
(flood zones, land-use overlays) fast enough for a synchronous web request. Testing exact
polygon-against-polygon for billions of combinations is hopeless. His recipe is to design a
fast *approximate* filter with a false-positive bias — it may return too many shapes but
never misses one — run the exact (expensive) test only on what survives, and precompute a
spatial index so the filter itself is sub-linear.

We reproduce the three rungs of that ladder against N small dwelling polygons and a batch of
query regions:

  1. exact-all      — run the exact polygon intersection test against every dwelling.
  2. bbox prefilter — a cheap bounding-box overlap test (the false-positive-biased approx)
                      first, then the exact test only on the boxes that overlap.
  3. spatial index  — an STRtree built once over the dwellings; query it per region for the
                      candidates whose bounding boxes intersect, then confirm exactly.

All three must return the identical set of intersecting dwellings per query (the anchor):
the approximations only ever *add* candidates that the exact test then removes.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf

import numpy as np  # noqa: E402
import shapely  # noqa: E402
from shapely import STRtree, box  # noqa: E402

from perf import time_s  # noqa: E402

N_SHAPES = 20_000
N_QUERIES = 50
WORLD = 1000.0


def _make_shapes(seed=0):
    rng = np.random.default_rng(seed)
    # Dwellings: small ~32-vertex blobs scattered over the world. Non-trivial polygons so the
    # exact intersection test is meaningfully more expensive than a bounding-box compare.
    cx = rng.uniform(0, WORLD, N_SHAPES)
    cy = rng.uniform(0, WORLD, N_SHAPES)
    r = rng.uniform(0.5, 2.0, N_SHAPES)
    dwellings = shapely.points(cx, cy)
    dwellings = shapely.buffer(dwellings, r, quad_segs=8)
    # Query regions: larger boxes (flood zones), each covering a small slice of the world.
    qx = rng.uniform(0, WORLD - 40, N_QUERIES)
    qy = rng.uniform(0, WORLD - 40, N_QUERIES)
    regions = [box(x, y, x + 30, y + 30) for x, y in zip(qx, qy)]
    return dwellings, regions


def match_exact(dwellings, regions):
    """Exact polygon intersection against every dwelling, per region (O(N) per query)."""
    return [set(np.nonzero(shapely.intersects(region, dwellings))[0].tolist())
            for region in regions]


def match_bbox(dwellings, regions, bounds):
    """Cheap bbox-overlap prefilter (false-positive biased), then exact on survivors."""
    minx, miny, maxx, maxy = bounds.T
    out = []
    for region in regions:
        rminx, rminy, rmaxx, rmaxy = region.bounds
        # Two axis-aligned boxes overlap iff they overlap on both axes — pure numpy, no geometry.
        overlap = (minx <= rmaxx) & (maxx >= rminx) & (miny <= rmaxy) & (maxy >= rminy)
        cand = np.nonzero(overlap)[0]
        keep = cand[shapely.intersects(region, dwellings[cand])]
        out.append(set(keep.tolist()))
    return out


def match_index(tree, regions):
    """STRtree: query returns bbox-candidate indices, predicate confirms them exactly."""
    return [set(tree.query(region, predicate="intersects").tolist()) for region in regions]


def measure(seed=0):
    dwellings, regions = _make_shapes(seed)
    bounds = shapely.bounds(dwellings)          # N x 4 (minx, miny, maxx, maxy)
    tree = STRtree(dwellings)                   # built once, reused for every query

    exact = match_exact(dwellings, regions)
    bbox = match_bbox(dwellings, regions, bounds)
    index = match_index(tree, regions)
    assert exact == bbox == index, "a prefiltered path disagreed with the exact result!"

    t_exact = time_s(lambda: match_exact(dwellings, regions), number=1, repeat=3)
    t_bbox = time_s(lambda: match_bbox(dwellings, regions, bounds), number=1, repeat=3)
    t_index = time_s(lambda: match_index(tree, regions), number=1, repeat=3)
    n_hits = sum(len(s) for s in exact)
    return {
        "n_shapes": N_SHAPES, "n_queries": N_QUERIES, "n_hits": n_hits,
        "exact_s": t_exact, "bbox_s": t_bbox, "index_s": t_index,
        "bbox_speedup": t_exact / t_bbox, "index_speedup": t_exact / t_index,
    }


def main():
    m = measure()
    print(f"{m['n_queries']} regions vs {m['n_shapes']:,} dwelling polygons "
          f"({m['n_hits']} intersections):\n")
    print(f"  exact-all      : {m['exact_s']*1e3:8.2f} ms   1.0x")
    print(f"  bbox prefilter : {m['bbox_s']*1e3:8.2f} ms   {m['bbox_speedup']:.1f}x")
    print(f"  spatial index  : {m['index_s']*1e3:8.2f} ms   {m['index_speedup']:.1f}x")


if __name__ == "__main__":
    main()
