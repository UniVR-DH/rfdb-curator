/**
 * SHACL-driven data entry form.
 *
 * On mount (or when `shape` changes) the component fetches the field schema
 * from GET /api/forms?shapeId=... and wires up a react-hook-form instance.
 * Each field is rendered by <FormField> which dispatches to the correct input
 * widget based on field.type (lang-string, entity-search, nested, etc.).
 *
 * On submit the form data is normalised into a JSON-LD object by
 * buildJsonLdEntity() and POSTed to POST /api/data. The SHACL report from
 * the response is forwarded to the parent via onValidation, and a successful
 * save triggers onSaved.
 *
 * --- IMPORTANT: CREATE vs UPDATE ---
 * - When creating a new record, the form is rendered with no record prop and no @id is present in the form state or payload.
 * - When editing, the form receives a record prop (with .id) and must ensure that @id is included in the form state and in the JSON-LD payload.
 * - If @id is missing from the payload, the backend will always create a new entity instead of updating.
 * - The mapping and submit logic must guarantee @id is preserved for updates.
 *
 * --- NESTED BRIDGE ENTITIES ---
 * - Bridge entities (e.g. AgentRole) are stored as separate RDF nodes linked from the parent.
 * - The parent's triples only contain the link IRI; the bridge's own property triples are stored separately.
 * - On edit, bridge entity IRIs are extracted from the parent's triples, then each bridge node is
 *   fetched individually via GET /api/data/{iri} and mapped into the useFieldArray structure.
 *
 * --- ENTITY-SEARCH LABEL RESOLUTION ---
 * - Entity-search fields store an IRI as value. On edit, the IRI is resolved to a human-readable
 *   label by searching the API so the async-select dropdown shows the correct selected option.
 *
 * --- RESET BEHAVIOUR ---
 * - The Reset button calls onReset() on the parent, which clears the selected record.
 * - When record becomes null the useEffect seeds a blank new-record form.
 * - This ensures Reset always produces a clean insert form, never re-populates the edited record.
 *
 * Props:
 *   shape        {object}       - Active shape descriptor from /api/shapes
 *   allShapes    {array}        - All shapes, forwarded to nested editors
 *   record       {object|null}  - Pre-selected record; resets the form when changed
 *   onValidation {function}     - Called with the SHACL ValidationResult
 *   onSaved      {function}     - Called after a successful write
 *   onReset      {function}     - Called when the user clicks Reset; parent should set record to null
 */
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { apiClient } from '../api/client.js'
import { buildJsonLdEntity } from '../utils/jsonld.js'
import { compactIri } from '../utils/prefixes.js'
// eslint-disable-next-line no-unused-vars
import FormField from './FormField.jsx'
import './ShapeForm.css'

export default function ShapeForm({ shape, allShapes, record, onValidation, onSaved, onReset }) {
  const [formSchema, setFormSchema] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const { register, handleSubmit, reset, control, formState } = useForm()

  useEffect(() => {
    if (!shape) return
    setFormSchema(null)
    apiClient
      .getFormSchema(shape.id)
      .then((res) => setFormSchema(res))
      .catch(console.error)
  }, [shape])

  // NOTE: triplesToFlatObject is defined inside the component because it is only
  // used within the component's effects and handlers. It is a pure function and
  // safe to hoist to module level if performance profiling shows re-creation cost.
  // Transform triples array to a flat { predicate: tripleObj } object
  // (first value per predicate, or array if multiple).
  // For literals, store the full triple object so language/datatype info is preserved.
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

  /**
   * Map a loaded record (triples from the backend) to form field values for react-hook-form.
   *
   * Handles all scalar field types synchronously. Two field types are handled
   * asynchronously in the useEffect instead:
   *   - 'nested'        — requires fetching each bridge entity's own triples
   *   - 'entity-search' — requires resolving IRIs to human-readable labels
   *
   * --- IMPORTANT: CREATE vs UPDATE ---
   * - When editing, this function must set formData['@id'] = record.id so the form state
   *   includes the identifier. This ensures that on submit, the payload will include @id
   *   and the backend will update the entity rather than creating a new one.
   */
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
        const values = Array.isArray(val) ? val : val ? [val] : []
        formData[field.path] = values.map((triple) => ({
          __value: triple.object ?? '',
          __lang: triple.language ?? 'en',
        }))
        // Always show at least one empty row so the list is never blank on edit
        if (formData[field.path].length === 0) {
          formData[field.path] = [{ __value: '', __lang: 'en' }]
        }
        continue
      }

      // --- Single language-tagged string (e.g. rdfs:label) ---
      // Stored as {field.path}.__value and {field.path}.__lang in form state,
      // matching the Controller names used by the lang-string widget in FormField.jsx.
      if (field.type === 'lang-string') {
        const triple = Array.isArray(val) ? val[0] : val
        if (
          triple &&
          typeof triple === 'object' &&
          'objectType' in triple &&
          triple.objectType === 'literal'
        ) {
          formData[`${field.path}.__value`] = triple.object
          formData[`${field.path}.__lang`] = triple.language ?? ''
        } else {
          formData[`${field.path}.__value`] = triple ? triple.object || String(triple) : ''
          formData[`${field.path}.__lang`] = 'en'
        }
      }

      // --- Language field (dcterms:language) ---
      // Stores the literal string value of the language code triple.
      // Falls back to empty string so the input is never left as undefined.
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
      // Falls back to empty string so the URL input is never left as undefined.
      else if (field.type === 'uri') {
        const triple = Array.isArray(val) ? val[0] : val
        if (triple && typeof triple === 'object') {
          if (triple.objectType === 'iri') {
            formData[field.path] = triple.object
          } else if (triple['@id']) {
            formData[field.path] = triple['@id']
          } else if (typeof triple.object === 'string') {
            formData[field.path] = triple.object
          } else {
            formData[field.path] = ''
          }
        } else if (typeof triple === 'string') {
          formData[field.path] = triple
        } else {
          formData[field.path] = ''
        }
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
      // Falls back to empty string so the input is never left as undefined.
      else if (field.type === 'temporal') {
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

      // --- Year and Number ---
      // Falls back to empty string so the input is never left as undefined.
      else if (field.type === 'year' || field.type === 'number') {
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

      // --- Generic fallback for objects with @value ---
      else if (val && typeof val === 'object' && val['@value']) {
        formData[field.path] = val['@value']
      } else {
        formData[field.path] = val
      }
    }

    return formData
  }

  useEffect(() => {
    if (!formSchema) return

    setSubmitError(null)

    if (!record || !record.id) {
      // New record: seed lang-string-list fields with one empty row so the
      // list widget is never blank on a fresh form.
      const defaults = {}
      for (const field of formSchema.fields) {
        if (field.type === 'lang-string-list') {
          defaults[field.path] = [{ __value: '', __lang: 'en' }]
        }
      }
      reset(defaults)
      return
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
      reset(mapped)
      return
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
                  entry[prop.path] = propVal
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
      reset(mapped)
    })
    // NOTE: `allShapes` and `resolveEntityLabel` are intentionally omitted from the
    // dependency array. `allShapes` rarely changes after initial load and re-running
    // the effect when it does would reset unsaved form edits. `resolveEntityLabel` is
    // a stable function in practice (defined once per render, not memoized). If
    // either causes stale-closure bugs in a future refactor, add them here.
  }, [record, shape, reset, formSchema])

  // --- Dirty field tracking ---
  // Used in onSubmit to build originalTriples: only predicates the user actually
  // changed are sent to the backend for deletion before the new values are inserted.
  // Nested/bridge fields are always excluded — their saves are handled by load_turtle
  // carrying the full graph including bridge triples.
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
      setSubmitError(err.response?.data?.detail ?? 'Save failed')
    } finally {
      setSubmitting(false)
    }
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

  return (
    <form className="shape-form" onSubmit={handleSubmit(onSubmit)} noValidate>
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
        {/* Reset clears the form back to a blank new-record state.
            onReset() tells the parent to deselect the current record,
            which causes record to become null and the useEffect to seed defaults. */}
        <button type="button" className="btn btn-ghost" onClick={() => onReset?.()}>
          Reset
        </button>
      </footer>
    </form>
  )
}
