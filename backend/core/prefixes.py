"""Curated CURIE prefix → namespace map for the project.

This is the **authoritative, hand-maintained** prefix list served by
``GET /api/meta/prefixes`` (and hydrated by the frontend for IRI compaction and
the Data Context Panel). It is declared explicitly rather than read from the
rdflib schema graph on purpose:

  - a bare ``rdflib.Graph()`` pre-binds ~29 unrelated "well-known" vocabularies
    (``brick``, ``csvw``, ``dcat``, ``qb``, ``odrl``, …) that would otherwise leak
    into the map, and
  - the real prefixes are spread across *several* TTL sources (``schema.ttl``,
    ``data.ttl``, ``vocab.ttl``, ``glottolog_language.ttl``), not just the schema.

⚠️  MAINTENANCE: when you add a new ``@prefix`` to any project TTL file, add it
here too. Run the manual sanity check to catch drift (declared-but-missing):

    cd backend && uv run python scripts/check_prefixes.py

``scan_ttl_prefixes`` below powers that check; it is intentionally cheap (reads
only each file's leading directive block).
"""

import re
from collections.abc import Iterable

# Union of the @prefix declarations across schema/data/vocab/glottolog as of
# 2026-07-16. Keep sorted by prefix. See the maintenance note above.
PREFIXES: dict[str, str] = {
    "bibo": "http://purl.org/ontology/bibo/",
    "cidoc": "http://www.cidoc-crm.org/cidoc-crm/",
    "core": "https://w3id.org/polifonia/ontology/core/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "dctype": "http://purl.org/dc/dcmitype/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "frbr": "http://purl.org/vocab/frbr/core#",
    "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
    "glottolog": "http://glottolog.org/resource/languoid/id/",
    "gold": "http://purl.org/linguistics/gold/",
    "isbd": "http://iflastandards.info/ns/isbd/elements/",
    "lexvo": "http://lexvo.org/ontology#",
    "lrmoo": "http://iflastandards.info/ns/lrm/lrmoo/",
    "mm": "https://w3id.org/polifonia/ontology/music-meta/",
    "owl": "http://www.w3.org/2002/07/owl#",
    "prism": "http://prismstandard.org/namespaces/basic/2.0/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "rfdb": "https://rosfeatr.eu/rdf/data/",
    "rfdbs": "https://rosfeatr.eu/rdf/schema/",
    "sh": "http://www.w3.org/ns/shacl#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "source": "https://w3id.org/polifonia/ontology/source/",
    "vcard": "http://www.w3.org/2001/vcard-rdf/3.0#",
    "void": "http://rdfs.org/ns/void#",
    "wd": "http://www.wikidata.org/entity/",
    "wdt": "http://www.wikidata.org/prop/direct/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}

# Matches a Turtle ``@prefix name: <uri> .`` or SPARQL ``PREFIX name: <uri>`` line.
# The empty (base) prefix ``@prefix : <…>`` is intentionally NOT matched.
_PREFIX_RE = re.compile(
    r"^\s*(?:@prefix|PREFIX)\s+([A-Za-z][\w.\-]*):\s*<([^>]*)>\s*\.?\s*$",
    re.IGNORECASE,
)


def scan_ttl_prefixes(paths: Iterable[str]) -> dict[str, str]:
    """Collect ``@prefix``/``PREFIX`` declarations from the header of each TTL file.

    Reads only the leading directive block and stops at the first triple line, so
    it stays cheap even on very large files (e.g. the ~38 MB Glottolog dump). On a
    prefix conflict, later files win. Unreadable paths are skipped silently.

    Example:
        >>> scan_ttl_prefixes(["schema/schema.ttl"])["rfdb"]
        'https://rosfeatr.eu/rdf/data/'
    """
    found: dict[str, str] = {}
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    match = _PREFIX_RE.match(line)
                    if match:
                        found[match.group(1)] = match.group(2)
                        continue
                    # Ignore @base and any malformed directive; stop at the first
                    # line that is neither blank/comment nor a directive (a triple).
                    low = stripped.lower()
                    if not low.startswith(("@prefix", "prefix", "@base")):
                        break
        except OSError:
            continue
    return found
