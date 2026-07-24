/**
 * Shared react-select `styles` object for the dark editor theme.
 *
 * Used by every dropdown in the form layer — the async entity autocomplete
 * (<EntitySearch>) and the plain single-selects (<StyledSelect>: enum fields,
 * the polymorphic type chooser, language-tag pickers) — so they all render with
 * the same control, menu, and option styling instead of a native <select>.
 */
export const selectStyles = {
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
  // The menu is portaled to <body> (menuPortalTarget) so it is never clipped by
  // a short form or a panel with overflow: hidden; keep it above modals/panels.
  menuPortal: (base) => ({ ...base, zIndex: 9999 }),
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
