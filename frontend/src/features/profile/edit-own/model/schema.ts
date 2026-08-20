import { z } from 'zod'

/** Mirrors OwnProfileUpdate (contracts/openapi.yaml). Every field optional
 * — the server decides, per FR-033, which of these a given role may
 * actually submit; this schema only validates shape and format. */
export const ownProfileUpdateSchema = z.object({
  first_name: z.string().min(1).max(100).optional(),
  last_name: z.string().min(1).max(100).optional(),
  phone: z.string().max(32).optional(),
  business_name: z.string().min(1).max(200).optional(),
  address: z.string().max(500).optional(),
  website: z.string().max(500).optional(),
  description: z.string().max(2000).optional(),
  bio: z.string().max(2000).optional(),
  credentials: z.string().max(1000).optional(),
  certifications: z.string().max(1000).optional(),
  is_publicly_visible: z.boolean().optional(),
  school: z.string().max(200).optional(),
  jersey_number: z.string().max(10).optional(),
  emergency_contact_name: z.string().max(200).optional(),
  emergency_contact_phone: z.string().max(32).optional(),
  emergency_contact_relation: z.string().max(100).optional(),
})

export type OwnProfileUpdateValues = z.infer<typeof ownProfileUpdateSchema>
