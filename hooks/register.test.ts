import { expect, test } from 'claude-code/testing'

const CHECKER = '/skills/icm-maintain/scripts/icm_check.py'

/**
 * A workspace at /ws as the plugin route leaves it: it holds 00-catalog/ and no copy of the
 * checker, which lives in the plugin's own folder. `write` sets the FAILs the checker reports
 * once the write has landed.
 */
function world(on: any, fails: { before: string[]; after: string[] }) {
  let current = fails.before
  const runs: string[][] = []
  on('fs.exists', ($: any, e: any) => {
    const p = String(e.path).replace(/\\/g, '/')
    return { value: p === '/ws/00-catalog' || (p.endsWith(CHECKER) && !p.startsWith('/ws/')) }
  })
  on('process.run', ($: any, e: any) => {
    runs.push([...e.argv])
    if (e.argv[1] === '--version') return { value: { exitCode: 0, stdout: 'Python 3.12.0', stderr: '' } }
    const out = { version: '0.3.0', today: '2026-09-08', fail: current, warn: [], info: [] }
    return { value: { exitCode: current.length ? 1 : 0, stdout: JSON.stringify(out), stderr: '' } }
  })
  on('ui.status', () => ({ value: undefined }))
  on('tool.call', () => {
    current = fails.after
    return { result: {}, text: 'written' }
  })
  return { runs }
}

const write = (path: string) => ({ tool: 'Write', file_path: path, content: 'x' }) as any
const note = (r: any) => (r.context ?? []).join('\n')

test('with the checker in the plugin, not the workspace, a write that adds a FAIL is reported', async ($, on) => {
  const { runs } = world(on, { before: [], after: ['broken relative link in 02-processes/new.md: (missing.md)'] })
  const r = await $.tool.call(write('/ws/02-processes/new.md'))
  expect(note(r)).toMatch(/this write FAILS the workspace checker\.\n- broken relative link in 02-processes\/new\.md/)
  const checks = runs.filter(a => a[1] !== '--version')
  expect(checks.length).toBeGreaterThan(0)
  for (const a of checks) {
    expect(String(a[1]).endsWith(CHECKER)).toBe(true)
    expect(String(a[1]).startsWith('/ws/')).toBe(false)
  }
})

test('the "Full detail" hint names the interpreter and checker that ran', async ($, on) => {
  const { runs } = world(on, { before: [], after: ['x.md: 300 lines — OVER its binding budget of 250.'] })
  const r = await $.tool.call(write('/ws/x.md'))
  const ran = runs.filter(a => a[1] !== '--version').pop() as string[]
  expect(note(r)).toContain(`Full detail: ${ran[0]} ${ran[1]} /ws`)
})

test("a session's first write is not blamed for the FAILs the workspace already had", async ($, on) => {
  const old = 'BRIEFING.md (readout: 2026-08-01) is OLDER than the newest ledger readout (2026-09-08)'
  world(on, { before: [old], after: [old] })
  const r = await $.tool.call(write('/ws/04-memory/STATE.md'))
  expect(note(r)).toBe('')
})

test('a first write that adds a FAIL to a backlog is told only about the one it added', async ($, on) => {
  const old = 'BRIEFING.md (readout: 2026-08-01) is OLDER than the newest ledger readout (2026-09-08)'
  const added = 'broken relative link in 04-memory/STATE.md: (gone.md)'
  world(on, { before: [old], after: [old, added] })
  const r = await $.tool.call(write('/ws/04-memory/STATE.md'))
  expect(note(r)).toContain('- ' + added)
  expect(note(r)).not.toContain(old)
})

test('a write outside any workspace runs no checker', async ($, on) => {
  const { runs } = world(on, { before: [], after: ['anything'] })
  const r = await $.tool.call(write('/elsewhere/notes.md'))
  expect(note(r)).toBe('')
  expect(runs.filter(a => a[1] !== '--version')).toEqual([])
})
