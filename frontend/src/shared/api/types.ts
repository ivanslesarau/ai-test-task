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
  /** Player/Parent only; null for every other role and for a player who
   * belongs to no trainer (extension 2026-08-26, FR-086). */
  active_trainer_id: string | null
  /** How many switchable trainers the caller has. Zero for every
   * non-player role. The switcher renders only above one (FR-088). */
  trainer_count: number
  /** Resolved server-side per FR-101 — a trainer's own, a player's
   * active context's, or the platform default. Coaches receive the
   * default until US-01.08 (research.md R-33). */
  portal_branding: PortalBranding
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

// -----------------------------------------------------------------------
// Extension (2026-08-26): ShareLink onboarding, multi-trainer, branding
// Mirrors contracts/openapi.yaml v1.1.0.
// -----------------------------------------------------------------------

export type Gender = 'male' | 'female' | 'other' | 'prefer_not_to_say'
export type ShareLinkKind = 'player_standing' | 'coach_single_use'

export interface PortalBranding {
  logo_url: string | null
  primary_color: string | null
  updated_at: string | null
}

export interface PortalBrandingUpdate {
  primary_color?: string | null
}

export interface ShareLink {
  id: string
  code: string
  url: string
  kind: ShareLinkKind
  is_active: boolean
  use_count: number
  expires_at: string | null
  max_uses: number | null
  created_at: string
}

export type JoinViewerState = 'anonymous' | 'can_join' | 'already_associated' | 'role_cannot_join'

export interface JoinLinkPreview {
  trainer_display_name: string
  branding: PortalBranding
  viewer: { state: JoinViewerState }
}

export interface JoinRegistrationRequest {
  first_name: string
  last_name: string
  email: string
  password: string
  phone: string
  is_self: boolean
  player_name: string | null
  date_of_birth: string
  gender: Gender
}

export interface JoinResult {
  trainer_id: string
  trainer_display_name: string
  already_associated: boolean
  active_trainer_id: string
}

export interface TrainerContextEntry {
  trainer_id: string
  display_name: string
  branding: PortalBranding
  joined_at: string
}

export interface TrainerContextList {
  active_trainer_id: string | null
  trainers: TrainerContextEntry[]
}

export interface TrainerContextRequest {
  trainer_id: string
}

export interface TrainerPlayerSummary {
  player_user_id: string
  display_name: string
  is_self: boolean
  age: number | null
  gender: string | null
  joined_at: string
  photo_url: string | null
}

export interface TrainerPlayerPage {
  items: TrainerPlayerSummary[]
  page: number
  page_size: number
  total: number
}
