/**
 * Hand-maintained mirror of specs/001-user-roles-admin/contracts/openapi.yaml.
 * No `any` anywhere (constitution Principle II) — role detail is a
 * discriminated union narrowed by `role`, not an index signature.
 */

export type UserRole = 'super_admin' | 'trainer' | 'coach' | 'player_parent'
export type AccountStatus = 'active' | 'inactive' | 'deleted'

export interface CurrentUser {
  id: string
  email: string
  role: UserRole
  status: AccountStatus
  first_name: string
  last_name: string
  photo_url: string | null
}

export interface TrainerDetail {
  business_name: string
  address: string | null
  website: string | null
  description: string | null
}

export interface CoachDetail {
  bio: string | null
  credentials: string | null
  certifications: string | null
  is_publicly_visible: boolean
}

export interface PlayerParentDetail {
  school: string | null
  jersey_number: string | null
  /** Assigned by a trainer in a later feature. Never writable here. */
  skill_level: string | null
  emergency_contact_name: string | null
  emergency_contact_phone: string | null
  emergency_contact_relation: string | null
}

export type RoleDetail = TrainerDetail | CoachDetail | PlayerParentDetail | null

export interface OwnProfile {
  id: string
  email: string
  role: UserRole
  status: AccountStatus
  created_at: string
  first_name: string
  last_name: string
  phone: string | null
  photo_url: string | null
  thumbnail_url: string | null
  role_detail: RoleDetail
  editable_fields: string[]
}

export interface OwnProfileUpdate {
  first_name?: string
  last_name?: string
  phone?: string | null
  business_name?: string
  address?: string | null
  website?: string | null
  description?: string | null
  bio?: string | null
  credentials?: string | null
  certifications?: string | null
  is_publicly_visible?: boolean
  school?: string | null
  jersey_number?: string | null
  emergency_contact_name?: string | null
  emergency_contact_phone?: string | null
  emergency_contact_relation?: string | null
}

export interface PhotoUrls {
  photo_url: string
  thumbnail_url: string
}

export type AvailableAction = 'deactivate' | 'reactivate' | 'erase' | 'reinvite'

export interface UserSummary {
  id: string
  email: string
  first_name: string
  last_name: string
  role: UserRole
  status: AccountStatus
  created_at: string
  thumbnail_url: string | null
  has_password: boolean
}

export interface UserDetail extends UserSummary {
  version: number
  phone: string | null
  photo_url: string | null
  role_detail: RoleDetail
  last_login_at: string | null
  available_actions: AvailableAction[]
}

export interface UserPage {
  items: UserSummary[]
  page: number
  page_size: number
  total: number
}

export interface CreateUserRequest {
  role: UserRole
  email: string
  first_name: string
  last_name: string
  phone: string
  business_name?: string
}

export interface CreatedUser {
  user: UserDetail
  invitation_sent: boolean
  invitation_expires_at: string
}

export interface StatusChangeRequest {
  version: number
}

export interface EraseUserRequest {
  version: number
  reason: string
}

export type AuditAction =
  | 'user_created'
  | 'invitation_issued'
  | 'invitation_consumed'
  | 'user_deactivated'
  | 'user_reactivated'
  | 'user_erased'
  | 'permission_denied'

export interface AuditActor {
  id: string
  display_name: string
}

export interface AuditEntry {
  id: string
  action: AuditAction
  actor: AuditActor | null
  reason: string | null
  detail: string | null
  occurred_at: string
}

export interface AuditPage {
  items: AuditEntry[]
  page: number
  page_size: number
  total: number
}

export interface ErasureRecord {
  user_id: string
  original_email: string
  original_first_name: string
  original_last_name: string
  erased_by: AuditActor
  reason: string
  erased_at: string
}

export interface LoginRequest {
  email: string
  password: string
}
