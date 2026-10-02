/**
 * The state contract for the icm-guard mod in `hooks/register.ts`.
 *
 * `fails` maps a workspace root to the FAIL lines the checker last reported for it,
 * so a write can be told apart from the backlog it inherited — the mod speaks only
 * when a write introduces a FAIL or clears the last one.
 *
 * `python` remembers which interpreter name answered (`python3`, `python` or `py`),
 * so the probe runs once per session rather than on every write.
 */

/** FAIL lines from the last check, keyed by workspace root. */
export type FailsByRoot = Record<string, string[]>

declare module 'claude-code' {
  interface PluginState {
    'icm-ops': { fails: FailsByRoot; python: string }
  }
}
