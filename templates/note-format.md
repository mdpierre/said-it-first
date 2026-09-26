# Note format

What a note produced by this pipeline looks like, and what is allowed in.

## The admission test

**The idea must be yours. The sentence does not have to be.**

A note may be drafted by a model when it renders thinking you actually did:
something you reasoned through, argued, or arrived at in the conversation.
What stays out is an idea the assistant supplied that you never wrestled with,
even if you said "yes, exactly" to it.

Handwriting every note is too slow to ever finish. A note that is 80% right and
exists beats a perfect one that never gets written, *as long as provenance is
honest*.

## Provenance

- Quotation marks mean **verbatim from your own turn**, typos kept. Nothing
  else goes inside them.
- Paraphrase goes without quotation marks.
- `source` in frontmatter describes the note as a whole: `chatgpt-synthesis`
  when any of its prose is model-drafted (nearly every archive-derived note),
  `chatgpt-archive` only when every sentence is your own wording. Line-level
  provenance is carried by the quotation marks and the labels below.
- Labels, which `synth verify` recognizes **only in bold** when they sit on
  the quote's line, up to three lines before it, or on the line after:
  - `**assistant-coined, echoed**`: the assistant said it first and you
    repeated it. Kept for the record; never presented as your idea.
  - `**cleaned**`: dictation artifacts fixed. Put the raw wording alongside.
  - `**paraphrase**`: reworded, with your actual wording alongside.
  - `**pasted**` / `**chip**`: text from someone else or a clicked
    suggestion, quoted only to show what you were responding to.
  - `**unverifiable**`: the assistant turn that would show who said it first
    is missing or cut off in the export. Verify cannot detect this case; you
    must add the label yourself.
- `synth verify` checks quotes of 40+ characters only. Check shorter quotes
  against the transcript by hand.
- The **profile is never a source**. Its wording is today's description of
  you; every "was" must be found in the archive, in your words, or reported
  as unsupported.
- Every note cites the conversations it came from:
  `*Sources:* [[2024-03-02-rethinking-the-founder-plan]]`
- **Dates.** Transcripts carry the date a conversation started. For a turn
  in a multi-day conversation, use `create_time` and `span_hours` from
  `index.json`, or write "conversation started <date>".
- **Out-of-scope details** (per the profile) that are part of a cause you
  state: record the cause in general terms ("a view absorbed growing up")
  and flag the specific for the owner. Never drop a cause silently.

## One note per idea, permanently

Never fork a note into dated copies (`ambition (2024)`, `ambition (2026)`).
Forking splits the link graph and every inbound link has to pick a version.
Instead: **current position on top, history below, newest first.**

## Record deltas, not snapshots

"In 2024 I thought X" is filler. The value is in the *transitions*: what moved,
and what moved it.

```yaml
---
position-since: 2024-03
stability: core | working | provisional
supersedes: 2023-11            # or before-2024-03 / unknown when the "was" has no start date
source: chatgpt-synthesis      # chatgpt-archive only if every sentence is yours
---
```

```markdown
# <the idea>

## Current position (2024-03)

<what you think now, in 2 to 6 sentences>

> "<a verbatim line that carries it>"
> [[2024-03-10-...]]

---

## How this changed

### 2023-11 -> 2024-03
**Was:** the position as actually held, not as you'd describe it today
**Now:** what replaced it
**Because:** what moved it, with the dated source

*Sources:* [[...]], [[...]]
```

## When the archive disagrees with the profile

If the newest evidence in the archive contradicts the current position the
profile gives (a relapse, a reversal), do not rewrite the current position
from the archive, and do not bury the contradiction in the history. Add:

```markdown
## Open: archive vs profile

The profile says <X> since <date>. On <date> the archive shows <Y>:
> "<verbatim>" [[...]]
The archive ends <export date>. Owner to confirm which is current.
```

The archive is a trailing indicator; only the owner can settle this.

## Stability

- `core`: held a long time, survived a challenge
- `working`: current, not yet tested
- `provisional`: recovered from the archive and not yet confirmed by you, or
  an abandoned position recorded for the history. **Never load provisional
  notes into an AI's picture of who you are now.**

## Two destinations, opposite rules

The same old conversation serves two goals that want opposite things from it:

| | Record of your thinking | AI context about you now |
|---|---|---|
| Old, abandoned positions | high value (the "was" half) | must be excluded |
| Volume | helps | hurts |

Do not let the second instinct filter the first.
