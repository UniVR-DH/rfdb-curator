/**
 * DEBUG UTILITY — do not leave imported in production code.
 *
 * Renders a collapsible <details> panel showing the raw `record` and
 * `formSchema.fields` passed to the form. Useful during development to
 * verify what data the backend returns and how it maps into form state.
 *
 * To use: import and drop <DebugRecord record={record} formSchema={formSchema} />
 * anywhere inside ShapeForm while debugging.  Remove before committing.
 */
export default function DebugRecord({ record, formSchema }) {
  return (
    <details
      style={{ background: '#f8f8f8', padding: '1em', margin: '1em 0', border: '1px solid #eee' }}
    >
      <summary>Debug: record & formSchema</summary>
      <pre>{JSON.stringify({ record, fields: formSchema?.fields }, null, 2)}</pre>
    </details>
  )
}
