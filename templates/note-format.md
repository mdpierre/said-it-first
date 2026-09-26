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

- Quote verbatim, in quotation marks, only when the wording is yours. Keep
  your typos.
- Paraphrase without quotation marks. If a note is mostly model-worded, set
  `source: chatgpt-synthesis` in frontmatter.
- Cleaned dictation is allowed only when labeled: `**cleaned**`, with the raw
  wording alongside.
- A line the assistant said first and you echoed back is labeled
  `**assistant-coined, echoed**`. It can be kept; it cannot pass as yours.
- Every note cites the conversations it came from:
  `*Sources:* [[2024-03-02-rethinking-the-founder-plan]]`

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
supersedes: 2023-11
source: chatgpt-archive          # or chatgpt-synthesis if model-worded
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
