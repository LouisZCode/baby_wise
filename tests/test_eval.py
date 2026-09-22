from __future__ import annotations

from bby_wise.eval.records import evaluate, verdict
from bby_wise.ingest.load import upsert_chunk

from test_ingest import fresh_db


def seed(s, url, text, **kw):
    args = dict(source="biog", title="T", lang="de", topics=["schlaf"])
    args.update(kw)
    return upsert_chunk(s, url=url, text=text, **args)


def test_eval_pass_on_clean_corpus():
    s = fresh_db()
    seed(s, "https://x.de/a", "Babys schlafen in den ersten Wochen sehr viel. " * 4,
         title="Wie viel schlafen Babys?")
    seed(s, "https://x.de/b", "Von einer Schlafstörung spricht man bei häufigen Problemen. " * 4,
         title="Was ist eine Schlafstörung?")
    report = evaluate(s, ["https://x.de/a", "https://x.de/b"])
    assert verdict(report) == (True, [])
    s.close()


def test_eval_catches_empty_leftovers_untagged_and_missing():
    s = fresh_db()
    seed(s, "https://x.de/a", "kurz")
    seed(s, "https://x.de/b", "Dazu wird um Ihre Einwilligung bei Matomo gebeten. " * 4)
    seed(s, "https://x.de/c", "Babys schlafen in den ersten Wochen sehr viel. " * 4,
         topics=[])
    report = evaluate(s, ["https://x.de/a", "https://x.de/gone"])
    ok, problems = verdict(report)
    assert not ok
    assert report["live_empty"] == ["https://x.de/a"]
    assert report["consent_leftovers"] == ["https://x.de/b"]
    assert report["untagged"] == ["https://x.de/c"]
    assert report["missing_urls"] == ["https://x.de/gone"]
    s.close()


def test_eval_catches_boilerplate_leftovers():
    s = fresh_db()
    seed(s, "https://x.de/a", "Wie viel schlafen Babys?\nHäufige Fragen\n" + "Babys schlafen viel. " * 6,
         title="Wie viel schlafen Babys?")
    report = evaluate(s)
    ok, _ = verdict(report)
    assert not ok
    assert report["boilerplate_leftovers"] == ["https://x.de/a"]
    s.close()


def test_eval_catches_dup_hash_and_title():
    s = fresh_db()
    seed(s, "https://x.de/a", "Gleicher Text hier und dort immer wieder. " * 4,
         title="Gleiche Frage?")
    seed(s, "https://x.de/b", "Gleicher Text hier und dort immer wieder. " * 4,
         title="Gleiche Frage!")
    report = evaluate(s)
    assert len(report["dup_hash"]) == 1
    assert len(report["dup_title"]) == 1
    s.close()
