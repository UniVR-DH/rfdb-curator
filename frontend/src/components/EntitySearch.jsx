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
 *   - Each option renders two lines: primary label above, compact IRI below
 *     (smaller, dimmed) to help distinguish identically-named entities.
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
          formatOptionLabel={(option) => (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span>{option.label}</span>
              <span style={{ opacity: 0.65, fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                {option.compactUri}
              </span>
            </div>
          )}
          styles={selectStyles}
          cacheOptions
        />
      )}
    />
  )
}

const selectStyles = {
  control: (base, state) => ({
    ...base,
    backgroundColor: 'rgba(0,0,0,0.35)',
    borderColor: state.isFocused ? 'var(--color-focus)' : 'rgba(255,255,255,0.14)',
    boxShadow: state.isFocused ? '0 0 0 3px var(--color-focus-glow)' : 'none',
    borderRadius: 'var(--radius-input)',
    minHeight: '38px',
    '&:hover': { borderColor: 'rgba(255,255,255,0.2)' },
  }),
  menu: (base) => ({
    ...base,
    backgroundColor: '#1e1e22',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 'var(--radius-panel)',
  }),
  option: (base, state) => ({
    ...base,
    backgroundColor: state.isFocused ? 'rgba(139,30,45,0.35)' : 'transparent',
    color: '#e8e1d6',
    cursor: 'pointer',
  }),
  multiValue: (base) => ({
    ...base,
    backgroundColor: 'rgba(198,161,91,0.15)',
    borderRadius: '4px',
  }),
  multiValueLabel: (base) => ({ ...base, color: '#c6a15b', fontSize: '12px' }),
  multiValueRemove: (base) => ({
    ...base,
    color: '#c6a15b',
    ':hover': { backgroundColor: 'rgba(139,30,45,0.4)', color: '#e8e1d6' },
  }),
  singleValue: (base) => ({ ...base, color: '#e8e1d6' }),
  input: (base) => ({ ...base, color: '#e8e1d6' }),
  placeholder: (base) => ({ ...base, color: 'rgba(201,210,216,0.5)' }),
  clearIndicator: (base) => ({ ...base, color: 'rgba(201,210,216,0.5)', cursor: 'pointer' }),
  dropdownIndicator: (base) => ({ ...base, color: 'rgba(201,210,216,0.5)' }),
}
