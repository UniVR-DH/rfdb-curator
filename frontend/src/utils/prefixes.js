/**
 * Prefix compaction utility for display purposes.
 *
 * The backend returns raw full IRIs everywhere.  This module maps them to
 * their compact CURIE form (e.g. `https://rfdb.it/data/Place_1` -> `rfdb:Place_1`)
 * for every place in the UI where a human-readable identifier is shown.
 *
 * SCHEMA RESILIENCE NOTE:
 *   This map must be updated manually whenever a new @prefix is added to
 *   schema/schema.ttl that is not already listed below.  Without an entry here:
 *     - Raw full IRIs will be shown in the record list, inspector, and triples panel
 *       instead of compact CURIEs.
 *   Also update JSONLD_CONTEXT in utils/jsonld.js (same set of prefixes).
 *   The backend equivalent is schema_extractor.py's _curie() helper which reads
 *   prefixes directly from the parsed rdflib graph at startup.
 */

/** @type {Record<string, string>} Maps CURIE prefix to full namespace URI */
const PREFIX_MAP = {
  cidoc: 'http://www.cidoc-crm.org/cidoc-crm/',
  core: 'https://w3id.org/polifonia/ontology/core/',
  dcterms: 'http://purl.org/dc/terms/',
  fabio: 'http://purl.org/spar/fabio/',
  frbr: 'http://purl.org/vocab/frbr/core#',
  lrmoo: 'http://iflastandards.info/ns/lrm/lrmoo/',
  mm: 'https://w3id.org/polifonia/ontology/music-meta/',
  owl: 'http://www.w3.org/2002/07/owl#',
  prism: 'http://prismstandard.org/namespaces/basic/2.0/',
  rdf: 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
  rdfs: 'http://www.w3.org/2000/01/rdf-schema#',
  rfdb: 'https://rfdb.it/data/',
  sh: 'http://www.w3.org/ns/shacl#',
  skos: 'http://www.w3.org/2004/02/skos/core#',
  source: 'https://w3id.org/polifonia/ontology/source/',
  wd: 'http://www.wikidata.org/entity/',
  xsd: 'http://www.w3.org/2001/XMLSchema#',
}

/**
 * Compact a full IRI to its CURIE prefix form.
 *
 * Returns the value unchanged when:
 *   - `value` is falsy or not a string
 *   - the value already looks like a CURIE (contains `:` but no `http` scheme)
 *   - no prefix in PREFIX_MAP matches
 *
 * Literal strings (e.g. `"Libretto (1736)"@en`) are safe to pass through;
 * they will not match any namespace and are returned as-is.
 *
 * @param {string} value - A full IRI or any other string.
 * @returns {string} Compact CURIE (e.g. "rfdb:Place_abc") or the original value.
 */
export function compactIri(value) {
  if (!value || typeof value !== 'string') return value
  if (value.includes(':') && !value.startsWith('http://') && !value.startsWith('https://')) {
    return value
  }

  for (const [prefix, ns] of Object.entries(PREFIX_MAP)) {
    if (value.startsWith(ns)) {
      return `${prefix}:${value.slice(ns.length)}`
    }
  }

  return value
}
