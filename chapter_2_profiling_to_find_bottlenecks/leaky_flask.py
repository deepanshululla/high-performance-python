"""Flask memory-leak demo wrapped in real Dozer middleware (WSGI).

Dozer is WSGI middleware, so it wraps a Flask app directly. It samples the live
object graph (via gc) on a timer and serves a UI at /_dozer/ showing each type's
object count over time — a type climbing monotonically = a leak.

Run it:
    uv run python leaky_flask.py            # from chapter_2/, serves on :8000

Drive a leak and inspect:
    curl localhost:8000/leak?n=1000         # repeat many times
    open  http://localhost:8000/_dozer/     # Dozer UI: object counts over time
"""
from flask import Flask, jsonify
from dozer import Dozer

app = Flask(__name__)

# THE LEAK: a global that grows on every /leak request and is never cleared.
_LEAKED: list = []


class Widget:
    """Object we deliberately accumulate so Dozer's gc counts climb visibly."""
    def __init__(self, i: int):
        self.i = i
        self.payload = [i] * 1000


@app.route("/leak")
def leak():
    from flask import request
    n = int(request.args.get("n", 1000))
    _LEAKED.extend(Widget(i) for i in range(n))
    return jsonify(leaked_now=n, total_held=len(_LEAKED))


@app.route("/healthy")
def healthy():
    from flask import request
    n = int(request.args.get("n", 1000))
    tmp = [Widget(i) for i in range(n)]      # created then dropped — no leak
    return jsonify(created_and_freed=len(tmp))


@app.route("/")
def index():
    return jsonify(hello="see /_dozer/ for the memory UI; hit /leak to grow it")


# Wrap the WSGI app with Dozer — this adds the /_dozer/ introspection UI.
app.wsgi_app = Dozer(app.wsgi_app)

if __name__ == "__main__":
    # threaded=False keeps a single worker so Dozer sees one consistent heap.
    app.run(host="127.0.0.1", port=8000, threaded=False)
