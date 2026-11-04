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

/** Run the shipped checker on a workspace: its FAIL lines, or null when it could not run. */
async function failsOf($: any, root: string): Promise<{ py: string; script: string; fails: string[] } | null> {
  const py = await interpreter($)
  if (!py) return null
  // The checker ships inside this plugin, not inside the workspace it checks.
  const script = String($.plugin.root).replace(/[\\/]+$/, '') + '/' + CHECKER
  if (!(await $.fs.exists(script))) return null

  const { exitCode, stdout } = await $.process.run([py, script, root, '--json'], {
    cwd: root,
    timeoutMs: 30000,
  })
  // The checker exits non-zero when it FAILS, which is a result, not an error.
  if (!stdout.trim() || (exitCode !== 0 && exitCode !== 1)) return null
  return { py, script, fails: (JSON.parse(stdout.trim()) as Check).fail }
}

/** Workspaces whose baseline was tried: a checker that gives no result is tried once, not before every write. */
const baselined = new Set<string>()

/** Before a session's first write to a workspace, record the FAILs it inherited, silently. */
async function baseline($: any, root: string): Promise<void> {
  if (baselined.has(root) || (await read($, seen))[root] !== undefined) return
  baselined.add(root)
  const r = await failsOf($, root)
  if (r) await update($, seen, s => ({ ...s, [root]: r.fails }))
}

/** One argument of a command line a person or agent can paste: quoted when it holds a space. */
const arg = (s: string) => (/\s/.test(s) ? `"${s}"` : s)

async function checkWorkspace($: any, root: string): Promise<string | null> {
  const r = await failsOf($, root)
  if (!r) return null
  const before: string[] = (await read($, seen))[root] ?? []
  const now = r.fails

  const introduced = now.filter(f => !before.includes(f))
  const cleared = before.filter(f => !now.includes(f))
  await update($, seen, s => ({ ...s, [root]: now }))

  $.ui.status(now.length > 0 ? `icm ${now.length} FAIL` : undefined)

  if (introduced.length > 0) {
    return (
      'icm-ops: this write FAILS the workspace checker.\n' +
      introduced.map(f => '- ' + f).join('\n') +
      '\nFix it now — it is cheaper than the compaction it becomes. ' +
      'Full detail: ' + [r.py, r.script, root].map(arg).join(' ')
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

      const path = file.replace(/\\/g, '/')
      const found = await workspaceOf($, path).catch(() => null)
      // The FAILs the workspace already had, so this write is not blamed for them.
      if (found) await baseline($, found).catch(() => undefined)

      const ran = await next(e)
      if (ran.deny !== undefined || ran.isError === true) return ran

      try {
        // A write can create the workspace itself (its 00-catalog/), so look again after it.
        const root = found ?? (await workspaceOf($, path))
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
