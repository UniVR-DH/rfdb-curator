/**
 * Dynamic list of language-tagged string inputs.
 *
 * Renders one row per entry, each with a text input and a language selector.
 * Entries are managed by react-hook-form's `useFieldArray` under `path`.
 * Each item is stored in form state as `{ __value: string, __lang: string }`.
 *
 * Validation: only the first row (index 0) is required when `isRequired` is true.
 * Empty rows beyond the first are allowed so the user can start typing without
 * immediately triggering validation errors.
 *
 * The `label` prop accepts a React node (typically a `<label>` element rendered
 * by the parent FormField) or `null`/`undefined` to suppress the label entirely.
 * FormField always passes `null` here because it renders its own label above.
 *
 * Props:
 *   path       {string}       - react-hook-form field array name (e.g. "skos:altLabel")
 *   label      {ReactNode}    - Optional label node to render above the list, or null
 *   control    {object}       - react-hook-form control object
 *   isRequired {boolean}      - Whether the first entry is required
 */
// eslint-disable-next-line no-unused-vars
import { useFieldArray, Controller } from 'react-hook-form'

const LANG_OPTIONS = ['en', 'it', 'de', 'ru', 'fr', 'la']

export default function LangStringList({ path, label, control, isRequired }) {
  const { fields, append, remove } = useFieldArray({ control, name: path })

  return (
    <div className="field-group">
      {label}

      {fields.map((item, index) => (
        <div key={item.id} className="lang-field lang-field-row">
          <Controller
            name={`${path}.${index}.__value`}
            control={control}
            defaultValue=""
            rules={{ required: isRequired && index === 0 }}
            render={({ field }) => (
              <input className="field-input" type="text" placeholder="Value…" {...field} />
            )}
          />
          <Controller
            name={`${path}.${index}.__lang`}
            control={control}
            defaultValue="en"
            render={({ field }) => (
              <select className="field-lang" {...field}>
                {LANG_OPTIONS.map((l) => (
                  <option key={l} value={l}>
                    {l.toUpperCase()}
                  </option>
                ))}
              </select>
            )}
          />
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

      <button
        type="button"
        className="btn btn-ghost btn-add-lang"
        onClick={() => append({ __value: '', __lang: 'en' })}
      >
        + Add label
      </button>
    </div>
  )
}
