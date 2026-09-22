"""JEV intent router: classify the question before retrieval.

One call to OpenRouter's Decisions API (`typesafe/jev-1.13`, same key as
the composer) asks three questions in parallel:
- topic: Choice over our 12 corpus topics (+ other) → retrieval filter.
- urgent: Noul — potentially urgent baby-health situation? (soft flag,
  unblocks the parked triage idea without routing on it).
- answerable: Noul — answerable from parenting guidelines at all?

Any failure → None; callers fall back to today's unfiltered behavior.
Low topic confidence (< TOPIC_MIN_CONF) → topic ignored, flags kept.
Pennies per thousand questions; ~300ms.
"""

from __future__ import annotations

import httpx

from .settings import settings

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
JEV_MODEL = "typesafe/jev-1.13"
TOPIC_MIN_CONF = 0.5

TOPIC_CRITERIA = {
    "schlaf": "baby sleep, falling asleep, sleep disorders, naps",
    "ernaehrung": "feeding, nursing, breast milk, formula, solids, nutrition",
    "haut": "skin, eczema, rash, sun",
    "impfen": "vaccinations",
    "krankheit": "illness, fever, cough, symptoms, infections, pain",
    "entwicklung": "growth, milestones, motor skills, teeth, weight",
    "sicherheit": "safety, accidents, emergencies, poison, car seats",
    "gefuehle": "crying, tantrums, fear, bonding, emotions",
    "betreuung": "daycare, childminders, parental leave",
    "hygiene": "diapers, bathing, dental care, hygiene",
    "sauberkeit": "bedwetting, potty training, toilet",
    "medien": "screens, smartphones, headphones, media use",
    "vorsorge": "check-ups, U-examinations, pediatrician, prevention",
    "other": "none of the above",
}


def route_question(question: str) -> dict | None:
    """Return {topic, topic_confidence, urgent, answerable} or None."""
    try:
        r = httpx.post(
            DECISIONS_URL,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": JEV_MODEL,
                "state": question,
                "questions": {
                    "topic": {
                        "type": "choice",
                        "instructions": "Which parenting topic is this question about?",
                        "criteria": TOPIC_CRITERIA,
                    },
                    "urgent": {
                        "type": "noul",
                        "instructions": "Does this describe a potentially urgent baby-health situation (e.g. high fever in a young infant, breathing difficulty, dehydration, lethargy)?",
                    },
                    "answerable": {
                        "type": "noul",
                        "instructions": "Is this question answerable from parenting health guidelines (as opposed to chat, opinion, or unrelated topics)?",
                    },
                },
            },
            timeout=30.0,
        )
        r.raise_for_status()
        a = r.json()["answers"]
        return {
            "topic": a["topic"]["choice"],
            "topic_confidence": a["topic"]["confidence"],
            "urgent": a["urgent"]["noul"],
            "answerable": a["answerable"]["noul"],
        }
    except Exception:
        return None
