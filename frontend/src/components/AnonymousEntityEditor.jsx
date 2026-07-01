/**
 * Inline editor for nested (bridge/helper) graph structures.
 *
 * This component is used in two contexts:
 *   1. As a nested editor inside a parent entity form (e.g., Source, Work) for bridge/helper shapes (like AgentRole).
 *   2. As a top-level form (direct navigation to e.g. /AgentRoleShape) for bridge/helper shapes.
 *
 * Policy:
 *   - Bridge/helper entities (e.g., AgentRole) should only be created/edited inline as connections from their parent entity.
 *   - Direct creation/editing of bridge entities via their own top-level form should be disabled, with a message to use the parent entity form.
 *
 * Shape role drives rendering:
 *   helper-bridge   - the nested shape is a pure relation container (no rdfs:label of its own).
 *                    Each inline card shows EntitySearch widgets for every entity-search property (core:isMemberOf, core:hasRole).
 *   external-entity - the nested shape has its own label; a note is shown directing the user to create it separately then reference it via search.
 *
 * Node creation:
 *   - When adding a bridge/helper entry, generate a regular node IRI (rfdb:ShapeType_<8hex>), not a blank node.
 *
 * Props:
 *   field      {object}  - Property descriptor (path, nestedShape, parentShape if nested)
 *   allShapes  {array}   - All shapes (used to resolve the nested shape metadata)
 *   control    {object}  - react-hook-form control (drives useFieldArray)
 */
import { useFieldArray } from 'react-hook-form'
// eslint-disable-next-line no-unused-vars
import EntitySearch from './EntitySearch.jsx'
import './AnonymousEntityEditor.css'

function getNestedShape(field, allShapes) {
  if (!field?.nestedShape || !Array.isArray(allShapes)) return null
  return allShapes.find((shape) => shape.id === field.nestedShape) ?? null
}

export default function AnonymousEntityEditor({ field, allShapes, control }) {
  const nestedShape = getNestedShape(field, allShapes)
  const { fields, append, remove } = useFieldArray({
    control,
    name: field.path,
  })

  // Helper-bridge shapes (e.g., AgentRole) are only editable inline via parent entity.
  // The disabling logic for top-level forms is handled in ShapeForm.jsx.
  const isHelperBridge = nestedShape?.shapeRole === 'helper-bridge'

  function addHelperEntry() {
    // Generate a regular named node IRI in the rfdb: namespace rather than a blank node.
    // Format: rfdb:<ShapeType>_<8hexchars>  (e.g. rfdb:core_AgentRole_a3f2b1c9)
    //
    // NOTE: nestedShape.targetClass is a CURIE like "core:AgentRole".
    // replace(':', '_') produces "core_AgentRole" so the generated IRI becomes
    // rfdb:core_AgentRole_<hex>, which is intentional: the prefix part is kept to
    // avoid collisions across shapes that may share local names.
    // This must match the backend assign_entity_id logic; verify if that changes.
    function randomHex(len = 8) {
      return Math.random()
        .toString(16)
        .slice(2, 2 + len)
    }
    const shapeType = (nestedShape?.targetClass || 'Entity').replace(':', '_')
    const entry = {
      '@id': `rfdb:${shapeType}_${randomHex(8)}`,
      '@type': nestedShape?.targetClass ?? '',
    }
    append(entry)
  }

  return (
    <div className="nested-editor">
      <div className="nested-editor-header">
        <span className="nested-editor-title">
          {isHelperBridge ? 'Connections' : 'Inline entries'}
        </span>
        <button type="button" className="btn btn-ghost btn-sm" onClick={addHelperEntry}>
          Add
        </button>
      </div>

      {nestedShape && !isHelperBridge && (
        <p className="nested-editor-note">
          Nested shape <span className="mono">{nestedShape.label}</span> is modeled as an external
          entity. Use reference fields to associate existing records.
        </p>
      )}

      {fields.length === 0 && <p className="nested-editor-empty">No inline entities yet.</p>}

      <div className="nested-editor-list">
        {fields.map((item, index) => (
          <div key={item.id} className="nested-card">
            <div className="nested-card-header">
              <span className="nested-card-title mono">Entry {index + 1}</span>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => remove(index)}>
                Remove
              </button>
            </div>
            {isHelperBridge && nestedShape ? (
              <div className="nested-fields">
                {nestedShape.properties
                  .filter((prop) => prop.path !== 'rdf:type')
                  .map((prop) => {
                    const nestedName = `${field.path}.${index}.${prop.path}`
                    if (prop.type === 'entity-search') {
                      return (
                        <div key={nestedName} className="field-group">
                          <label className="field-label">{prop.name}</label>
                          <EntitySearch field={prop} control={control} name={nestedName} />
                        </div>
                      )
                    }
                    return (
                      <div key={nestedName} className="field-group">
                        <label className="field-label">{prop.name}</label>
                        <input
                          className="field-input"
                          value={item[prop.path] ?? ''}
                          readOnly
                          placeholder="Bridge helper uses existing entity associations"
                        />
                      </div>
                    )
                  })}
              </div>
            ) : (
              <input
                className="field-input"
                value={item.roleType ?? ''}
                readOnly
                placeholder="Helper bridge rendering applies only to helper shapes"
              />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
