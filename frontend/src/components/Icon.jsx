/**
 * Thin wrapper around lucide-react icons.
 *
 * Looks up the icon by `name` in the lucide-react export map and renders it
 * with the given size and strokeWidth. Returns null silently when `name` does
 * not match any lucide icon (avoids crashing on unknown icon names).
 *
 * Props:
 *   name        {string}  - Lucide icon name (PascalCase, e.g. "Pencil", "Eye", "Trash")
 *   size        {number}  - Icon size in pixels (default: 16)
 *   strokeWidth {number}  - SVG stroke width (default: 1.75)
 *   className   {string}  - Additional CSS class
 *   aria-label  {string}  - Accessible label forwarded to the SVG element
 */
import * as LucideIcons from 'lucide-react'

export default function Icon({
  name,
  size = 16,
  strokeWidth = 1.75,
  className = '',
  'aria-label': ariaLabel,
}) {
  const LucideIcon = LucideIcons[name]
  if (!LucideIcon) return null
  return (
    <LucideIcon
      size={size}
      strokeWidth={strokeWidth}
      className={className}
      aria-label={ariaLabel}
    />
  )
}
