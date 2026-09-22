"""Topic inference: keyword map over URL slug + title, human sidecar wins.

The sidecar (topic_overrides.json, {url: [topics]}) is the human-curated
layer: exact URL matches there override the keyword guess.
"""

from __future__ import annotations

import json
from pathlib import Path

_OVERRIDES_PATH = Path(__file__).with_name("topic_overrides.json")

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "schlaf": ("schlaf", "schläf", "schlaef", "einschlaf", "durchschlaf",
               "bett", "wiege", "aufwach", "müde", "muede", "schnarch"),
    "ernaehrung": (
        "ernaehr", "beikost", "still", "muttermilch", "brei", "milch",
        "essen", "trinken", "weaning", "fläschchen", "flaeschchen",
        "hunger", "besteck", "süß", "suess", "süss", "frühstück",
        "fruehstueck",
    ),
    "haut": ("haut", "neurodermitis", "ekzem", "ausschlag", "pickel",
             "sonne", "sonnenbrand"),
    "impfen": ("impf",),
    "krankheit": (
        "fieber", "husten", "schnupfen", "infekt", "krank", "durchfall",
        "erbrechen", "mittelohr", "pseudokrupp", "windpocken", "masern",
        "antibiotika", "schmerz", "laus", "läuse", "laeuse", "wurm",
        "würm", "wuerm", "erkält", "erkaelt", "grippe", "blase",
        "hausmittel", "haustier",
    ),
    "entwicklung": (
        "entwicklung", "motorik", "sprechen", "laufen", "krabbeln",
        "wachstum", "gewicht", "zähne", "zaehne", "sehen", "hören",
        "hoeren", "langeweile", "beschaeftig", "bastel", "spielzeug",
        "spiel",
    ),
    "sicherheit": (
        "sicherheit", "unfall", "notfall", "giftnotruf", "autositz",
        "kinderwagen", "sturz", "vergiftung", "verbrennung", "trampolin",
        "spielplatz", "fahrrad", "schwimm", "garten", "insekten",
        "zecke", "schüttel", "schuettel", "wippe", "laufstall",
        "lauflern", "kindstod", "monitor", "couch", "sofa",
    ),
    "gefuehle": (
        "trotz", "weinen", "wein", "schreien", "schrei", "angst", "ängst",
        "aengst", "bindung", "eifersucht", "wut", "trauer", "fremdel",
        "quengel", "aggress",
    ),
    "betreuung": ("kita", "tagesmutter", "betreuung", "elternzeit",
                  "eingewöhnung", "eingewoehnung"),
    "hygiene": ("wickel", "windel", "hygiene", "baden", "zähneputzen",
                "zaehneputzen", "pflege", "fluor"),
    "sauberkeit": ("einnäss", "einnaess", "bettnäss", "bettnæss", "näss",
                   "naess", "töpfchen", "toepfchen", "sauber"),
    "medien": ("bildschirm", "smartphone", "medien", "kopfhörer",
               "kopfhoerer", "smart speaker", "fernseh", "tablet",
               "computer", "kino", "babyfon", "strahlung", "musik"),
    "vorsorge": ("u-untersuchung", "u untersuchung", "vorsorge",
                 "gelbes heft", "gelbe heft", "kinderarzt", "früherkennung",
                 "frueherkennung", "vitamin"),
}


def _overrides() -> dict[str, list[str]]:
    try:
        return json.loads(_OVERRIDES_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def infer_topics(url: str, title: str | None) -> list[str]:
    """Return sorted topic tags for a page. Sidecar exact-match wins."""
    hit = _overrides().get(url)
    if hit is not None:
        return sorted(hit)
    hay = f"{url} {title or ''}".lower()
    return sorted(t for t, kws in TOPIC_KEYWORDS.items() if any(k in hay for k in kws))
