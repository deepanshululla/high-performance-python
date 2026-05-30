"""Convert a cProfile stats file into a self-contained, interactive
d3-flame-graph HTML page (click-to-zoom, hover tooltips, search).

Usage: python build_flame_html.py julia.prof julia_flame_interactive.html
"""
import json
import os
import sys
from collections import defaultdict
import pstats


def short(func):
    file, line, fn = func
    base = os.path.basename(file) if file not in ("~", "") else file
    return f"{fn}  ({base}:{line})" if line else f"{fn}  [{base}]"


def build_tree(prof_path):
    p = pstats.Stats(prof_path)
    stats = getattr(p, "stats")  # {func: (cc, nc, tt, ct, callers{caller:(cc,nc,tt,ct)})}

    # Invert callers -> callees, carrying the sub-call cumulative time (sct).
    callees = defaultdict(list)
    totals = {}
    for func, entry in stats.items():
        ct = entry[3]              # cumulative time
        callers = entry[4]         # {caller: (cc, nc, tt, ct)}
        totals[func] = ct
        for caller, sub in callers.items():
            sct = sub[3] if isinstance(sub, tuple) else float(sub)  # caller's sub-cumtime
            callees[caller].append((func, sct))

    def node(func, value, path):
        n = {"name": short(func), "value": max(float(value), 1e-9)}
        kids = [node(c, sct, path | {c})
                for c, sct in callees.get(func, []) if c not in path]  # break cycles
        if kids:
            n["children"] = kids
        return n

    # Root at the highest-cumulative-time frame — the real entry point
    # (exec/<module>), not a tiny import-bootstrap leaf with no callers.
    root = max(totals, key=lambda f: totals[f])
    tree = node(root, totals[root], {root})
    tree["name"] = f"{short(root)}  —  {totals[root]:.3f}s total"
    return tree


def main():
    prof = sys.argv[1] if len(sys.argv) > 1 else "julia.prof"
    out = sys.argv[2] if len(sys.argv) > 2 else "julia_flame_interactive.html"
    # Resolve assets next to this script, so it works from any working directory.
    assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".viz-assets")

    data = build_tree(prof)

    def read(name):
        with open(os.path.join(assets, name)) as f:
            return f.read()

    d3 = read("d3.min.js")
    fg = read("d3-flamegraph.min.js")
    tip = read("d3-flamegraph-tooltip.min.js")
    css = read("d3-flamegraph.css")

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Julia set — interactive flame graph ({os.path.basename(prof)})</title>
<style>
{css}
body{{font-family:-apple-system,Segoe UI,Arial,sans-serif;margin:16px;background:#fff;color:#222}}
h1{{font-size:16px;margin:0 0 2px}}
p{{color:#555;font-size:13px;margin:0 0 10px}}
#controls{{margin:8px 0}}
input{{padding:4px 8px;font-size:13px;width:240px}}
button{{padding:4px 10px;font-size:13px;margin-left:6px;cursor:pointer}}
#chart{{margin-top:6px}}
</style></head>
<body>
<h1>Julia set — interactive cProfile flame graph</h1>
<p>Source: {os.path.basename(prof)} &nbsp;·&nbsp; width = cumulative time &nbsp;·&nbsp;
click a frame to zoom, hover for details, type to search.</p>
<div id="controls">
  <input id="term" type="text" placeholder="search (e.g. abs)…">
  <button onclick="search()">Search</button>
  <button onclick="clear_()">Clear</button>
  <button onclick="reset()">Reset zoom</button>
</div>
<div id="chart"></div>

<script>{d3}</script>
<script>{fg}</script>
<script>{tip}</script>
<script>
var data = {json.dumps(data)};
var tip = flamegraph.tooltip.defaultFlamegraphTooltip()
  .html(function(d){{return d.data.name + "<br>cumulative: " + d.data.value.toFixed(4) + " s";}});
var chart = flamegraph()
  .width(Math.max(960, window.innerWidth - 40))
  .cellHeight(18)
  .transitionDuration(400)
  .minFrameSize(1)
  .tooltip(tip)
  .sort(true);
d3.select("#chart").datum(data).call(chart);
function search(){{ chart.search(document.getElementById('term').value); }}
function clear_(){{ chart.clear(); document.getElementById('term').value=''; }}
function reset(){{ chart.resetZoom(); }}
document.getElementById('term').addEventListener('keyup', function(e){{ if(e.key==='Enter') search(); }});
window.addEventListener('resize', function(){{ chart.width(Math.max(960, window.innerWidth-40)); chart.update(); }});
</script>
</body></html>"""

    with open(out, "w") as f:
        f.write(html)
    print(f"wrote {out}: {len(html)} bytes, root value {data['value']:.3f}s, "
          f"{len(data['children'])} root child(ren)")


if __name__ == "__main__":
    main()
