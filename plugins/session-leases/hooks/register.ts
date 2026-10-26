/**
 * session-leases: two agent sessions on one machine never use a shared resource at once.
 *
 * Several sessions can run on one machine. Without a gate, collisions are accidents of timing that
 * neither session can see coming: two builds in an editor that takes one client, two pushes of the
 * same branch, one session changing the scheduled tasks another depends on. lease.py (shipped
 * beside this file, and in skills/icm-maintain/scripts/) holds the lease; this mod makes it the
 * gate at the moment of the action, so it does not depend on an agent remembering a paragraph.
 *
 * Before a tool call that touches a shared resource, it claims the resource for this session:
 * - free, or already this session's: the call runs, and a "hold" lease keeps renewing while the
 *   session keeps using the resource;
 * - held by another session: the call is refused, and the refusal names the holder and its reason,
 *   so the agent can message that session or do something else.
 * A "call" resource (a git push, a scheduled-task change) is released when the call returns; a
 * "hold" resource (the desktop, an editor) stays leased until the session leaves it idle for the
 * rule's minutes, or releases it with lease.py.
 *
 * Rules: three defaults below, plus any in <lease dir>/config.json, which can also name the python
 * and the lease tool to use. A config rule with a default's resource name replaces that default.
 *
 * It fails open. If the lease tool cannot run, the call goes ahead with one note to the agent per
 * session: a broken coordinator must not stop work that a working one would allow.
 */
import type { Register } from 'claude-code'

const NAME = 'session-leases'

type Rule = { resource: string; tool?: string; command?: string; mode?: 'hold' | 'call'; minutes?: number }
type Config = { python?: string; lease_tool?: string; rules?: Rule[] }
type Live = { rules: Array<{ rule: Rule; toolRe: RegExp; cmdRe: RegExp | null }>; python: string[] | null; tool: string }

const SHELLS = '^(Bash|PowerShell)$'

/** Resources every machine has. More come from <lease dir>/config.json. */
const DEFAULT_RULES: Rule[] = [
  {
    resource: 'git-{repo}',
    command: '(?:^|[;&|(]\\s*)git(?:\\.exe)?(?:\\s+-C\\s+(?:"[^"]*"|\'[^\']*\'|\\S+)|\\s+-c\\s+\\S+)*\\s+push\\b',
    mode: 'call',
    minutes: 30,
  },
  {
    resource: 'scheduled-tasks',
    command:
      '\\b(?:Register|Set|Unregister|Enable|Disable)-ScheduledTask\\b|\\bschtasks(?:\\.exe)?\\s+/(?:create|change|delete)\\b|\\bcrontab\\s+(?!-l\\b)\\S',
    mode: 'call',
    minutes: 10,
  },
  { resource: 'desktop', tool: '^mcp__(?:computer-use__|remote-devices__computer)', mode: 'hold', minutes: 15 },
]

const RESOURCE = /^[a-z0-9][a-z0-9-]{0,47}$/

let live: Live | null = null
const claimedAt = new Map<string, number>() // resource -> when this session last claimed it (ms)
let notedFailure = false

async function safe(value: Promise<string | undefined>): Promise<string> {
  try {
    return (await value) || ''
  } catch {
    return ''
  }
}

/** The folder lease.py uses, worked out the same way: ICM_LEASE_DIR, else the per-user state folder. */
async function leaseDir($: any): Promise<string> {
  const explicit = await safe($.env.get('ICM_LEASE_DIR'))
  if (explicit) return explicit
  const local = await safe($.env.get('LOCALAPPDATA'))
  if (local) return `${local}/icm-leases`
  const state = (await safe($.env.get('XDG_STATE_HOME'))) || `${await safe($.env.get('HOME'))}/.local/state`
  return `${state}/icm-leases`
}

async function load($: any): Promise<Live> {
  if (live) return live
  const dir = await leaseDir($)
  let user: Config = {}
  try {
    const p = `${dir}/config.json`
    if (await $.fs.exists(p)) user = JSON.parse(await $.fs.read(p)) as Config
  } catch {
    user = {}
  }
  const extra = Array.isArray(user.rules) ? user.rules : []
  const names = new Set(extra.map(r => r.resource))
  const rules = [...DEFAULT_RULES.filter(r => !names.has(r.resource)), ...extra].flatMap(rule => {
    try {
      const toolRe = new RegExp(rule.tool ?? (rule.command ? SHELLS : '$^'))
      const cmdRe = rule.command ? new RegExp(rule.command, 'i') : null
      return [{ rule, toolRe, cmdRe }]
    } catch {
      return [] // a rule whose pattern does not compile is skipped, not fatal
    }
  })
  let python: string[] | null = user.python ? [user.python] : null
  if (!python) {
    for (const candidate of ['python3', 'python', 'py']) {
      try {
        const r = await $.process.run([candidate, '-c', 'print(1)'], { timeoutMs: 10000 })
        if (r.exitCode === 0 && r.stdout.trim() === '1') {
          python = [candidate]
          break
        }
      } catch {
        // not on PATH; try the next
      }
    }
  }
  live = { rules, python, tool: user.lease_tool || `${$.plugin.root}/lease.py` }
  return live
}

function repoName(cmd: string, cwd: string): string {
  const m = /\bgit(?:\.exe)?\s+-C\s+(?:"([^"]*)"|'([^']*)'|(\S+))/.exec(cmd)
  const path = m ? (m[1] ?? m[2] ?? m[3] ?? '') : cwd
  const base = path.replace(/[\\/]+$/, '').split(/[\\/]/).pop() || 'repo'
  return base.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'repo'
}

async function lease($: any, l: Live, args: string[]) {
  return $.process.run([...(l.python ?? []), l.tool, ...args], { timeoutMs: 15000 })
}

export const register: Register = on => {
  on('tool.call', async ($: any, e: any, next: any) => {
    const tool = String(e.tool ?? '')
    const cmd = typeof e.command === 'string' ? e.command : ''
    const l = await load($)
    const hits = l.rules.filter(h => h.toolRe.test(tool) && (!h.cmdRe || h.cmdRe.test(cmd)))
    if (hits.length === 0) return next(e)

    const sid = String(await $.session.id())
    const why = ('auto: ' + tool + (cmd ? ' ' + cmd : '')).replace(/\s+/g, ' ').slice(0, 100)
    const toRelease: string[] = []
    for (const { rule } of hits) {
      const resource = rule.resource.includes('{repo}')
        ? rule.resource.replace('{repo}', repoName(cmd, String(await $.session.cwd())))
        : rule.resource
      if (!RESOURCE.test(resource)) continue
      const minutes = Math.max(1, Math.min(720, rule.minutes ?? 15))
      const recent = claimedAt.get(resource)
      if (rule.mode !== 'call' && recent !== undefined && Date.now() - recent < Math.min(60000, minutes * 20000)) continue

      let r: any = null
      if (l.python) {
        try {
          r = await lease($, l, ['take', resource, '--session', sid, '--why', why, '--minutes', String(minutes)])
        } catch {
          r = null
        }
      }
      const out = r ? String(r.stdout ?? '').trim() : ''
      if (r && r.exitCode === 1 && /^HELD:/m.test(out)) {
        return {
          deny:
            `${NAME}: ${resource} is in use by another session on this machine, so this call was not run.\n` +
            out +
            '\nAsk that session (your session listing shows which one is busy; message it by name), or do ' +
            'something else first. Do not work around the lease: it frees when the holder releases it, or at ' +
            'the time shown.',
        }
      }
      if (!r || r.exitCode !== 0) {
        if (!notedFailure) {
          notedFailure = true
          const reason = !l.python ? 'no python found' : r ? `lease tool exit ${r.exitCode}` : 'the lease tool did not run'
          const ran = await next(e)
          return {
            ...ran,
            context: [
              ...(ran.context ?? []),
              `${NAME}: could not check the lease for ${resource} (${reason}); this call ran without one. ` +
                'Further calls this session skip the note.',
            ],
          }
        }
        continue
      }
      claimedAt.set(resource, Date.now())
      if (rule.mode === 'call' && /^took\b/.test(out)) toRelease.push(resource)
    }

    const ran = await next(e)
    for (const resource of toRelease) {
      claimedAt.delete(resource)
      try {
        await lease($, l, ['release', resource, '--session', sid])
      } catch {
        // the lease expires on its own
      }
    }
    return ran
  }).catch(($: any, e: any, next: any) => next(e)) // fail open: coordination, not a wall
}
