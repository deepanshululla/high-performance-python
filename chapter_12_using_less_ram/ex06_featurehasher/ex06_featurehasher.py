"""ex06 — DictVectorizer vs FeatureHasher: a vocabulary you store vs one you don't.

Text classification turns documents into sparse feature vectors over a vocabulary of
n-grams, and that vocabulary explodes: unigrams, bigrams, and trigrams across a corpus
run to millions of distinct tokens. scikit-learn offers two ways to build the feature
matrix:

* `DictVectorizer` does it losslessly. It makes a first pass to learn the full
  vocabulary (token -> column), then a second pass to fill the matrix. You can invert the
  result back to tokens, but you pay for storing the vocabulary and for two passes, and
  the matrix is as wide as the vocabulary is large.
* `FeatureHasher` does it with a hash. It maps each token straight to one of a *fixed*
  number of columns via MurmurHash3 — no vocabulary, one pass, trivially parallel. Two
  different tokens can collide into the same column, so it is lossy and irreversible.

The book's claim is that the hashed, lossy representation classifies *just as well* as the
lossless one, while building faster and avoiding the vocabulary's memory. We reproduce that
on the 20 Newsgroups corpus: same documents, same n-grams, both vectorizers, then a
`LogisticRegression` on each, comparing matrix width, build time, and test accuracy.

(Scaled to 5 categories and unigrams+bigrams so the classifier trains in seconds rather
than the book's ~500-880 s on the full 20-way, trigram problem. The *parity* between the
two representations is the lesson, not the absolute scores.)
"""
import pathlib
import re
import sys
import time
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root

from sklearn.datasets import fetch_20newsgroups  # noqa: E402
from sklearn.feature_extraction import DictVectorizer, FeatureHasher  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

CATEGORIES = ["sci.med", "comp.graphics", "rec.sport.hockey",
              "talk.politics.guns", "soc.religion.christian"]
NGRAM_MAX = 2                # unigrams + bigrams
N_FEATURES = 2 ** 18         # FeatureHasher's fixed width (262,144 columns)
_TOKEN_RE = re.compile(r"[a-z]{2,}")


def ngram_counts(text, nmax=NGRAM_MAX):
    """Turn a document into a {ngram: count} frequency dict (uni- + bi-grams)."""
    words = _TOKEN_RE.findall(text.lower())
    counts = Counter(words)
    for n in range(2, nmax + 1):
        for i in range(len(words) - n + 1):
            counts[" ".join(words[i:i + n])] += 1
    return counts


def load_docs():
    tr = fetch_20newsgroups(subset="train", categories=CATEGORIES)
    te = fetch_20newsgroups(subset="test", categories=CATEGORIES)
    train = [ngram_counts(d) for d in tr.data]
    test = [ngram_counts(d) for d in te.data]
    return train, tr.target, test, te.target


def _nnz(matrix):
    return int(matrix.nnz)


def run_dictvectorizer(train, y_train, test, y_test):
    dv = DictVectorizer()
    t0 = time.time()
    Xtr = dv.fit_transform(train)        # two passes: learn vocab, then fill
    build_s = time.time() - t0
    Xte = dv.transform(test)
    clf = LogisticRegression(max_iter=1000, n_jobs=-1)
    t1 = time.time()
    clf.fit(Xtr, y_train)
    train_s = time.time() - t1
    score = clf.score(Xte, y_test)
    return {"shape": Xtr.shape, "vocab": len(dv.vocabulary_), "nnz": _nnz(Xtr),
            "build_s": build_s, "train_s": train_s, "score": score}


def run_featurehasher(train, y_train, test, y_test):
    fh = FeatureHasher(n_features=N_FEATURES)
    t0 = time.time()
    Xtr = fh.transform(train)            # one pass, no vocabulary
    build_s = time.time() - t0
    Xte = fh.transform(test)
    clf = LogisticRegression(max_iter=1000, n_jobs=-1)
    t1 = time.time()
    clf.fit(Xtr, y_train)
    train_s = time.time() - t1
    score = clf.score(Xte, y_test)
    return {"shape": Xtr.shape, "vocab": None, "nnz": _nnz(Xtr),
            "build_s": build_s, "train_s": train_s, "score": score}


def measure():
    train, y_train, test, y_test = load_docs()
    return {
        "DictVectorizer": run_dictvectorizer(train, y_train, test, y_test),
        "FeatureHasher": run_featurehasher(train, y_train, test, y_test),
    }


def main():
    m = measure()
    dv, fh = m["DictVectorizer"], m["FeatureHasher"]
    print(f"20 Newsgroups, {len(CATEGORIES)} categories, uni+bigrams:\n")
    for name, d in m.items():
        vocab = f"{d['vocab']:,}" if d["vocab"] else "— (no vocabulary)"
        print(f"  {name}")
        print(f"    matrix {d['shape'][0]}x{d['shape'][1]:,}  nnz {d['nnz']:,}  "
              f"vocab {vocab}")
        print(f"    build {d['build_s']:.2f}s  train {d['train_s']:.2f}s  "
              f"accuracy {d['score']:.3f}")
    print(f"\n  width: DictVectorizer {dv['shape'][1]:,} cols vs FeatureHasher fixed "
          f"{fh['shape'][1]:,}")
    print(f"  accuracy parity: {dv['score']:.3f} vs {fh['score']:.3f}  "
          f"(equivalent), and FeatureHasher needs no stored vocabulary")


if __name__ == "__main__":
    main()
