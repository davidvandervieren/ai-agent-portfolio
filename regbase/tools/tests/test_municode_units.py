#!/usr/bin/env python3
"""content_units() must yield one unit per chapter whatever shape the tree
arrives in, and never a section.

A live Greeley harvest fetched 2,694 records with 189 distinct bodies:
sections were chosen as units, and CodesContent answers with the enclosing
chapter for any node, so each chapter was stored once per section. The tree
shapes below are the ones that produced that - and the clean one for
contrast. Every shape must reduce to exactly its chapters.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import municode  # noqa: E402

N = municode.Node


def link(parent, *kids):
    for k in kids:
        k.depth = parent.depth + 1
        parent.children.append(k)
    return [parent, *kids]


def ids(units):
    return sorted(u.node_id for u in units)


def main() -> int:
    failed = 0

    def check(label, ok):
        nonlocal failed
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        failed += not ok

    root = N("18000", "Municipal Code")

    def title():
        return N("T_TIT24", "Title 24")     # fresh per case; children accumulate otherwise

    # Clean hierarchy: chapter -> sections.
    ch10 = N("T_TIT24_CH10", "Chapter 10")
    nodes = [root] + link(title(), ch10) + link(ch10, N("T_TIT24_CH10_S24-1100", "s"),
                                              N("T_TIT24_CH10_S24-1102", "s"))
    check("clean: one unit, the chapter", ids(municode.content_units(nodes)) == ["T_TIT24_CH10"])

    # Mixed: chapter holds an article AND direct sections.
    ch11 = N("T_TIT24_CH11", "Chapter 11")
    art = N("T_TIT24_CH11_ARTI", "Article I")
    nodes = [root] + link(title(), ch11) + link(ch11, art, N("T_TIT24_CH11_S24-1102OIGA", "oil and gas")) \
            + link(art, N("T_TIT24_CH11_ARTI_S24-1150", "s"))
    got = ids(municode.content_units(nodes))
    check("mixed: chapter and article are units, sections are not",
          got == ["T_TIT24_CH11", "T_TIT24_CH11_ARTI"])

    # Flattened: the title probe returned chapters AND their sections together,
    # so the chapter node has no children of its own.
    ch12 = N("T_TIT24_CH12", "Chapter 12")
    nodes = [root] + link(title(), ch12, N("T_TIT24_CH12_S24-1201", "s"), N("T_TIT24_CH12_S24-1202", "s"))
    got = ids(municode.content_units(nodes))
    check("flattened: chapter is the unit once, never its sections", got == ["T_TIT24_CH12"])

    # Orphan: a section whose chapter never appeared in the tree at all.
    nodes = [root, title(), N("T_TIT24_CH13_S24-1301", "s", depth=2)]
    units = municode.content_units(nodes)
    check("orphan section: its chapter is synthesised from the id",
          ids(units) == ["T_TIT24_CH13"] and units[0].title == "T_TIT24_CH13")
    check("orphan section: the synthesised chapter is fetched by the section's real id",
          units[0].fetch_id == "T_TIT24_CH13_S24-1301")

    # A section id with an extra suffix, or nested under a section that is
    # itself listed: the invented parent id is not a node Municode knows
    # (Greeley's charter answered 404 to 25 of them). The nearest listed
    # chapter-like ancestor is the unit, once.
    ch16 = N("T_TIT24_CH16", "Chapter 16")
    s1 = N("T_TIT24_CH16_S24-1601", "s")
    nodes = [root] + link(title(), ch16, N("T_TIT24_CH16_S24-1601_A", "a"),
                          N("T_TIT24_CH16_S24-1601_B", "b"))
    check("suffixed section ids: the real chapter is the unit, no invented id",
          ids(municode.content_units(nodes)) == ["T_TIT24_CH16"])
    nodes = [root] + link(title(), ch16, s1, N("T_TIT24_CH16_S24-1601_A", "a"))
    check("section under a listed section: the chapter is the unit, the section is not",
          ids(municode.content_units(nodes)) == ["T_TIT24_CH16"])

    # A chapter with no sections yet is still fetched; the product root never is.
    ch14 = N("T_TIT24_CH14", "Chapter 14 (reserved)")
    nodes = [root] + link(title(), ch14)
    check("empty chapter fetched, root not", ids(municode.content_units(nodes)) == ["T_TIT24_CH14"])

    # A section listed straight under a TITLE belongs to its chapter by id;
    # the title must not be fetched as if it were a chapter.
    nodes = [root] + link(title(), N("T_TIT24_CH15", "Chapter 15"), N("T_TIT24_CH15_S24-1501", "s"))
    check("section under a title: chapter is the unit, title is not",
          ids(municode.content_units(nodes)) == ["T_TIT24_CH15"])

    print("\n" + ("units are chapters, never sections" if not failed else f"{failed} check(s) failed"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
