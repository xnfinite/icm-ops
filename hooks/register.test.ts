import { expect, test } from 'claude-code/testing'

const CHECKER = '/skills/icm-maintain/scripts/icm_check.py'

type World = {
  before: string[] // FAILs the checker reports before the write lands
  after: string[] // FAILs it reports once the write has landed
  root?: string // the workspace, '/ws' unless given
  catalogBeforeWrite?: boolean // false: the write itself creates 00-catalog/
  checkerExit?: number // 2: the checker gives no result (a config error, say)
}

/**
 * A workspace as the plugin route leaves it: it holds 00-catalog/ and no copy of the checker,
 * which lives in the plugin's own folder. Paths are compared without a drive letter, should the
 * test harness add one on Windows.
 */
function world(on: any, w: World) {
  const root = w.root ?? '/ws'
  let written = false
  const runs: string[][] = []
  const key = (p: unknown) => String(p).replace(/\\/g, '/').replace(/^[A-Za-z]:/, '')
  on('fs.exists', ($: any, e: any) => {
    const p = key(e.path)
    if (p === `${root}/00-catalog`) return { value: written || w.catalogBeforeWrite !== false }
    return { value: p.endsWith(CHECKER) && !p.startsWith(root + '/') }
  })
  on('process.run', ($: any, e: any) => {
    runs.push([...e.argv])
    if (e.argv[1] === '--version') return { value: { exitCode: 0, stdout: 'Python 3.12.0', stderr: '' } }
    if (w.checkerExit === 2) return { value: { exitCode: 2, stdout: '', stderr: 'icm_check: catalog not found' } }
    const fail = written ? w.after : w.before
    const out = { version: '0.3.0', today: '2026-09-08', fail, warn: [], info: [] }
    return { value: { exitCode: fail.length ? 1 : 0, stdout: JSON.stringify(out), stderr: '' } }
  })
  on('ui.status', () => ({ value: undefined }))
  on('tool.call', () => {
    written = true
    return { result: {}, text: 'written' }
  })
  const checks = () => runs.filter(a => a[1] !== '--version')
  return { checks }
}

const write = (path: string) => ({ tool: 'Write', file_path: path, content: 'x' }) as any
const note = (r: any) => (r.context ?? []).join('\n')
const OLD = 'BRIEFING.md (readout: 2026-08-01) is OLDER than the newest ledger readout (2026-09-08)'

test('with the checker in the plugin, not the workspace, a write that adds a FAIL is reported', async ($, on) => {
  const { checks } = world(on, { before: [], after: ['broken relative link in 02-processes/new.md: (missing.md)'] })
  const r = await $.tool.call(write('/ws/02-processes/new.md'))
  expect(note(r)).toMatch(/this write FAILS the workspace checker\.\n- broken relative link in 02-processes\/new\.md/)
  expect(checks().length).toBeGreaterThan(0)
  for (const a of checks()) {
    expect(String(a[1]).endsWith(CHECKER)).toBe(true)
    expect(String(a[1]).startsWith('/ws/')).toBe(false)
  }
})

test('the "Full detail" hint names the interpreter and checker that ran', async ($, on) => {
  const { checks } = world(on, { before: [], after: ['x.md: 300 lines — OVER its binding budget of 250.'] })
  const r = await $.tool.call(write('/ws/x.md'))
  const ran = checks().pop() as string[]
  expect(note(r)).toContain(`Full detail: ${ran[0]} ${ran[1]} /ws`)
})

test('the "Full detail" hint quotes a path that holds a space', async ($, on) => {
  world(on, { root: '/my ws', before: [], after: ['x.md: 300 lines — OVER its binding budget of 250.'] })
  const r = await $.tool.call(write('/my ws/x.md'))
  expect(note(r)).toMatch(/ "\/my ws"$/)
})

test("a session's first write is not blamed for the FAILs the workspace already had", async ($, on) => {
  world(on, { before: [OLD], after: [OLD] })
  const r = await $.tool.call(write('/ws/04-memory/STATE.md'))
  expect(note(r)).toBe('')
})

test('a first write that adds a FAIL to a backlog is told only about the one it added', async ($, on) => {
  const added = 'broken relative link in 04-memory/STATE.md: (gone.md)'
  world(on, { before: [OLD], after: [OLD, added] })
  const r = await $.tool.call(write('/ws/04-memory/STATE.md'))
  expect(note(r)).toContain('- ' + added)
  expect(note(r)).not.toContain(OLD)
})

test('the baseline runs once per workspace: two writes cost one baseline and one check each', async ($, on) => {
  const { checks } = world(on, { before: [], after: [] })
  await $.tool.call(write('/ws/a.md'))
  await $.tool.call(write('/ws/b.md'))
  expect(checks().length).toBe(3)
})

test('a checker that gives no result is not retried as a baseline before every write', async ($, on) => {
  const { checks } = world(on, { before: [], after: [], checkerExit: 2 })
  const first = await $.tool.call(write('/ws/a.md'))
  await $.tool.call(write('/ws/b.md'))
  expect(note(first)).toBe('')
  expect(checks().length).toBe(3)
})

test('the write that creates 00-catalog/ is checked, and its FAILs are not absorbed later', async ($, on) => {
  const link = 'broken relative link in 00-catalog/CATALOG.md: (x.md)'
  world(on, { before: [], after: [link], catalogBeforeWrite: false })
  const first = await $.tool.call(write('/ws/00-catalog/CATALOG.md'))
  expect(note(first)).toContain('- ' + link)
})

test('a write outside any workspace runs no checker', async ($, on) => {
  const { checks } = world(on, { before: [], after: ['anything'], catalogBeforeWrite: false, root: '/elsewhere-ws' })
  const r = await $.tool.call(write('/elsewhere/notes.md'))
  expect(note(r)).toBe('')
  expect(checks()).toEqual([])
})
