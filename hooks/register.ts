/**
 * icm-guard — the checker, at the moment of the write.
 *
 * `icm_check.py` already knows every rule this pack enforces. What it cannot do is
 * choose when to run: a session learns what it broke at the next maintenance pass,
 * by which time the cheap fix has become a compaction. A binding budget crossed on
 * the third write of a session is discovered on the thirtieth.
 *
 * So this runs the SHIPPED checker after a write inside a workspace and reports only
 * what CHANGED. No second checker and no restated rules — a rule in two places drifts,
 * and a budget owned twice is how an off-by-one reaches a binding threshold.
 *
 * It never denies. The checker is the authority; this is the doorbell.
 *
 * It reports to the AGENT, not the person: a workspace is written by the agent walking
 * it, so the person is not the one who can act on "this write crossed a budget". The
 * finding goes in the tool result's `context`, which the model reads and the person
 * never sees. A toast here would interrupt someone about something they did not do.
 * The status line stays, because a standing FAIL count is worth a glance.
 *
 * Quiet by design: it speaks only when a write introduces a FAIL or clears the last
 * one. Steady state says nothing, because a signal that fires every turn stops being
 * read — the same failure as a build light that is always red.
 */
import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

/** A workspace is a directory holding `00-catalog/`. */
const MARKER = '00-catalog'
const CHECKER = 'skills/icm-maintain/scripts/icm_check.py'

type Check = { version: string; today: string; fail: string[]; warn: string[]; info: string[] }

const seen = atom({ plugin: 'icm-ops', key: 'fails' } as const, {})
const python = atom({ plugin: 'icm-ops', key: 'python' } as const, '')

function dirOf(p: string): string {
  const i = Math.max(p.lastIndexOf('/'), p.lastIndexOf('\\'))
  return i <= 0 ? '' : p.slice(0, i)
}

/** Walk up from the written file for the nearest directory containing `00-catalog/`. */
async function workspaceOf($: any, file: string): Promise<string | null> {
  let dir = dirOf(file)
  for (let i = 0; i < 12 && dir; i += 1) {
    try {
      if (await $.fs.exists(dir + '/' + MARKER)) return dir
    } catch {
      return null
    }
    const up = dirOf(dir)
    if (up === dir) break
    dir = up
  }
  return null
}

/** `python3` on macOS and Linux; `python` or `py` on Windows. Resolved once. */
async function interpreter($: any): Promise<string | null> {
  const remembered = await read($, python)
  if (remembered) return remembered
  for (const cmd of ['python3', 'python', 'py']) {
    try {
      const { exitCode } = await $.process.run([cmd, '--version'], { timeoutMs: 8000 })
      if (exitCode === 0) {
        await update($, python, () => cmd)
        return cmd
      }
    } catch {
      // try the next one
    }
  }
  return null
}

async function checkWorkspace($: any, root: string): Promise<string | null> {
  const py = await interpreter($)
  if (!py) return null
  const script = root + '/' + CHECKER
  if (!(await $.fs.exists(script))) return null // the pack is not installed in this workspace

  const { exitCode, stdout } = await $.process.run([py, script, root, '--json'], {
    cwd: root,
    timeoutMs: 30000,
  })
  // The checker exits non-zero when it FAILS, which is a result, not an error.
  if (!stdout.trim() || (exitCode !== 0 && exitCode !== 1)) return null

  const result = JSON.parse(stdout.trim()) as Check
  const before: string[] = (await read($, seen))[root] ?? []
  const now = result.fail

  const introduced = now.filter(f => !before.includes(f))
  const cleared = before.filter(f => !now.includes(f))
  await update($, seen, s => ({ ...s, [root]: now }))

  $.ui.status(now.length > 0 ? `icm ${now.length} FAIL` : undefined)

  if (introduced.length > 0) {
    return (
      'icm-ops: this write FAILS the workspace checker.\n' +
      introduced.map(f => '- ' + f).join('\n') +
      '\nFix it now — it is cheaper than the compaction it becomes. ' +
      'Full detail: python ' + CHECKER + ' ' + root
    )
  }
  if (cleared.length > 0 && now.length === 0) return 'icm-ops: workspace checker is clear, 0 FAIL.'
  return null
}

export const register: Register = on => {
  for (const tool of ['Write', 'Edit', 'NotebookEdit'] as const) {
    on('tool.call', { tool }, async ($, e, next) => {
      const file: unknown = (e as any).file_path ?? (e as any).notebook_path
      if (typeof file !== 'string' || file.length === 0) return next(e)

      const ran = await next(e)
      if (ran.deny !== undefined || ran.isError === true) return ran

      try {
        const root = await workspaceOf($, file.replace(/\\/g, '/'))
        const note = root ? await checkWorkspace($, root) : null
        // `context` is read by the model after the tool's result and never shown to
        // the person — the agent is the one who writes here, so the agent is told.
        if (note) return { ...ran, context: [...(ran.context ?? []), note] }
      } catch {
        // A guard that errors must never look like a workspace that failed.
      }
      return ran
    })
  }
}
