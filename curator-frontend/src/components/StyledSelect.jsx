/**
 * Themed single-select dropdown that matches the entity autocomplete look.
 *
 * Wraps react-select with the shared `selectStyles`, but stores a plain string
 * value (not a react-select `{value,label}` option object) so it drops straight
 * into the places that expect the raw value: enum (`sh:in`) fields, the
 * polymorphic `@type` chooser, and the language-tag pickers. Options are a
 * static `[{value, label}]` array; the component maps the current string value
 * to its option for display and hands the chosen string back via `onChange`.
 *
 * Props:
 *   options      {Array<{value,label}>} - Selectable options.
 *   value        {string}    - Current raw value ('' = nothing selected).
 *   onChange     {function}  - Called with the chosen raw value ('' when cleared).
 *   onBlur       {function=} - Optional blur handler (for react-hook-form).
 *   selectRef    {object=}   - Optional ref forwarded to react-select (focus on error).
 *   inputId      {string=}   - Underlying input id, so a <label htmlFor> can target it.
 *   placeholder  {string=}   - Placeholder text.
 *   isClearable  {boolean=}  - Whether the value can be cleared (default true).
 *   isSearchable {boolean=}  - Whether options can be filtered by typing (default true).
 */
import Select from 'react-select'
import { selectStyles } from './selectStyles.js'

export default function StyledSelect({
  options,
  value,
  onChange,
  onBlur,
  selectRef,
  inputId,
  placeholder = 'Select…',
  isClearable = true,
  isSearchable = true,
}) {
  const selected = options.find((o) => o.value === value) ?? null
  return (
    <Select
      inputId={inputId}
      ref={selectRef}
      options={options}
      value={selected}
      onChange={(opt) => onChange(opt ? opt.value : '')}
      onBlur={onBlur}
      placeholder={placeholder}
      isClearable={isClearable}
      isSearchable={isSearchable}
      styles={selectStyles}
      menuPlacement="auto"
      menuPortalTarget={typeof document !== 'undefined' ? document.body : undefined}
    />
  )
}
