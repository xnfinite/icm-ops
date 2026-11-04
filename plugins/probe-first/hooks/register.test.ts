import { expect, mock, test } from 'claude-code/testing'

let n = 0

/** Records the session's rows; call before the test's first call on `$`. */
function world(on: any) {
  return mock.session(on)
}

/** The model's reply arriving as a response row; the nudges probe-first appended so far. */
async function reply($: any, session: ReturnType<typeof world>, text: string): Promise<string[]> {
  await $.session.append({
    message: { type: 'assistant', content: [{ type: 'text', text }] },
    door: 'response',
    origin: { kind: 'model' },
    uuid: `00000000-0000-4000-8000-${String(++n).padStart(12, '0')}`,
  } as any)
  return session
    .appended()
    .filter(r => r.door === 'note')
    .map(r => (r.message.content as any[]).map(b => b.text).join(''))
}

test('an unhedged absolute with nothing run this turn gets one nudge naming the phrase', async ($, on) => {
  const notes = await reply($, world(on), 'I looked at the folder layout and there are no preview clips left to render here.')
  expect(notes.length).toBe(1)
  expect(notes[0]).toMatch(/you wrote "there are no"/)
})

test('a hedged sentence passes', async ($, on) => {
  const notes = await reply($, world(on), 'I think there are no preview clips left to render here, but I have not looked yet.')
  expect(notes).toEqual([])
})

test('a hedge in another sentence does not excuse an unhedged absolute', async ($, on) => {
  const notes = await reply(
    $,
    world(on),
    'There are no preview clips left to render here. You may want to archive the folder afterwards.',
  )
  expect(notes.length).toBe(1)
  expect(notes[0]).toMatch(/you wrote "There are no"/)
})

test('a sentence carries on past "i.e." and "e.g.", so its hedge still covers it', async ($, on) => {
  const notes = await reply(
    $,
    world(on),
    'The cache may be stale here, i.e. there is no fresh copy on disk yet, e.g. after a rebuild.',
  )
  expect(notes).toEqual([])
})

test('an absolute after a tool call that turn passes', async ($, on) => {
  const session = world(on)
  on('tool.call', () => ({ result: {}, text: '0 files' }))
  await $.tool.call({ tool: 'Bash', command: 'ls clips | wc -l' } as any)
  const notes = await reply($, session, 'I counted the folder just now and there are no preview clips left to render.')
  expect(notes).toEqual([])
})
