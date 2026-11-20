"""Baseline duplicate detection and master-record selection.

This is deliberately simple: a reference baseline to improve on and to
measure other methods against. Known limitations:
  * Candidates are grouped by the first character of the normalized name, so
    a typo in the first character would be missed.
  * Similarity is a plain string ratio; it uses no attributes or relationships.
"""
from difflib import SequenceMatcher

from .normalize import normalize_name


def select_master(a, b):
    """Return (master, duplicate): the older record is the master; ties break on id."""
    return (a, b) if (a["created"], a["id"]) <= (b["created"], b["id"]) else (b, a)


def find_duplicate_pairs(cis, threshold=0.92, cls="business_app"):
    items = [(c, normalize_name(c["name"])) for c in cis if c["class"] == cls]
    blocks = {}
    for ci, norm in items:
        blocks.setdefault(norm[:1], []).append((ci, norm))

    pairs = []
    for members in blocks.values():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                (a, na), (b, nb) = members[i], members[j]
                score = 1.0 if na == nb else SequenceMatcher(None, na, nb).ratio()
                if score >= threshold:
                    master, dup = select_master(a, b)
                    pairs.append({"master": master["id"], "duplicate": dup["id"],
                                  "score": round(score, 3)})
    return pairs
