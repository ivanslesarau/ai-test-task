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
  /** Which player profile the caller is currently looking at. Player/Parent
   * only, and null for every other role and for an account with no
   * reachable context (extension 2026-08-27, contract v1.2.0, FR-117). */
  active_player_profile_id: string | null
  /** The trainer half of the active pair. Null under the same conditions
   * as `active_player_profile_id`; the two are always both set or both
   * null. Changed only through `PUT /me/context`. */
  active_trainer_id: string | null
  /** How many switchable profile-and-trainer pairs the caller has,
   * replacing `trainer_count` (contract v1.2.0). The switcher renders
   * only above one (FR-118, FR-119). Zero for every non-player role. */
  context_count: number
  /** True when this account is a child's own sign-in — derived
   * server-side, never stored (research.md R-38). The interface uses it
   * to withhold the controls FR-132 forbids. */
  is_child_account: boolean
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
  /** What remains true of the *account* rather than of any one player on
   * it (contract v1.2.0, research.md R-34). `school`, `jersey_number`,
   * and `skill_level` moved to `PlayerProfile`, reached through
   * `/me/players`. */
  emergency_contact_name: string | null
  emergency_contact_phone: string | null
  emergency_contact_relation: string | null
  /** How many live player profiles the account holds. Zero is valid for
   * an account a Super Admin created. */
  profile_count: number
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
  /** Contract-unchanged (`openapi.yaml` still lists both): no role can
   * successfully submit either any more, now that they live on
   * `PlayerProfile` (data-model.md §35) — the server 422s them for every
   * role, including player_parent. The frontend form no longer offers
   * them (features/profile/edit-own), but the wire shape still accepts
   * them syntactically, so the type is not narrowed here. */
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

export type JoinViewerState =
  | 'anonymous'
  | 'can_join'
  | 'already_associated'
  | 'role_cannot_join'
  /** US11 (FR-137, FR-138): the caller is a signed-in child. The platform
   * has already raised an approval request and emailed the parent — the
   * join page only needs to explain this, not act again. */
  | 'child_must_ask_parent'
  /** US13 (FR-122): the caller is a parent holding at least one child
   * profile — ask who this trainer is for. `selectable_profiles` is
   * present only for this state. */
  | 'choose_family_members'

export interface JoinLinkPreview {
  trainer_display_name: string
  branding: PortalBranding
  viewer: { state: JoinViewerState; selectable_profiles?: JoinSelectableProfile[] }
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

/**
 * **Changed in 1.2.0** (Story 13, tasks.md T413/T414): a single join may
 * associate several family members, so the result reports sets rather
 * than one boolean.
 */
export interface JoinResult {
  trainer_id: string
  trainer_display_name: string
  associated_profile_ids: string[]
  already_associated_profile_ids: string[]
  active_player_profile_id: string | null
  active_trainer_id: string | null
}

export interface TrainerPlayerSummary {
  /** Changed in 1.2.0: names a player profile rather than an account —
   * `player_user_id` is gone (data-model.md §35, research.md R-49). */
  player_profile_id: string
  display_name: string
  kind: PlayerProfileKind
  age: number | null
  gender: string | null
  joined_at: string
  photo_url: string | null
  /** The account responsible for this player — the player themselves for
   * a `self` profile, the parent for a `child` (FR-113, FR-116). */
  responsible_contact: ResponsibleContact
}

export interface TrainerPlayerPage {
  items: TrainerPlayerSummary[]
  page: number
  page_size: number
  total: number
}

// -----------------------------------------------------------------------
// Extension (2026-08-27): family accounts, child sign-in, approvals
// Mirrors contracts/openapi.yaml v1.2.0.
// -----------------------------------------------------------------------

export type PlayerProfileKind = 'self' | 'child'

export interface ResponsibleContact {
  /** The adult a trainer contacts about a player. Never carries the
   * responsible account's identifier (FR-116, SC-040). */
  display_name: string
  email: string | null
  phone: string | null
}

export interface TrainingContextEntry {
  /** One switchable pair, replacing `TrainerContextEntry` (research.md
   * R-49). */
  player_profile_id: string
  player_display_name: string
  player_profile_kind: PlayerProfileKind
  trainer_id: string
  trainer_display_name: string
  branding: PortalBranding
  joined_at: string
}

export interface TrainingContextList {
  active_player_profile_id: string | null
  active_trainer_id: string | null
  contexts: TrainingContextEntry[]
}

export interface TrainingContextRequest {
  player_profile_id: string
  trainer_id: string
}

export interface PlayerProfileAssociation {
  association_id: string
  trainer_id: string
  trainer_display_name: string
  joined_at: string
}

export interface PlayerProfile {
  id: string
  kind: PlayerProfileKind
  display_name: string
  first_name: string | null
  last_name: string | null
  date_of_birth: string | null
  /** Derived from `date_of_birth`, never stored (R-31). */
  age: number | null
  gender: string | null
  school: string | null
  jersey_number: string | null
  /** Assigned by a trainer in a later feature. Never writable by the
   * family (FR-107). */
  skill_level: string | null
  photo_url: string | null
  tokens_without_approval: boolean
  has_sign_in: boolean
  associations: PlayerProfileAssociation[]
}

export interface PlayerProfileList {
  profiles: PlayerProfile[]
}

export interface CreateChildProfileRequest {
  first_name: string
  last_name: string
  date_of_birth: string
  gender: Gender
  school?: string | null
  jersey_number?: string | null
  trainer_ids?: string[]
  acknowledge_possible_duplicate?: boolean
}

export interface PlayerProfileUpdate {
  first_name?: string
  last_name?: string
  date_of_birth?: string
  gender?: Gender
  school?: string | null
  jersey_number?: string | null
  tokens_without_approval?: boolean
}

export interface DuplicateProfileError {
  error: {
    code: 'possible_duplicate_profile'
    message: string
    matches: PlayerProfile[]
  }
}

export interface AddPlayerTrainerRequest {
  code?: string | null
  trainer_id?: string | null
}

export interface GrantChildSignInRequest {
  email: string
}

export interface ChildSignIn {
  player_profile_id: string
  email: string
  invitation_sent: boolean
}

export interface JoinSelectableProfile {
  player_profile_id: string
  display_name: string
  kind: PlayerProfileKind
  already_associated: boolean
}

export interface JoinAcceptRequest {
  player_profile_ids?: string[]
}

export type ApprovalRequestKind = 'join_trainer' | 'usd_payment' | 'token_spend'

export type ApprovalRequestStatus =
  | 'pending_parent_approval'
  | 'info_requested'
  | 'approved'
  | 'denied'
  | 'expired'
  | 'withdrawn'

export interface ApprovalRequest {
  id: string
  player_profile_id: string
  player_display_name: string
  kind: ApprovalRequestKind
  status: ApprovalRequestStatus
  trainer_id: string | null
  trainer_display_name: string | null
  amount_minor: number | null
  currency: string | null
  requested_at: string
  expires_at: string
  parent_note: string | null
  child_note: string | null
  resolved_at: string | null
  resolved_by: 'parent' | 'child' | 'super_admin' | null
}

export interface ApprovalRequestPage {
  items: ApprovalRequest[]
  page: number
  page_size: number
  total: number
}

export interface ApprovalDecisionRequest {
  note?: string | null
}

export interface ApprovalInfoRequest {
  note: string
}
