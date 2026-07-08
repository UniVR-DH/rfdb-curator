/** SHACL-driven form: loads schema metadata, maps records to form state, and submits JSON-LD. */
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { apiClient } from '../api/client.js'
import { buildJsonLdEntity } from '../utils/jsonld.js'
import { compactIri } from '../utils/prefixes.js'
 
import FormField from './FormField.jsx'
import './ShapeForm.css'

/**
 * Convert backend triples for one predicate into the value shape expected by a field widget.
 */
function tripleToFieldValue(val, fieldType, languageTagPolicy, maxCount = 1) {
  const triple = Array.isArray(val) ? val[0] : val

  if (fieldType === 'lang-string-list') {
    const values = Array.isArray(val) ? val : val ? [val] : []
    const mapped = values.map((t) => ({
      __value: t.object ?? '',
      __lang: t.language ?? 'en',
    }))
    // Never show a fully blank list widget on edit.
    return mapped.length > 0 ? mapped : [{ __value: '', __lang: 'en' }]
  }

  if (fieldType === 'lang-string') {
    // react-hook-form controllers for lang strings bind to path.__value and path.__lang.
    // The form state must therefore store a nested object at formData[path].
    const defaultLang = languageTagPolicy === 'required' ? 'en' : ''
    if (
      triple &&
      typeof triple === 'object' &&
      'objectType' in triple &&
      triple.objectType === 'literal'
    ) {
      return { __value: triple.object, __lang: triple.language ?? defaultLang }
    }
    return { __value: triple ? triple.object || String(triple) : '', __lang: defaultLang }
  }

  if (fieldType === 'uri') {
    const isMulti = maxCount !== 1
    const values = Array.isArray(val) ? val : val ? [val] : []
    const mapped = values
      .map((entry) => {
        if (entry && typeof entry === 'object') {
          if (entry.objectType === 'iri') return entry.object
          if (entry['@id']) return entry['@id']
          if (typeof entry.object === 'string') return entry.object
          return ''
        }
        return typeof entry === 'string' ? entry : ''
      })
      .filter((entry) => entry && String(entry).trim() !== '')
    return isMulti ? mapped : (mapped[0] ?? '')
  }

  if (fieldType === 'temporal' || fieldType === 'year' || fieldType === 'number') {
    if (triple && typeof triple === 'object' && triple['@value']) return triple['@value']
    if (triple && typeof triple === 'object' && triple.object) return triple.object
    if (typeof triple === 'string') return triple
    return ''
  }

  // Generic fallback for plain text-like scalar fields. Backend triples
  // commonly arrive as objects with `.object` for literal values; map those
  // to scalar strings so inputs never render "[object Object]".
  if (triple && typeof triple === 'object') {
    if (triple['@value']) return triple['@value']
    if (typeof triple.object === 'string') return triple.object
    if (typeof triple['@id'] === 'string') return triple['@id']
    return ''
  }
  return triple ?? ''
}

function tripleToFieldScalarValue(val, fieldType, languageTagPolicy) {
  return tripleToFieldValue(val, fieldType, languageTagPolicy, 1)
}

export default function ShapeForm({ shape, allShapes, record, onValidation, onSaved, onReset }) {
  const [formSchema, setFormSchema] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const { register, handleSubmit, reset, control, formState } = useForm()

  function formatApiError(err) {
    const detail = err?.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    if (Array.isArray(detail)) {
      const parts = detail
        .map((item) => {
          if (typeof item === 'string') return item
          if (item?.msg) return item.msg
          return null
        })
        .filter(Boolean)
      if (parts.length > 0) return parts.join('; ')
    }
    if (detail && typeof detail === 'object') {
      try {
        return JSON.stringify(detail)
      } catch {
        // fallback handled below
      }
    }
    return err?.message || 'Save failed'
  }

  function collectErrorPaths(node, prefix = '') {
    if (!node || typeof node !== 'object') return []
    if (node.type) return [prefix]

    const paths = []
    for (const [key, value] of Object.entries(node)) {
      const nextPrefix = prefix ? `${prefix}.${key}` : key
      paths.push(...collectErrorPaths(value, nextPrefix))
    }
    return paths
  }

  useEffect(() => {
    if (!shape) return
    setFormSchema(null)

    // Ignore stale in-flight responses when the selected shape changes quickly.
    let ignore = false

    apiClient
      .getFormSchema(shape.id)
      .then((res) => {
        if (ignore) return
        setFormSchema(res)
      })
      .catch((err) => {
        if (ignore) return
        console.error(err)
      })

    return () => {
      ignore = true
    }
  }, [shape])

  // Flatten triples into a predicate-keyed map while preserving full triple metadata.
  function triplesToFlatObject(triples) {
    if (!Array.isArray(triples)) return {}
    const out = {}
    for (const triple of triples) {
      const key = compactIri(triple.predicate)
      if (out[key]) {
        if (Array.isArray(out[key])) {
          out[key].push(triple)
        } else {
          out[key] = [out[key], triple]
        }
      } else {
        out[key] = triple
      }
    }
    return out
  }

  /**
   * Resolve a human-readable label for an entity IRI by querying the search API.
   * Falls back to the IRI itself if no label is found or the request fails.
   * Used to populate entity-search fields with proper labels on form load.
   */
  async function resolveEntityLabel(iri, field) {
    try {
      // Prefer nestedShape (shape ID like "PlaceShape") over nodeClass (class IRI).
      // This matches the same priority used by EntitySearch.jsx loadOptions.
      const targetShape = field?.nestedShape ?? field?.nodeClass ?? ''
      const results = await apiClient.searchEntities(targetShape, iri, 5)
      // Backend returns {uri, label} — match against r.uri only.
      const match = results?.find((r) => r.uri === iri)
      if (match) {
        return { value: match.uri, label: match.label || iri }
      }
    } catch {
      // fall through to IRI fallback
    }
    return { value: iri, label: iri }
  }

  /** Map a loaded record into react-hook-form state for the active schema fields. */
  function mapRecordToFormData(record, fields) {
    if (!record || !fields) return {}
    const flat = record.triples ? triplesToFlatObject(record.triples) : record
    const formData = {}

    // Always carry @id forward so the backend knows this is an update
    if (record && record.id) {
      formData['@id'] = record.id
    }

    for (const field of fields) {
      const val = flat[field.path]

      // --- Multi-value language-tagged list (e.g. skos:altLabel) ---
      if (field.type === 'lang-string-list') {
        formData[field.path] = tripleToFieldScalarValue(val, field.type, field.languageTagPolicy)
        continue
      }

      // --- Single language-tagged string (e.g. rdfs:label) ---
      if (field.type === 'lang-string') {
        formData[field.path] = tripleToFieldScalarValue(val, field.type, field.languageTagPolicy)
        continue
      }

      // --- Language field (dcterms:language) ---
      // Stores the literal string value of the language code triple.
      // Falls back to empty string so the input is never left as undefined.
      // (Path-based special case, not type-based — left as-is.)
      else if (field.path === 'dcterms:language') {
        const triple = Array.isArray(val) ? val[0] : val
        if (triple && typeof triple === 'object' && triple['@value']) {
          formData[field.path] = triple['@value']
        } else if (triple && typeof triple === 'object' && triple.object) {
          formData[field.path] = triple.object
        } else if (typeof triple === 'string') {
          formData[field.path] = triple
        } else {
          formData[field.path] = ''
        }
      }

      // --- Entity search ---
      // Initialised to null here; resolved asynchronously in useEffect
      // to obtain a proper {value, label} object the async-select can display.
      else if (field.type === 'entity-search') {
        formData[field.path] = null
      }

      // --- URI input ---
      else if (field.type === 'uri') {
        formData[field.path] = tripleToFieldValue(
          val,
          field.type,
          field.languageTagPolicy,
          field.maxCount
        )
      }

      // --- Nested bridge entity ---
      // Not populated here — handled asynchronously in the useEffect below
      // by fetching each bridge node's own triples from the backend.
      // Initialised to empty array so useFieldArray starts in a clean state
      // while the async fetch is in flight.
      else if (field.type === 'nested') {
        formData[field.path] = []
      }

      // --- Temporal (xsd:date / xsd:gYear / xsd:gYearMonth) ---
      else if (field.type === 'temporal') {
        formData[field.path] = tripleToFieldScalarValue(val, field.type, field.languageTagPolicy)
      }

      // --- Year and Number ---
      else if (field.type === 'year' || field.type === 'number') {
        formData[field.path] = tripleToFieldScalarValue(val, field.type, field.languageTagPolicy)
      }

      // --- Generic fallback for text-like fields ---
      else {
        formData[field.path] = tripleToFieldScalarValue(val, field.type, field.languageTagPolicy)
      }
    }

    return formData
  }

  useEffect(() => {
    if (!formSchema) return

    setSubmitError(null)

    // Ignore stale async mapping results if record/shape changes mid-flight.
    let ignore = false

    if (!record || !record.id) {
      // New record: seed lang-string-list fields with one empty row so the
      // list widget is never blank on a fresh form.
      const defaults = {}
      for (const field of formSchema.fields) {
        if (field.type === 'lang-string-list') {
          defaults[field.path] = [{ __value: '', __lang: 'en' }]
        } else if (field.type === 'lang-string') {
          defaults[field.path] = {
            __value: '',
            __lang: field.languageTagPolicy === 'required' ? 'en' : '',
          }
        } else if (field.type === 'uri' && field.maxCount !== 1) {
          defaults[field.path] = ['']
        }
      }
      if (!ignore) reset(defaults)
      return () => {
        ignore = true
      }
    }

    // Editing existing record:
    // Step 1 — map all scalar fields synchronously so the form is not blank
    //           while async fetches are in flight.
    const mapped = mapRecordToFormData(record, formSchema.fields)
    const flat = triplesToFlatObject(record.triples)

    const nestedFields = formSchema.fields.filter((f) => f.type === 'nested')
    const entitySearchFields = formSchema.fields.filter((f) => f.type === 'entity-search')

    if (nestedFields.length === 0 && entitySearchFields.length === 0) {
      // Nothing async needed — reset straight away
      if (!ignore) reset(mapped)
      return () => {
        ignore = true
      }
    }

    // Step 2 — resolve nested bridge entities and entity-search labels in parallel.
    const nestedPromises = nestedFields.map(async (field) => {
      const val = flat[field.path]

      // Collect all bridge IRIs linked via this predicate (may be multiple)
      const rawVals = Array.isArray(val) ? val : val ? [val] : []
      const iris = rawVals.map((t) => (t?.objectType === 'iri' ? t.object : null)).filter(Boolean)

      if (iris.length === 0) {
        mapped[field.path] = []
        return
      }

      // Resolve the nested shape descriptor so we know which properties to map
      const resolvedShape = allShapes?.find((s) => s.id === field.nestedShape)

      const entries = await Promise.all(
        iris.map(async (iri) => {
          try {
            const entity = await apiClient.getEntity(iri)
            const bridgeFlat = triplesToFlatObject(entity.triples)

            // Start with the IRI so AnonymousEntityEditor can identify the node
            const entry = {
              '@id': iri,
              // Keep rdf:type in form state so nested nodes satisfy sh:hasValue rdf:type constraints.
              '@type': resolvedShape?.targetClass ?? '',
            }

            if (resolvedShape) {
              for (const prop of resolvedShape.properties) {
                if (prop.path === 'rdf:type') continue

                const propVal = bridgeFlat[prop.path]
                if (!propVal) continue

                if (prop.type === 'entity-search') {
                  // Resolve label for entity-search props inside bridge entities too
                  const t = Array.isArray(propVal) ? propVal[0] : propVal
                  const iriVal = t?.objectType === 'iri' ? t.object : String(t)
                  entry[prop.path] = await resolveEntityLabel(iriVal, prop)
                } else {
                  // Reuse the same triple-to-widget mapping as top-level fields.
                  entry[prop.path] = tripleToFieldValue(propVal, prop.type, prop.languageTagPolicy)
                }
              }
            }

            return entry
          } catch {
            // If a single bridge entity fetch fails, skip it rather than
            // breaking the whole form load
            return null
          }
        })
      )

      mapped[field.path] = entries.filter(Boolean)
    })

    // Step 3 — resolve labels for top-level entity-search fields
    const entitySearchPromises = entitySearchFields.map(async (field) => {
      const val = flat[field.path]
      const triple = Array.isArray(val) ? val[0] : val
      if (!triple) {
        mapped[field.path] = null
        return
      }

      // Extract the raw IRI from the triple
      let iri = null
      if (triple?.objectType === 'iri') {
        iri = triple.object
      } else if (triple?.['@id']) {
        iri = triple['@id']
      } else if (typeof triple?.object === 'string') {
        iri = triple.object
      } else if (typeof triple === 'string') {
        iri = triple
      }

      if (!iri) {
        mapped[field.path] = null
        return
      }

      // Resolve to {value, label} using the search API
      mapped[field.path] = await resolveEntityLabel(iri, field)
    })

    Promise.all([...nestedPromises, ...entitySearchPromises]).then(() => {
      if (ignore) return
      reset(mapped)
    })

    // Mark this run as stale when a newer run starts or component unmounts.
    return () => {
      ignore = true
    }
    // NOTE: `allShapes` and `resolveEntityLabel` are intentionally omitted from the
    // dependency array. `allShapes` rarely changes after initial load and re-running
    // the effect when it does would reset unsaved form edits. `resolveEntityLabel` is
    // a stable function in practice (defined once per render, not memoized). If
    // either causes stale-closure bugs in a future refactor, add them here.
  }, [record, shape, reset, formSchema])

  // Track dirty predicates to build a minimal originalTriples delete set on update.
  const { dirtyFields } = formState

  function isFieldDirty(field) {
    // Nested/bridge fields are managed by AnonymousEntityEditor and must never
    // be included in originalTriples — exclude them unconditionally.
    if (field.type === 'nested') return false

    if (field.type === 'lang-string-list') {
      const df = dirtyFields[field.path]
      if (!df) return false
      // react-hook-form sets df to `true` when the array length changed (item added/removed)
      if (df === true) return true
      // When items were edited in place, df is an array of per-item dirty state objects
      if (Array.isArray(df)) return df.some((item) => item?.__value || item?.__lang)
      return false
    }

    if (field.type === 'lang-string') {
      // react-hook-form stores nested dirty state as an object on dirtyFields[field.path],
      // NOT as flat dot-notation keys. Access .__value and .__lang as object properties.
      return !!(dirtyFields[field.path]?.__value || dirtyFields[field.path]?.__lang)
    }

    return !!dirtyFields[field.path]
  }

  async function onSubmit(formData) {
    setSubmitting(true)
    setSubmitError(null)
    try {
      const formDataWithId = { ...formData }
      if (record && record.id) {
        if (!formDataWithId['@id']) formDataWithId['@id'] = record.id
      }

      const newData = buildJsonLdEntity(formSchema.shape, formSchema.fields, formDataWithId)

      // Build originalTriples: only for predicates the user actually changed.
      // Nested/bridge fields are excluded via isFieldDirty returning false for type === 'nested'.
      // On create, record is null so changedOriginalTriples stays null and no delete runs.
      let changedOriginalTriples = null
      if (record && record.triples && Object.keys(dirtyFields).length > 0) {
        const dirtyPathUris = new Set(
          formSchema.fields.filter((f) => isFieldDirty(f)).map((f) => f.pathUri)
        )
        changedOriginalTriples = record.triples.filter((t) => dirtyPathUris.has(t.predicate))
      }

      const payload = {
        shapeId: shape.id,
        data: newData,
        originalTriples: changedOriginalTriples,
      }

      const result = await apiClient.createEntity(payload)
      onValidation?.(result.validationReport)
      if (result.success) onSaved?.()
    } catch (err) {
      setSubmitError(formatApiError(err))
    } finally {
      setSubmitting(false)
    }
  }

  function onInvalidSubmit(errors) {
    const rawPaths = collectErrorPaths(errors)
    const normalizedPaths = Array.from(
      new Set(rawPaths.map((p) => p.replace(/\.\d+\./g, '.').replace(/\.(__value|__lang)$/, '')))
    )

    const labelByPath = new Map((formSchema?.fields ?? []).map((f) => [f.path, f.name]))
    const labels = normalizedPaths.map((p) => labelByPath.get(p) ?? p)

    const message =
      labels.length > 0
        ? `Please fill required fields: ${labels.join(', ')}`
        : 'Form is invalid. Please check required fields.'

    setSubmitError(message)
  }

  if (!formSchema) {
    return <div className="form-loading">Loading form schema…</div>
  }

  // Block direct editing of helper-bridge shapes — they are only editable
  // inline via their parent entity form (AnonymousEntityEditor).
  if (shape.shapeRole === 'helper-bridge') {
    return (
      <div className="shape-form shape-form-blocked">
        <header className="form-header">
          <h2 className="form-title">{shape.label}</h2>
          {shape.description && <p className="form-description">{shape.description}</p>}
        </header>
        <div className="form-blocked-message">
          <p>
            This entity type is only editable as a connection from its parent entity. Please use the
            parent form to add or edit connections.
          </p>
        </div>
      </div>
    )
  }

  // Block editing of read-only shapes (reference vocabulary managed externally).
  if (shape.readOnly) {
    return (
      <div className="shape-form shape-form-blocked">
        <header className="form-header">
          <h2 className="form-title">{shape.label}</h2>
          {shape.description && <p className="form-description">{shape.description}</p>}
        </header>
        <div className="form-blocked-message">
          <p>
            This vocabulary is managed externally and cannot be edited here. Use the Records tab to
            browse available entries and select them from relation fields.
          </p>
        </div>
      </div>
    )
  }

  return (
    <form className="shape-form" onSubmit={handleSubmit(onSubmit, onInvalidSubmit)} noValidate>
      <header className="form-header">
        <h2 className="form-title">{shape.label}</h2>
        {shape.description && <p className="form-description">{shape.description}</p>}
        {record && record.id && (
          <span
            className="form-editing-label"
            style={{ display: 'block', fontSize: '0.9em', color: '#888', marginTop: '0.5em' }}
          >
            Editing <span style={{ fontFamily: 'monospace' }}>{record.id}</span>
          </span>
        )}
      </header>

      <div className="form-fields">
        {formSchema.fields.map((field) => (
          <FormField
            key={field.path}
            field={field}
            allShapes={allShapes}
            register={register}
            control={control}
          />
        ))}
      </div>

      {submitError && <p className="form-error">{submitError}</p>}

      <footer className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting
            ? record && record.id
              ? 'Updating…'
              : 'Inserting…'
            : record && record.id
              ? 'Update record'
              : 'Insert record'}
        </button>
        {/* Reset returns to a blank create form by clearing selected record in the parent. */}
        <button type="button" className="btn btn-ghost" onClick={() => onReset?.()}>
          Reset
        </button>
      </footer>
    </form>
  )
}