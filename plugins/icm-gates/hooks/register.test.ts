import { expect, mock, test } from 'claude-code/testing'

type World = { config?: object | null; files?: Record<string, string>; suite?: { exitCode: number; stdout?: string } | 'throws' }

/** The machine beneath the plugin: a workspace at C:/ws, its files, a store, and a suite that answers as told. */
function world(on: any, opts: World = {}) {
  const files: Record<string, string> = { ...(opts.files ?? {}) }
  if (opts.config !== null && opts.config !== undefined) files['C:/ws/icm-gates.json'] = JSON.stringify(opts.config)
  const store = new Map<string, unknown>()
  const seen = { runs: [] as string[][], installs: 0 }
  const key = (p: string) => String(p).replace(/\\/g, '/')
  mock.env(on, {})
  on('session.cwd', () => ({ value: 'C:/ws' }))
  on('fs.exists', ($: any, e: any) => ({ value: key(e.path) in files }))
  on('fs.read', ($: any, e: any) => {
    if (!(key(e.path) in files)) throw new Error('ENOENT ' + e.path)
    return { value: files[key(e.path)] }
  })
  on('store.get', ($: any, e: any) => ({ value: store.get(e.key) }))
  on('store.set', ($: any, e: any) => { store.set(e.key, e.value); return { value: undefined } })
  on('process.run', ($: any, e: any) => {
    seen.runs.push([...e.argv])
    if (opts.suite === 'throws') throw new Error('python: not found')
    const s = opts.suite ?? { exitCode: 0, stdout: 'ok' }
    return { value: { exitCode: s.exitCode, stdout: s.stdout ?? '', stderr: '' } }
  })
  on('tool.call', () => { seen.installs++; return { result: {}, text: 'done' } })
  return { files, seen }
}

const GATE = { name: 'broker', files: ['admin/broker.py'], test: ['python', 'tests/broker.py'], install: '\\binstall-broker\\.sh\\b', max_lines: 5, rules: 'admin/RULES.md' }
const CONFIG = { gates: [GATE] }
const install = { tool: 'Bash', command: 'bash guest-run.sh root install-broker.sh broker.py' } as any

test('with no icm-gates.json nothing is gated: the install runs and no suite is started', async ($, on) => {
  const { seen } = world(on, { config: null })
  const r = await $.tool.call(install)
  expect(r.deny).toBe(undefined)
  expect(seen.installs).toBe(1)
  expect(seen.runs).toEqual([])
})

test('a gated install runs the suite first, installs on a pass, and says so', async ($, on) => {
  const { seen } = world(on, { config: CONFIG, files: { 'C:/ws/admin/broker.py': 'a\nb\n' } })
  const r = await $.tool.call(install)
  expect(r.deny).toBe(undefined)
  expect(seen.runs).toEqual([['python', 'tests/broker.py']])
  expect(seen.installs).toBe(1)
  expect((r.context ?? []).join('\n')).toMatch(/suite passed on this exact content/)
})

test('the same content installs again without rerunning the suite; changed content reruns it', async ($, on) => {
  const { seen, files } = world(on, { config: CONFIG, files: { 'C:/ws/admin/broker.py': 'a\nb\n' } })
  await $.tool.call(install)
  await $.tool.call(install)
  expect(seen.runs.length).toBe(1)
  files['C:/ws/admin/broker.py'] = 'a\nc\n'
  await $.tool.call(install)
  expect(seen.runs.length).toBe(2)
  expect(seen.installs).toBe(3)
})

test('a failing suite refuses the install and shows its last lines', async ($, on) => {
  const { seen } = world(on, { config: CONFIG, files: { 'C:/ws/admin/broker.py': 'a\n' }, suite: { exitCode: 1, stdout: 'FAIL clone refused every request' } })
  const r = await $.tool.call(install)
  expect(r.deny).toMatch(/suite failed \(exit 1\)/)
  expect(r.deny).toMatch(/FAIL clone refused every request/)
  expect(r.deny).toMatch(/Fix the code, never the test/)
  expect(seen.installs).toBe(0)
})

test('a failed suite is not remembered: the next try runs it again', async ($, on) => {
  const { seen } = world(on, { config: CONFIG, files: { 'C:/ws/admin/broker.py': 'a\n' }, suite: { exitCode: 1 } })
  await $.tool.call(install)
  await $.tool.call(install)
  expect(seen.runs.length).toBe(2)
  expect(seen.installs).toBe(0)
})

test('a file over its size limit refuses the install before any suite runs', async ($, on) => {
  const { seen } = world(on, { config: CONFIG, files: { 'C:/ws/admin/broker.py': '1\n2\n3\n4\n5\n6\n' } })
  const r = await $.tool.call(install)
  expect(r.deny).toMatch(/6 lines, over gate broker's limit of 5/)
  expect(seen.runs).toEqual([])
  expect(seen.installs).toBe(0)
})

test('a suite that cannot run refuses the install (a gate fails closed)', async ($, on) => {
  const { seen } = world(on, { config: CONFIG, files: { 'C:/ws/admin/broker.py': 'a\n' }, suite: 'throws' })
  const r = await $.tool.call(install)
  expect(r.deny).toMatch(/could not run or did not finish/)
  expect(seen.installs).toBe(0)
})

test('a gated file that is missing refuses the install', async ($, on) => {
  const { seen } = world(on, { config: CONFIG, files: {} })
  const r = await $.tool.call(install)
  expect(r.deny).toMatch(/admin\/broker\.py, which cannot be read/)
  expect(seen.installs).toBe(0)
})

test('a broken gate (no test command) refuses its install and says what to fix', async ($, on) => {
  const { seen } = world(on, { config: { gates: [{ ...GATE, test: [] }] }, files: { 'C:/ws/admin/broker.py': 'a\n' } })
  const r = await $.tool.call(install)
  expect(r.deny).toMatch(/gate is broken \(gate broker has no test command/)
  expect(seen.installs).toBe(0)
})

test('ordinary commands and non-shell tools are never gated', async ($, on) => {
  const { seen } = world(on, { config: CONFIG, files: { 'C:/ws/admin/broker.py': 'a\n' } })
  await $.tool.call({ tool: 'Bash', command: 'python tests/broker.py && git status' } as any)
  await $.tool.call({ tool: 'Read', file_path: 'C:/ws/admin/broker.py' } as any)
  expect(seen.runs).toEqual([])
  expect(seen.installs).toBe(2)
})

test('a write to a gated file asks once per session for a second reader, naming the rules file', async ($, on) => {
  world(on, { config: CONFIG, files: { 'C:/ws/admin/broker.py': 'a\n' } })
  const first = await $.tool.call({ tool: 'Edit', file_path: 'C:\\ws\\admin\\broker.py', old_string: 'a', new_string: 'b' } as any)
  const again = await $.tool.call({ tool: 'Edit', file_path: 'C:/ws/admin/broker.py', old_string: 'b', new_string: 'c' } as any)
  expect((first.context ?? []).join('\n')).toMatch(/second reader that did not write the change gets only the diff and admin\/RULES\.md/)
  expect((again.context ?? []).join('\n')).not.toMatch(/second reader/)
})

test('a write that takes a gated file over its limit says so at once; other files get no note', async ($, on) => {
  world(on, { config: CONFIG, files: { 'C:/ws/admin/broker.py': '1\n2\n3\n4\n5\n6\n7\n', 'C:/ws/notes.md': 'x\n' } })
  const over = await $.tool.call({ tool: 'Write', file_path: 'C:/ws/admin/broker.py', content: 'x' } as any)
  expect((over.context ?? []).join('\n')).toMatch(/now 7 lines, over gate broker's limit of 5/)
  const other = await $.tool.call({ tool: 'Write', file_path: 'C:/ws/notes.md', content: 'x' } as any)
  expect(other.context).toBe(undefined)
})
