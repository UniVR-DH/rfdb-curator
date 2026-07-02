/**
 * Dynamic list of URI inputs.
 *
 * Renders one URL input row per value and persists values as string[]
 * under the given form path.
 */
import { useFieldArray, Controller } from 'react-hook-form'

export default function UriList({ path, label, control, isRequired }) {
  const { fields, append, remove } = useFieldArray({ control, name: path })

  return (
    <div className="field-group">
      {label}

      {fields.map((item, index) => (
        <div key={item.id} className="lang-field lang-field-row">
          <Controller
            name={`${path}.${index}`}
            control={control}
            defaultValue=""
            rules={{ required: isRequired && index === 0 }}
            render={({ field }) => (
              <input className="field-input mono" type="url" placeholder="https://…" {...field} />
            )}
          />
          <div />
          <button
            type="button"
            className="btn-remove-lang"
            onClick={() => remove(index)}
            aria-label="Remove"
          >
            ✕
          </button>
        </div>
      ))}

      <button type="button" className="btn btn-ghost btn-add-lang" onClick={() => append('')}>
        + Add URI
      </button>
    </div>
  )
}