/**
 * probe-first — the ledger's commonest finding, enforced instead of read.
 *
 * `icm-ledger` scores an agent's advice and a readout turns the record into a
 * briefing the next session reads on arrival. Across the ledgers this pack has seen,
 * one failure dominates the working sessions: a NUMERAL OR AN ABSOLUTE put on a
 * shipping surface without the one-step-away check. Count or probe first, then write
 * the sentence.
 *
 * A briefing is read at the start and skipped under momentum. One session, in the
 * same hour it had re-read its own briefing, wrote "only three preview clips exist"
 * (there were fifty), "it is not the files" after checking one of five, and treated
 * an empty accessibility tree as proof an application had wedged. Advice a session
 * can skim past is not a control.
 *
 * WHY THIS IS NOT "IS THAT TRUE".
 * The same briefings warn that self-consistent systems only prove their pipes. A
 * model grading its own claim over its own transcript inherits the context that
 * produced the claim, so it cannot sort a wrong absolute from a right one. It can
 * answer a mechanical question: did this turn run anything able to check that? So
 * the test is PROCEDURAL — an absolute asserted with no tool call behind it — which
 * is the step the ledgers say gets skipped.
 *
 * It speaks to the AGENT, via `$.session.append`: a row the person never sees as
 * typed and the model reads. The person is not the one asserting things.
 *
 * It never blocks and never rewrites what was said. One nudge per turn at most, and
 * a hedged sentence is already honest, so it passes.
 */
import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

/** The shapes the scored failures actually took: a universal, a non-existence, an impossibility. */
const ABSOLUTE =
  /\b(?:only (?:one|two|three|four|five|\d+)|there (?:is|are) no\b|does not exist|do not exist|doesn't exist|don't exist|nothing (?:in|on|here|there)\b|never\b|always\b|every single\b|all (?:of them|five|four|three)\b|cannot be\b|can't be\b|impossible\b|none of\b|no (?:way|such)\b)/i

/** A hedge means the claim is already marked unverified, which is the behaviour wanted. */
const HEDGED =
  /\b(?:probably|might|may|seems|appears|i think|unverified|untested|not sure|believe|likely|assume|guess)\b/i

/** Tools that could have checked something about this machine, project or the world. */
const VERIFYING = /^(Bash|PowerShell|Read|Grep|Glob|WebFetch|WebSearch|NotebookRead)$|^mcp__/

const turn = atom({ plugin: 'probe-first', key: 'turn' } as const, { tools: [], flagged: false })

export const register: Register = on => {
  on('prompt.submit', async ($, e, next) => {
    await update($, turn, () => ({ tools: [], flagged: false }))
    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    const name = String((e as any).tool ?? '')
    if (VERIFYING.test(name)) await update($, turn, t => ({ ...t, tools: [...t.tools, name] }))
    return next(e)
  })

  on('session.append', { door: 'response' }, async ($, e, next) => {
    const stored = await next(e)
    try {
      const state = await read($, turn)
      if (state.flagged || state.tools.length > 0) return stored

      const blocks = (e.message as any).content
      if (!Array.isArray(blocks)) return stored
      const text = blocks
        .filter((b: any) => b && b.type === 'text' && typeof b.text === 'string')
        .map((b: any) => b.text)
        .join('\n')
      if (text.length < 40) return stored

      const hit = ABSOLUTE.exec(text)
      if (!hit || HEDGED.test(text)) return stored

      await update($, turn, t => ({ ...t, flagged: true }))
      await $.session.append({
        message: {
          type: 'user',
          content: [
            {
              type: 'text',
              text:
                `probe-first (automatic): you wrote "${hit[0]}" and this turn has run ` +
                'no tool that could check it. This is the failure the ledger scores most ' +
                'often in working sessions: an absolute on a shipping surface, asserted ' +
                'without the one-step-away check.\n' +
                'It is a procedural flag, not a claim that you are wrong — it cannot know. ' +
                'Before the next message, run the one command that would settle it, or ' +
                'hedge the sentence to what you actually checked. If you verified it in an ' +
                'earlier turn, say which: the reader cannot see that either.',
            },
          ],
        },
      })
    } catch {
      // A guard that errors must never disturb the conversation it watches.
    }
    return stored
  })
}
