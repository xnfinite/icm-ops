/**
 * What `probe-first` keeps within one turn.
 *
 * `tools` are the verifying tool calls made since the person's last prompt; an
 * absolute is only flagged when that list is empty. `flagged` caps the mod at one
 * nudge per turn, because a guard that speaks repeatedly stops being read.
 */
export type TurnProbe = { tools: string[]; flagged: boolean }

declare module 'claude-code' {
  interface PluginState {
    'probe-first': { turn: TurnProbe }
  }
}
