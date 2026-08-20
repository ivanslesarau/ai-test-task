export type FieldKind = 'text' | 'textarea' | 'checkbox'

export interface FieldConfig {
  label: string
  kind: FieldKind
}

/** One entry per field OwnProfileUpdate can carry. Which of these actually
 * render is decided at runtime by the server's `editable_fields` — this
 * map only supplies presentation metadata, never the editability rule
 * itself (contracts/frontend-contracts.md §6). */
export const FIELD_CONFIG: Record<string, FieldConfig> = {
  first_name: { label: 'First name', kind: 'text' },
  last_name: { label: 'Last name', kind: 'text' },
  phone: { label: 'Phone', kind: 'text' },
  business_name: { label: 'Business name', kind: 'text' },
  address: { label: 'Address', kind: 'text' },
  website: { label: 'Website', kind: 'text' },
  description: { label: 'Description', kind: 'textarea' },
  bio: { label: 'Bio', kind: 'textarea' },
  credentials: { label: 'Credentials', kind: 'textarea' },
  certifications: { label: 'Certifications', kind: 'textarea' },
  is_publicly_visible: { label: 'Publicly visible profile', kind: 'checkbox' },
  school: { label: 'School', kind: 'text' },
  jersey_number: { label: 'Jersey number', kind: 'text' },
  emergency_contact_name: { label: 'Emergency contact name', kind: 'text' },
  emergency_contact_phone: { label: 'Emergency contact phone', kind: 'text' },
  emergency_contact_relation: { label: 'Emergency contact relation', kind: 'text' },
}

/** Field order within the form — fields not listed fall back to the order
 * the server returned them in. */
export const FIELD_ORDER = Object.keys(FIELD_CONFIG)
