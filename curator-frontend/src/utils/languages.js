/**
 * Language acronym → human-readable name mapping for language-tag dropdowns.
 *
 * Single source of truth for the ordered set of language options offered in
 * `<FormField>` and `<LangStringList>` selectors. Keys are lowercase BCP-47 /
 * xsd language codes; values are the English display names.
 *
 * To expose a new language in the UI, add one entry here — both dropdowns pick
 * it up automatically.
 */
export const LANGUAGE_NAMES = {
  en: 'English',
  it: 'Italian',
  de: 'German',
  ru: 'Russian',
  fr: 'French',
  la: 'Latin',
}

/** Ordered list of language codes, derived from LANGUAGE_NAMES insertion order. */
export const LANG_OPTIONS = Object.keys(LANGUAGE_NAMES)

/**
 * Format a language code for display, e.g. "en" → "English (EN)".
 * Unknown codes fall back to the upper-cased code alone.
 *
 * @param {string} code - Lowercase language code.
 * @returns {string} Display label.
 */
export function languageLabel(code) {
  const name = LANGUAGE_NAMES[code]
  return name ? `${name} (${code.toUpperCase()})` : code.toUpperCase()
}
