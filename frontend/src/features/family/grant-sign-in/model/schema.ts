import { z } from 'zod'

/** Mirrors `GrantChildSignInRequest` (contracts/openapi.yaml). A factory,
 * not a static schema: FR-129's "the parent's own address is refused
 * rather than shared" is checked client-side too, so the common mistake
 * is caught before a round trip (the lesson of D-06) — but the value to
 * compare against is the signed-in account's own email, known only at
 * render time. The server still enforces the platform-wide uniqueness
 * rule regardless; this is a UX shortcut, not the actual barrier. */
export function buildGrantChildSignInSchema(ownEmail: string) {
  return z.object({
    email: z
      .string()
      .min(1, 'Email is required')
      .max(320)
      .email('Enter a valid email address')
      .refine(
        (value) => value.trim().toLowerCase() !== ownEmail.trim().toLowerCase(),
        "That's your own email — a child needs an address of their own",
      ),
  })
}

export type GrantChildSignInValues = z.infer<ReturnType<typeof buildGrantChildSignInSchema>>
