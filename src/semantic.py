"""Deterministic semantic candidate selection for edge extraction.

Edge extraction is O(n^2) in principle, so it must sample which claim pairs to show the model.
How that sampling is done decides which edges are *findable at all* — a limit we measured the
hard way (PRIMARY §5): sampling pairs by position works to a few hundred claims and then quietly
stops finding cross-source links. Source-interleaving a 60-claim window covers ~30% of each
source at 202 claims but ~3.8% at 1,590, so interleaved neighbours stop being about the same
subject and there is no relation left to extract.

This module samples by *meaning* instead: TF-IDF over claim text, cosine similarity, and windows
grown around a seed claim from its nearest neighbours in other sources. Every window is then one
topic argued by several documents, which is the only shape in which a cross-source contradiction
is visible.

Deliberately pure Python and deterministic — no model, no key, no embedding service. Candidate
selection is *mechanism*, not judgement, so it belongs on the code side of "the AI proposes; the
code disposes": the model still decides every relation, but which pairs it is asked about is
reproducible from the claims alone. Same input, same windows, byte for byte.
"""

import math
import re

_WORD = re.compile(r"[a-z0-9]+")

# Ordinary English function words, plus discourse verbs and quantifiers ("people", "using",
# "account for", "multiple") that are frequent enough to dominate a short-text cosine score while
# carrying no subject matter. Without the second group, windows cohere around the word "using"
# rather than around a topic, and the model is handed unrelated claims to relate.
#
# Every entry must be checked against the corpus vocabulary before being added: this list is
# subtractive, so a term wrongly included here becomes permanently invisible to selection.
_STOP = frozenset("""
a an the and or but if then than that this these those there here of in on at to for from by
with without within into onto over under about above below between across is are was were be
been being am do does did doing have has had having will would shall should can could may might
must not no nor only own same so too very just as it its it's they them their we our us you your
he she his her him i me my which who whom whose what when where why how all any both each few
more most other some such one two three also however therefore thus hence rather quite
people person account accounts accounting multiple many much several various given makes make
made making made use used uses using say says said stated state states claim claims claimed
argue argues argued argument arguments evidence case cases point points show shows shown showed
suggest suggests suggested consider considers considered think thinks thought believe believes
believed note notes noted mean means meant find finds found based due likely unlikely probable
probability probabilities possible possibility reason reasons result results resulting
different differences difference specific specifically particular particularly general generally
actually really simply merely still even yet already often usually always never sometimes
first second third last next another others whether because since while during before after
number numbers amount level levels kind kinds type types thing things way ways fact facts
""".split())

_MIN_TOKEN_LEN = 3
# A term appearing in more than this fraction of claims is corpus-wide boilerplate, not a topic.
_MAX_DF_RATIO = 0.28


def tokenize(text):
    return [t for t in _WORD.findall((text or "").lower())
            if len(t) >= _MIN_TOKEN_LEN and t not in _STOP]


def tfidf_vectors(texts):
    """L2-normalised sparse TF-IDF vectors, as a list of {term: weight} dicts."""
    docs = [tokenize(t) for t in texts]
    n = len(docs) or 1

    df = {}
    for toks in docs:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1

    cap = max(2, int(_MAX_DF_RATIO * n))
    vectors = []
    for toks in docs:
        tf = {}
        for t in toks:
            if df.get(t, 0) > cap:
                continue
            tf[t] = tf.get(t, 0) + 1
        vec = {}
        for t, c in tf.items():
            # sublinear tf damps repetition; smoothed idf keeps weights finite for df == n
            vec[t] = (1.0 + math.log(c)) * math.log((1.0 + n) / (1.0 + df[t]))
        norm = math.sqrt(sum(w * w for w in vec.values()))
        vectors.append({t: w / norm for t, w in vec.items()} if norm else {})
    return vectors


def _inverted_index(vectors):
    inv = {}
    for i, vec in enumerate(vectors):
        for t in vec:
            inv.setdefault(t, []).append(i)
    return inv


def _neighbours(i, vectors, inv):
    """Cosine similarity of claim i against every claim sharing at least one term with it.

    The inverted index keeps this near-linear in practice: rare terms have short postings, and
    corpus-wide terms were already dropped from the vectors by the document-frequency cap.
    """
    scores = {}
    vi = vectors[i]
    for t, w in vi.items():
        for j in inv.get(t, ()):
            if j != i:
                scores[j] = scores.get(j, 0.0) + w * vectors[j].get(t, 0.0)
    return scores


def semantic_groups(items, source_of, window=60, min_sim=0.06, cross_fraction=0.7,
                    text_of=lambda x: x["text"], seed_if=None):
    """Group items into topically-coherent, cross-source-rich windows.

    Each group is seeded on a not-yet-grouped item and filled with its nearest neighbours,
    reserving `cross_fraction` of the window for items from *other* sources so the model is
    always shown the same subject as argued by different documents. Same-source neighbours fill
    the remainder, which preserves within-document reasoning chains inside the topic.

    Every item seeds at most one group, but an item may appear in several groups as a neighbour —
    that overlap is deliberate: it is how a claim connecting two topics gets related to both.

    `seed_if` restricts which items may *start* a group without restricting who may join one.
    Seeding on the warrant-bearing kinds (conclusions and inferences) concentrates the windows on
    the structure the audit actually measures, while leaving evidence claims free to be pulled in
    as neighbours — which is what an `is_evidence_for` edge needs.

    Returns a list of lists of items, in deterministic order.
    """
    if not items:
        return []
    vectors = tfidf_vectors([text_of(x) for x in items])
    inv = _inverted_index(vectors)
    sources = [source_of(x) for x in items]

    n_cross = max(1, int(round((window - 1) * cross_fraction)))
    grouped, groups = set(), []

    for seed in range(len(items)):
        if seed in grouped:
            continue
        if seed_if is not None and not seed_if(items[seed]):
            continue
        scores = _neighbours(seed, vectors, inv)
        ranked = sorted(((s, j) for j, s in scores.items() if s >= min_sim),
                        key=lambda sj: (-sj[0], sj[1]))

        cross = [j for _, j in ranked if sources[j] != sources[seed]][:n_cross]
        taken = set(cross)
        same = [j for _, j in ranked
                if sources[j] == sources[seed] and j not in taken][:window - 1 - len(cross)]

        members = [seed] + cross + same
        if len(members) < 2:
            grouped.add(seed)
            continue
        grouped.update(members)
        groups.append([items[k] for k in members])

    return groups


def group_stats(groups, source_of):
    """Per-group source diversity — the number that says whether selection actually worked."""
    if not groups:
        return {"groups": 0, "mean_size": 0.0, "mean_sources": 0.0, "single_source_groups": 0}
    sizes = [len(g) for g in groups]
    per = [len({source_of(x) for x in g}) for g in groups]
    return {
        "groups": len(groups),
        "mean_size": round(sum(sizes) / len(sizes), 1),
        "mean_sources": round(sum(per) / len(per), 2),
        "single_source_groups": sum(1 for p in per if p < 2),
    }
