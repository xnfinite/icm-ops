import { expect, mock, test } from 'claude-code/testing'

type World = { take?: { exitCode: number; stdout: string }; config?: object; python?: boolean; opened?: string[] }

/** The machine beneath the plugin: one session, a lease tool that answers as told, an optional config. */
function world(on: any, opts: World = {}): string[][] {
  const calls: string[][] = []
  mock.env(on, { USERPROFILE: 'C:/Users/u', LOCALAPPDATA: 'C:/Users/u/AppData/Local' })
  on('session.id', () => ({ value: 'sess-aaaaaaaa' }))
  on('session.cwd', () => ({ value: 'C:/work/icm-ops' }))
  on('fs.exists', ($: any, e: any) => { opts.opened?.push(String(e.path)); return { value: opts.config !== undefined } })
  on('fs.read', ($: any, e: any) => { opts.opened?.push(String(e.path)); return { value: JSON.stringify(opts.config ?? {}) } })
  on('process.run', ($: any, e: any) => {
    const argv = [...e.argv] as string[]
    calls.push(argv)
    if (argv[1] === '-c') return { value: { exitCode: opts.python === false ? 1 : 0, stdout: '1\n', stderr: '' } }
    if (argv.includes('take')) {
      return { value: { stderr: '', ...(opts.take ?? { exitCode: 0, stdout: 'took it until 2026-10-26 12:00\n' }) } }
    }
    return { value: { exitCode: 0, stdout: 'released it\n', stderr: '' } }
  })
  return calls
}

const takes = (calls: string[][]) => calls.filter(c => c.includes('take'))

test('a git push takes the repo lease for this session, runs, then releases it', async ($, on) => {
  const calls = world(on)
  let ran = false
  on('tool.call', () => { ran = true; return { result: {}, text: 'pushed' } })
  const r = await $.tool.call({ tool: 'PowerShell', command: 'git -C "C:\\Users\\u\\dev\\icm-ops" push origin main' } as any)
  expect(r.deny).toBe(undefined)
  expect(ran).toBe(true)
  const take = takes(calls)[0]
  expect(take).toContain('git-icm-ops')
  expect(take).toContain('sess-aaaaaaaa')
  expect(calls.some(c => c.includes('release') && c.includes('git-icm-ops'))).toBe(true)
})

test('a push is refused while another session holds the repo, and the refusal names the holder', async ($, on) => {
  world(on, {
    take: {
      exitCode: 1,
      stdout: 'HELD: git-icm-ops: Docs [5cb01d], since 2026-10-26 11:00, for "push the release", until 2026-10-26 11:30\n',
    },
  })
  let ran = false
  on('tool.call', () => { ran = true; return { result: {}, text: 'pushed' } })
  const r = await $.tool.call({ tool: 'Bash', command: 'cd /c/work/icm-ops && git push' } as any)
  expect(r.deny).toMatch(/in use by another session/)
  expect(r.deny).toMatch(/Docs \[5cb01d\]/)
  expect(ran).toBe(false)
})

test('a lease the session already held is renewed, not released, after the push', async ($, on) => {
  const calls = world(on, { take: { exitCode: 0, stdout: 'renewed git-icm-ops until 2026-10-26 13:00\n' } })
  on('tool.call', () => ({ result: {}, text: 'pushed' }))
  await $.tool.call({ tool: 'Bash', command: 'git push' } as any)
  expect(takes(calls).length).toBe(1)
  expect(calls.some(c => c.includes('release'))).toBe(false)
})

test('ordinary calls never touch the lease tool', async ($, on) => {
  const calls = world(on)
  on('tool.call', () => ({ result: {}, text: 'ok' }))
  await $.tool.call({ tool: 'Bash', command: 'git status && git log -1' } as any)
  await $.tool.call({ tool: 'Read', file_path: 'C:/work/README.md' } as any)
  await $.tool.call({ tool: 'Bash', command: 'git commit -m "push it later"' } as any)
  expect(takes(calls)).toEqual([])
})

test('a held resource is claimed once for a burst of actions and kept', async ($, on) => {
  const calls = world(on)
  on('tool.call', () => ({ result: {}, text: 'ok' }))
  for (let i = 0; i < 3; i++) await $.tool.call({ tool: 'mcp__computer-use__left_click', coordinate: [1, 2] } as any)
  expect(takes(calls).length).toBe(1)
  expect(takes(calls)[0]).toContain('desktop')
  expect(calls.some(c => c.includes('release'))).toBe(false)
})

test('a scheduled-task change takes the scheduled-tasks lease', async ($, on) => {
  const calls = world(on)
  on('tool.call', () => ({ result: {}, text: 'ok' }))
  await $.tool.call({ tool: 'PowerShell', command: 'Set-ScheduledTask -TaskName X -Action $a' } as any)
  expect(takes(calls)[0]).toContain('scheduled-tasks')
})

test('a config rule adds a resource of its own', async ($, on) => {
  const calls = world(on, { config: { rules: [{ resource: 'editor', command: '\\bbuild-editor\\b', mode: 'hold', minutes: 45 }] } })
  on('tool.call', () => ({ result: {}, text: 'ok' }))
  await $.tool.call({ tool: 'Bash', command: 'build-editor --project 80' } as any)
  const take = takes(calls)[0]
  expect(take).toContain('editor')
  expect(take).toContain('45')
})

test('the machine rules come from <profile>/.icm-leases, never from AppData', async ($, on) => {
  const opened: string[] = []
  const calls = world(on, { opened, config: { rules: [{ resource: 'editor', command: '\\bbuild-editor\\b', mode: 'hold', minutes: 45 }] } })
  on('tool.call', () => ({ result: {}, text: 'ok' }))
  await $.tool.call({ tool: 'Bash', command: 'build-editor --project 80' } as any)
  expect(opened.map(p => p.replace(/\\/g, '/'))).toContain('C:/Users/u/.icm-leases/config.json')
  expect(opened.some(p => /AppData/i.test(p))).toBe(false)
  expect(takes(calls)[0]).toContain('editor')
})

/** A workspace whose ledger folder holds `files`; counts the folder reads and the writes that ran. */
function ledgerWorld(on: any, files: Record<string, string>) {
  const seen = { lists: 0, writes: 0 }
  mock.env(on, { USERPROFILE: 'C:/Users/u', LOCALAPPDATA: 'C:/Users/u/AppData/Local' })
  on('session.id', () => ({ value: 'sess-aaaaaaaa' }))
  on('session.cwd', () => ({ value: 'C:/ws' }))
  on('fs.exists', () => ({ value: false }))
  on('fs.list', () => {
    seen.lists++
    return { value: Object.keys(files).map(name => ({ name, kind: 'file', size: 1, mtimeMs: 0, isLink: false })) }
  })
  on('fs.read', ($: any, e: any) => ({ value: files[String(e.path).split(/[\\/]/).pop() ?? ''] ?? '' }))
  on('process.run', () => ({ value: { exitCode: 0, stdout: '1\n', stderr: '' } }))
  on('tool.call', () => { seen.writes++; return { result: {}, text: 'edited' } })
  return seen
}

const LEDGER = {
  '2026-09.md': '## L-090 - 2026-09-30 - builder\nCLAIM: a\nOUTCOME: open\n',
  '2026-10.md': '## L-106 - 2026-10-26 - builder\nCLAIM: b\nOUTCOME: open\n\n## L-107 - 2026-10-26 - builder\nCLAIM: c\nOUTCOME: open\n',
}
const MONTH = 'C:/ws/04-memory/ledger/2026-10.md'

test('a second L-107 is refused at the write, and the refusal names the next free id', async ($, on) => {
  const seen = ledgerWorld(on, LEDGER)
  const r = await $.tool.call({ tool: 'Edit', file_path: MONTH, old_string: 'CLAIM: b\nOUTCOME: open\n',
    new_string: 'CLAIM: b\nOUTCOME: open\n\n## L-107 - 2026-10-26 - builder\nCLAIM: mine\n' } as any)
  expect(r.deny).toMatch(/L-107 is already taken in 2026-10\.md/)
  expect(r.deny).toMatch(/next free id is L-108/)
  expect(seen.writes).toBe(0)
})

test('the next free id passes, and evidence added under an existing heading passes', async ($, on) => {
  const seen = ledgerWorld(on, LEDGER)
  const fresh = await $.tool.call({ tool: 'Edit', file_path: MONTH, old_string: 'CLAIM: c\nOUTCOME: open\n',
    new_string: 'CLAIM: c\nOUTCOME: open\n\n## L-108 - 2026-10-26 - builder\nCLAIM: mine\n' } as any)
  expect(fresh.deny).toBe(undefined)
  const evidence = await $.tool.call({ tool: 'Edit', file_path: MONTH, old_string: '## L-106 - 2026-10-26 - builder\nCLAIM: b\n',
    new_string: '## L-106 - 2026-10-26 - builder\nCLAIM: b\nEVIDENCE: it held\n' } as any)
  expect(evidence.deny).toBe(undefined)
  expect(seen.writes).toBe(2)
})

test('files outside a ledger folder are not read for ids', async ($, on) => {
  const seen = ledgerWorld(on, LEDGER)
  const r = await $.tool.call({ tool: 'Edit', file_path: 'C:/ws/04-memory/log/2026-10-26.md', old_string: 'a',
    new_string: 'a\n## L-107 notes\n' } as any)
  expect(r.deny).toBe(undefined)
  expect(seen.lists).toBe(0)
})

test('it fails open: without python the call runs, with one note per session', async ($, on) => {
  world(on, { python: false })
  let ran = 0
  on('tool.call', () => { ran++; return { result: {}, text: 'ok' } })
  const a = await $.tool.call({ tool: 'Bash', command: 'git push' } as any)
  expect(ran).toBe(1)
  expect((a.context ?? []).join('\n')).toMatch(/could not check the lease/)
  const b = await $.tool.call({ tool: 'Bash', command: 'git push' } as any)
  expect(ran).toBe(2)
  expect(b.context).toBe(undefined)
})
