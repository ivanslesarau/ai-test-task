export const joinKeys = {
  preview: (code: string) => ['join', 'preview', code] as const,
} as const
