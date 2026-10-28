/**
 * icm-gates: a change to a guarded file does not go live until its own tests pass on that exact content.
 *
 * WHY. When agents write the code, the work moves from writing it to checking it. The checking that gets
 * skipped is the one at the worst moment: a fix installed before its suite ran. One builder session did
 * exactly that to a publish service and refused a real release for a minute; its tests, run a minute
 * later, failed at once. A paragraph telling the agent to test first is skimmed under momentum, so this
 * mod makes the install command itself the checkpoint.
 *
 * HOW. A workspace lists its gates in icm-gates.json at its root (or the file ICM_GATES_CONFIG names):
 *
 *   { "gates": [ { "name": "broker", "files": ["admin/broker.py"], "test": ["python", "tests/broker.py"],
 *                  "install": "\\binstall-broker\\.sh\\b", "max_lines": 400, "rules": "admin/BROKER-RULES.md" } ] }
 *
 * - A shell command matching a gate's `install` pattern: the mod reads the gate's files. A file over
 *   `max_lines` refuses the install (split it first). If this exact content already passed, the install
 *   runs. Otherwise the mod runs `test` itself and lets the install run only on exit 0, remembering the
 *   content that passed. A failing suite refuses with its last lines; a suite that cannot run refuses too.
 * - A write to a gated file: a note to the agent if the file is now over its limit, and once per gate per
 *   session a reminder that a gated change gets a second reader before it installs (skill icm-gates).
 *
 * It is a checkpoint for an honest agent under momentum, not a wall against a hostile one. With no config
 * it does nothing, and it never reads or changes the icm-ops core, its checker or icm-ops.json. It fails
 * CLOSED for an install it cannot check, which is the point of a gate; everything else fails open.
 */
import type { Register } from 'claude-code'

const NAME = 'icm-gates'
const SHELLS = /^(Bash|PowerShell)$/

type Gate = {
  name: string
  files: string[]
  test: string[]
  install: string
  max_lines?: number
  rules?: string
  timeout_minutes?: number
}
type Config = { root: string; gates: Gate[] } | null

const reminded = new Set<string>() // gate names already reminded this session

/** Two independent 32-bit hashes and the length: an accidental match is not a realistic event here. */
function fingerprint(text: string): string {
  let a = 0x811c9dc5
  let b = 5381
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i)
    a = Math.imul(a ^ c, 0x01000193) >>> 0
    b = (Math.imul(b, 33) + c) >>> 0
  }
  return `${a.toString(16)}-${b.toString(16)}-${text.length}`
}

/** wc -l semantics, the same line count the icm-ops checker uses. */
function lines(text: string): number {
  if (!text) return 0
  return text.split('\n').length - (text.endsWith('\n') ? 1 : 0)
}

const norm = (p: string) => p.replace(/\\/g, '/').replace(/\/+/g, '/').toLowerCase()
const absolute = (p: string) => /^([a-zA-Z]:[\\/]|[\\/])/.test(p)
const join = (root: string, p: string) => (absolute(p) ? p : `${root.replace(/[\\/]+$/, '')}/${p}`)

async function safe<T>(value: Promise<T>, fallback: T): Promise<T> {
  try {
    return await value
  } catch {
    return fallback
  }
}

async function load($: any): Promise<Config> {
  const override = await safe<string | undefined>($.env.get('ICM_GATES_CONFIG'), undefined)
  const cwd = String(await safe($.session.cwd(), ''))
  const path = override || `${cwd.replace(/[\\/]+$/, '')}/icm-gates.json`
  if (!(await safe($.fs.exists(path), false))) return null
  const raw = JSON.parse(String(await $.fs.read(path)).replace(/^﻿/, ''))
  const root = path.replace(/[\\/][^\\/]*$/, '')
  const gates = Array.isArray(raw?.gates) ? (raw.gates as Gate[]) : []
  return { root, gates }
}

function problem(g: Gate): string | null {
  if (!g || typeof g.name !== 'string' || !/^[a-z0-9][a-z0-9-]{0,47}$/.test(g.name)) return 'a gate needs a name of lowercase letters, digits and hyphens'
  if (!Array.isArray(g.files) || g.files.length === 0) return `gate ${g.name} names no files`
  if (!Array.isArray(g.test) || g.test.length === 0 || !g.test.every(a => typeof a === 'string')) return `gate ${g.name} has no test command (an argv list)`
  if (typeof g.install !== 'string' || !g.install) return `gate ${g.name} has no install pattern`
  return null
}

function tail(text: string, n: number): string {
  return text.trim().split('\n').slice(-n).join('\n')
}

export const register: Register = on => {
  // ---- the install command is the checkpoint --------------------------------------------------
  on('tool.call', async ($: any, e: any, next: any) => {
    const tool = String(e.tool ?? '')
    const cmd = typeof e.command === 'string' ? e.command : ''
    if (!SHELLS.test(tool) || !cmd) return next(e)
    let cfg: Config
    try {
      cfg = await load($)
    } catch (err) {
      return next(e) // no readable config: nothing is gated, so nothing is refused
    }
    if (!cfg) return next(e)
    const hits = cfg.gates.filter(g => {
      try {
        return typeof g?.install === 'string' && new RegExp(g.install, 'i').test(cmd)
      } catch {
        return false
      }
    })
    if (hits.length === 0) return next(e)

    const notes: string[] = []
    for (const g of hits) {
      const bad = problem(g)
      if (bad) return { deny: `${NAME}: this install is gated but the gate is broken (${bad}); fix icm-gates.json first.` }
      let text = ''
      for (const f of g.files) {
        const p = join(cfg.root, f)
        let body: string
        try {
          body = String(await $.fs.read(p))
        } catch {
          return { deny: `${NAME}: gate ${g.name} names ${f}, which cannot be read; the install was not run.` }
        }
        const n = lines(body)
        if (g.max_lines && n > g.max_lines) {
          return {
            deny:
              `${NAME}: ${f} is ${n} lines, over gate ${g.name}'s limit of ${g.max_lines}. Split it by ` +
              'responsibility before it installs; a file that keeps growing is where review stops working.',
          }
        }
        text += `\u0000${norm(f)}\u0000${body}`
      }
      const print = fingerprint(text)
      const key = `green:${g.name}`
      if ((await safe($.store.get(key), undefined)) === print) continue

      const minutes = Math.max(1, Math.min(60, g.timeout_minutes ?? 10))
      let r: any
      try {
        r = await $.process.run(g.test, { cwd: cfg.root, timeoutMs: minutes * 60000 })
      } catch (err) {
        return {
          deny:
            `${NAME}: gate ${g.name}'s suite (${g.test.join(' ')}) could not run or did not finish in ` +
            `${minutes} min, so the install was not run. ${String((err as any)?.message ?? err).slice(0, 200)}`,
        }
      }
      if (r.exitCode !== 0) {
        return {
          deny:
            `${NAME}: gate ${g.name}'s suite failed (exit ${r.exitCode}) on the files as they stand, so the ` +
            `install was not run. Fix the code, never the test. Last lines:\n` +
            tail(`${r.stdout ?? ''}\n${r.stderr ?? ''}`, 15),
        }
      }
      await safe($.store.set(key, print), undefined)
      notes.push(`${NAME}: gate ${g.name}'s suite passed on this exact content; the install ran.`)
    }
    const ran = await next(e)
    return notes.length ? { ...ran, context: [...(ran.context ?? []), ...notes] } : ran
  }).catch(($: any, e: any, next: any) => next(e))

  // ---- writes to gated files: size note, and the second reader -------------------------------
  for (const tool of ['Edit', 'Write'] as const) {
    on('tool.call', { tool }, async ($: any, e: any, next: any) => {
      const ran = await next(e)
      try {
        const cfg = await load($)
        if (!cfg) return ran
        const target = norm(String(e.file_path ?? ''))
        const notes: string[] = []
        for (const g of cfg.gates) {
          if (problem(g)) continue
          const f = g.files.find(x => norm(join(cfg.root, x)) === target)
          if (!f) continue
          if (g.max_lines) {
            const n = lines(String(await $.fs.read(join(cfg.root, f))))
            if (n > g.max_lines) {
              notes.push(`${NAME}: ${f} is now ${n} lines, over gate ${g.name}'s limit of ${g.max_lines}; its install will be refused until it is split.`)
            }
          }
          if (!reminded.has(g.name)) {
            reminded.add(g.name)
            notes.push(
              `${NAME}: ${f} is gated (${g.name}). Before its install: a second reader that did not write the ` +
                `change gets only the diff${g.rules ? ` and ${g.rules}` : ''}, and the install runs the suite on ` +
                'this exact content (skill icm-gates).',
            )
          }
        }
        return notes.length ? { ...ran, context: [...(ran.context ?? []), ...notes] } : ran
      } catch {
        return ran // a note that failed never disturbs a write that succeeded
      }
    }).catch(($: any, e: any, next: any) => next(e))
  }
}
