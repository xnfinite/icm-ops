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
 * Quiet by design: a toast only when a write introduces a FAIL or clears one. Steady
 * state says nothing, because a guard that speaks every turn stops being read — the
 * same failure as a build signal that is always red.
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

async function checkWorkspace($: any, root: string): Promise<void> {
  const py = await interpreter($)
  if (!py) return
  const script = root + '/' + CHECKER
  if (!(await $.fs.exists(script))) return // the pack is not installed in this workspace

  const { exitCode, stdout } = await $.process.run([py, script, root, '--json'], {
    cwd: root,
    timeoutMs: 30000,
  })
  // The checker exits non-zero when it FAILS, which is a result, not an error.
  if (!stdout.trim() || (exitCode !== 0 && exitCode !== 1)) return

  const result = JSON.parse(stdout.trim()) as Check
  const before: string[] = (await read($, seen))[root] ?? []
  const now = result.fail

  const introduced = now.filter(f => !before.includes(f))
  const cleared = before.filter(f => !now.includes(f))
  await update($, seen, s => ({ ...s, [root]: now }))

  if (introduced.length > 0) {
    $.ui.toast('icm-ops — this write FAILS the checker:\n' + introduced.map(f => '· ' + f).join('\n'))
  } else if (cleared.length > 0 && now.length === 0) {
    $.ui.toast('icm-ops — checker clear: 0 FAIL')
  }
  $.ui.status(now.length > 0 ? `icm ${now.length} FAIL` : undefined)
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
        if (root) await checkWorkspace($, root)
      } catch {
        // A guard that errors must never look like a workspace that failed.
      }
      return ran
    })
  }
}
