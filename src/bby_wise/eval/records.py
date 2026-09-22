"""Record-quality evaluation: invariants over stored chunks + coverage.

Pure `evaluate(db, expected_urls=None)` returns a report dict; runnable as
`python -m bby_wise.eval.records <sqlite-path>` for the human eyeball pass
before anything (retrieval, /ask) reads from the corpus.
"""

from __future__ import annotations

import re
import sys
from collections import Counter

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ..ingest.extract import _BOILERPLATE, _STRICT
from ..models import Base, GuidelineChunk

MIN_TEXT_LEN = 50


def _norm_title(title: str | None) -> str:
    t = (title or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", t)).strip()


def evaluate(
    db: Session,
    expected_urls: list[str] | None = None,
    known_empty: tuple[str, ...] = (),
) -> dict:
    rows = db.query(GuidelineChunk).all()
    live = [r for r in rows if r.status == "live"]
    report: dict = {"counts": Counter(r.status for r in rows), "n": len(rows)}

    report["live_empty"] = [
        r.source_url for r in live if len((r.text or "").strip()) < MIN_TEXT_LEN
    ]
    report["consent_leftovers"] = [
        r.source_url
        for r in live
        if any(m in (r.text or "").lower() for m in _STRICT)
    ]
    report["boilerplate_leftovers"] = [
        r.source_url
        for r in live
        if any(
            p.strip().lower() in _BOILERPLATE
            for p in (r.text or "").split("\n")
            if p.strip()
        )
    ]
    report["untagged"] = [r.source_url for r in live if not r.topics]
    report["quarantined"] = [r.source_url for r in rows if r.status == "quarantined"]

    by_hash: dict[str, list[str]] = {}
    for r in live:
        by_hash.setdefault(r.content_hash, []).append(r.source_url)
    report["dup_hash"] = {h: u for h, u in by_hash.items() if len(u) > 1}

    by_title: dict[str, list[str]] = {}
    for r in live:
        by_title.setdefault(_norm_title(r.title), []).append(r.source_url)
    report["dup_title"] = {t: u for t, u in by_title.items() if len(u) > 1}

    report["by_topic"] = Counter(t for r in live for t in (r.topics or []))
    lens = [len(r.text or "") for r in live]
    report["avg_len"] = sum(lens) // len(lens) if lens else 0
    report["min_len"] = min(lens) if lens else 0

    if expected_urls is not None:
        stored = {r.source_url for r in rows if r.status == "live"}
        report["missing_urls"] = [
            u for u in expected_urls if u not in stored and u not in known_empty
        ]
        report["extra_urls"] = sorted(stored - set(expected_urls))
        report["known_empty_stored"] = [u for u in known_empty if u in stored]
    return report


def verdict(report: dict) -> tuple[bool, list[str]]:
    problems = []
    for key in ("live_empty", "consent_leftovers", "boilerplate_leftovers",
                "untagged", "quarantined"):
        if report.get(key):
            problems.append(f"{key}: {len(report[key])}")
    if report.get("dup_hash"):
        problems.append(f"dup_hash: {len(report['dup_hash'])}")
    if report.get("dup_title"):
        problems.append(f"dup_title: {len(report['dup_title'])}")
    if report.get("missing_urls"):
        problems.append(f"missing_urls: {len(report['missing_urls'])}")
    if report.get("known_empty_stored"):
        problems.append(f"known_empty_stored: {len(report['known_empty_stored'])}")
    return (not problems, problems)


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "preview.db"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    db = Session(engine)
    expected = None
    known: tuple[str, ...] = ()
    if "--coverage" in sys.argv:
        from ..ingest import biog, fetch

        expected = biog.collect_faq_urls(fetch.PoliteFetcher())
        known = biog.KNOWN_EMPTY_FAQS
    report = evaluate(db, expected, known)
    ok, problems = verdict(report)
    print(f"rows={report['n']} counts={dict(report['counts'])}")
    print(f"avg_len={report['avg_len']} min_len={report['min_len']}")
    print(f"by_topic={dict(report['by_topic'])}")
    for key in ("live_empty", "consent_leftovers", "boilerplate_leftovers",
                "untagged", "quarantined", "missing_urls", "extra_urls"):
        vals = report.get(key) or []
        print(f"{key}: {len(vals)}")
        for v in vals[:15]:
            print(f"  - {v}")
    for key in ("dup_hash", "dup_title"):
        d = report.get(key) or {}
        print(f"{key}: {len(d)}")
        for k, v in list(d.items())[:10]:
            print(f"  - {str(k)[:40]}: {v}")
    print("VERDICT:", "PASS" if ok else f"FAIL ({'; '.join(problems)})")


if __name__ == "__main__":
    main()
