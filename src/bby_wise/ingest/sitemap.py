"""Sitemap parsing (urlset + sitemapindex)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def sitemap_kind(xml_text: str) -> str:
    """'index' for a sitemapindex, else 'urlset'."""
    root = ET.fromstring(xml_text)
    return "index" if root.tag.endswith("sitemapindex") else "urlset"


def parse_sitemap_bytes(data: bytes) -> list[tuple[str, str | None]]:
    """Tolerant decode (BOM/UTF-16 servers exist) then parse."""
    for enc in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "latin-1"):
        try:
            return parse_sitemap(data.decode(enc))
        except (UnicodeDecodeError, ET.ParseError):
            continue
    raise ET.ParseError("could not decode sitemap as XML")


def parse_sitemap(xml_text: str) -> list[tuple[str, str | None]]:
    """Return [(loc, lastmod-or-None)] for a urlset or sitemapindex."""
    root = ET.fromstring(xml_text)
    items: list[tuple[str, str | None]] = []
    if root.tag.endswith("sitemapindex"):
        entries = root.findall("sm:sitemap", NS)
    else:
        entries = root.findall("sm:url", NS)
    for e in entries:
        loc = (e.findtext("sm:loc", default="", namespaces=NS) or "").strip()
        lastmod = e.findtext("sm:lastmod", default=None, namespaces=NS)
        lastmod = (lastmod or "").strip() or None
        if loc:
            items.append((loc, lastmod))
    return items


def is_sub_sitemap(loc: str) -> bool:
    return loc.lower().endswith(".xml")
