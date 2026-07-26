/**
 * Map RDF class URIs to an entity "kind" — a short display label plus a colour
 * key used for node headers and type badges. The kind keys line up with the
 * --kind-* CSS variables in index.css.
 *
 * Classification is by the class's local name (last URI segment), so it works
 * regardless of namespace. The first type that maps to a known kind wins; an
 * unrecognised set falls back to the first type's local name and the default
 * colour.
 */
import { localName } from './prefixes.js'

const KIND_BY_LOCAL = {
  MusicEntity: 'work',
  F1_Work: 'work',
  F2_Expression: 'expression',
  F3_Manifestation: 'manifestation',
  Source: 'source',
  F5_Item: 'source',
  Person: 'person',
  Role: 'role',
  AgentRole: 'agentrole',
  Place: 'place',
  Organization: 'org',
  F31_Performance: 'performance',
  E89_Propositional_Object: 'subject',
  LinguisticSystem: 'language',
  DigitalDocument: 'file',
}

const LABEL_BY_KIND = {
  work: 'Musical Work',
  expression: 'Expression',
  manifestation: 'Manifestation',
  source: 'Source',
  person: 'Person',
  role: 'Role',
  agentrole: 'Agent Role',
  place: 'Place',
  org: 'Organization',
  performance: 'Performance',
  subject: 'Subject',
  language: 'Language',
  file: 'Digital Copy',
}

/**
 * Resolve a list of full class URIs to `{ kind, label }`.
 *
 * @param {string[]} types - Full RDF class URIs.
 * @returns {{kind: string, label: string}}
 */
export function entityKind(types = []) {
  for (const t of types) {
    const kind = KIND_BY_LOCAL[localName(t)]
    if (kind) return { kind, label: LABEL_BY_KIND[kind] }
  }
  if (types.length > 0) return { kind: 'default', label: localName(types[0]) }
  return { kind: 'default', label: 'Entity' }
}

/** CSS colour for a kind (used inline for node header / badge backgrounds). */
export function kindColor(kind) {
  return `var(--kind-${kind || 'default'})`
}

// Friendlier verbs for the relation predicates the graph traverses; anything
// not listed falls back to the predicate's local name.
const PRED_LABEL = {
  R7_exemplifies: 'exemplifies',
  R4_embodies: 'embodies',
  P148i_is_component_of: 'component of',
  hasAgentRole: 'has agent role',
  hasAgent: 'agent',
  hasRole: 'role',
  P129_is_about: 'about',
  P16_used_specific_object: 'used object',
  P19_was_intended_use_of: 'intended for',
  P51_has_former_or_current_owner: 'owner',
  language: 'language',
  hasPlace: 'place',
}

/** Short, human label for a relation predicate URI. */
export function predicateLabel(uri) {
  const ln = localName(uri)
  return PRED_LABEL[ln] || ln
}
