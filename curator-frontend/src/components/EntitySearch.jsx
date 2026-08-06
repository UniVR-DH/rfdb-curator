/**
 * Async autocomplete widget for entity-type relation fields (sh:class / sh:node).
 *
 * Wraps react-select AsyncSelect; options come from
 * GET /api/entities/search?shape=<targetShape>&query=<text>.
 *
 * Behaviour:
 *   - defaultOptions is set so the dropdown pre-populates on focus even before
 *     the user types (fires an empty-string search showing all available entities).
 *   - Multi-select is enabled when field.maxCount !== 1.
 *   - Each option renders up to three lines: primary label, compact IRI below
 *     (smaller, dimmed), and — in the open menu only — the entity's rdfs:comment
 *     (truncated) to help distinguish identically-named entities.
 *   - The stored form value is a react-select option {value, label};
 *     buildJsonLdEntity() in utils/jsonld.js reads option.value (the full IRI)
 *     and emits the correct {"@id": "..."} JSON-LD node.
 *
 * Props:
 *   field    {object}    - Property descriptor (nestedShape, nodeClass, minCount, maxCount)
 *   control  {object}    - react-hook-form control
 *   name     {string=}   - Override field path (required for nested/AnonymousEntityEditor usage)
 */
import { useCallback } from 'react'
 
import { Controller } from 'react-hook-form'
 
import AsyncSelect from 'react-select/async'
import { apiClient } from '../api/client.js'
import { compactIri } from '../utils/prefixes.js'
import { selectStyles } from './selectStyles.js'

/**
 * Normalise a react-hook-form field value for use with AsyncSelect.
 *
 * AsyncSelect requires `null` (not undefined or '') for a cleared single-select,
 * and an array (not null) for a cleared multi-select. This function enforces
 * those invariants so the select component never receives an invalid value.
 *
 * @param {*}       value   - Current value from react-hook-form (option object, array, or nullish).
 * @param {boolean} isMulti - Whether the field allows multiple selections.
 * @returns {object|null|Array} Normalised value safe to pass to AsyncSelect's `value` prop.
 */
function normalizeSelectValue(value, isMulti) {
  if (isMulti) {
    return Array.isArray(value) ? value : []
  }
  return value ?? null
}

/**
 * Truncate a string to `max` characters, appending an ellipsis when clipped.
 *
 * @param {string} text - The text to shorten.
 * @param {number} max  - Maximum character count before the ellipsis.
 * @returns {string} The original text, or its first `max` chars plus '…'.
 */
function truncate(text, max) {
  const s = String(text)
  return s.length > max ? `${s.slice(0, max)}…` : s
}

export default function EntitySearch({ field, control, name }) {
  const fieldName = name || field.path
  const loadOptions = useCallback(
    async (inputValue) => {
      try {
        const targetShape = field.nestedShape ?? field.nodeClass ?? ''
        const results = await apiClient.searchEntities(targetShape, inputValue)
        return results
          .map((r) => ({
            value: r.uri,
            label: r.label ?? compactIri(r.uri),
            compactUri: compactIri(r.uri),
            comment: r.comment ?? null,
          }))
          .sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: 'base' }))
      } catch {
        return []
      }
    },
    [field.nodeClass, field.nestedShape]
  )

  const isMulti = field.maxCount !== 1

  return (
    <Controller
      name={fieldName}
      control={control}
      rules={{ required: field.minCount > 0 }}
      render={({ field: ctrl }) => (
        <AsyncSelect
          isMulti={isMulti}
          loadOptions={loadOptions}
          defaultOptions
          value={normalizeSelectValue(ctrl.value, isMulti)}
          onChange={ctrl.onChange}
          onBlur={ctrl.onBlur}
          ref={ctrl.ref}
          placeholder={`Search ${field.name}…`}
          noOptionsMessage={() => 'No results'}
          formatOptionLabel={(option, meta) => (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span>{option.label}</span>
              <span style={{ opacity: 0.65, fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                {option.compactUri}
              </span>
              {option.comment && meta.context === 'menu' && (
                <span style={{ opacity: 0.75, fontSize: '11px' }}>
                  {truncate(option.comment, 100)}
                </span>
              )}
            </div>
          )}
          styles={selectStyles}
          menuPlacement="auto"
          menuPortalTarget={typeof document !== 'undefined' ? document.body : undefined}
          cacheOptions
        />
      )}
    />
  )
}
