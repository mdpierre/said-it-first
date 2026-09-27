# Deltas report (dry run, synthetic owner "Sam")

**Verify:** `python3 -m synth verify --dir workspace/staging/deltas`: 19 quotes
checked, 0 not verbatim, 0 unlabeled echoes, 0 unlabeled pastes/chips,
3 labeled and kept deliberately (2 **assistant-coined, echoed**, 1 **chip**).
One more quote carries **unverifiable** by hand; verify cannot detect that case.
Quotes under 40 characters were checked against the transcripts by hand. Two
of them were assistant wording inside quotation marks and were changed to
paraphrase.

Archive: 10 conversations, 2024-03-02 to 2025-07-15. Four carry owner
reasoning (founder-plan, walk-home, borrowed-ambition, two-lists), plus
said-it-first, which restates a position. The rest are a branch duplicate,
a paste, coursework, a to-do template and a code question.

## Deltas written

| File | Change | Stability | Was side in the corpus? |
|---|---|---|---|
| `technical-lead-track-not-founding.md` | founder aim -> tech lead track (2024-03) | working | **Yes**, in his own words, 2024-03-02 |
| `ambition-is-not-one-costume.md` | "settling" fear -> ambition is not one form (2024-03); unsure if lazy -> sorts own goals (2025-05 -> 2025-07) | provisional | Partly: see below |
| `letting-myself-want-things.md` | deciding ahead he doesn't care -> naming what he wants (2025-01) | provisional | Only as his retrospective self-description |

## Known changes: genuine was vs asserted

- **2024-03-10 career (founder -> technical lead track): genuine.** The Was,
  Now and Because are all in the owner's turns of
  [[2024-03-02-rethinking-the-founder-plan]], a conversation spanning about
  8 days. The Was can be seen directly ("I keep telling myself I want to start
  my own company", "stop pitching myself as a future founder in interviews"),
  though by the first turn he was already doubting it. The Now ("told my
  manager I want the technical lead track") lands about 2024-03-10 by
  `span_hours`, which matches the profile date. There is no earlier
  conversation where the founder aim is held without doubt. How long he held
  it before 2024-03 is unknown (`supersedes: before-2024-03`).

That is the only known change. It is supported.

## Unrecorded changes found

1. **Ambition vs "a specific costume of ambition"** (2024-03). The fear that
   not founding meant settling, and how he resolved it. It is part of the career
   change but is its own idea, and it comes back in 2025.
   *Limit:* the Was ("My fear was that I'd be settling") appears only in the
   same turn that lets it go. No earlier turn states it.
2. **Chosen vs performed goals** (2025-05 -> 2025-07). In May he can't tell
   if he is "lazy". By July he sorts his goals himself into cares-about and
   should-want lists. *Cause unknown:* the only thing between the two dates is
   the assistant's "borrowed ambition" framing, which he agreed to (labeled
   echoed). I did not credit him with it.
3. **Letting himself want things** (2025-01-15). Moves from deciding ahead of
   time that he doesn't care to "I actually do want stuff". *Limit:* the Was is
   his own description in the memo where he notices it. No earlier
   conversation shows the habit.

## Open: archive vs profile (questions for the owner)

1. **Founder plans in May 2025.** The profile says tech lead, not founding,
   since 2024-03. On 2025-05-05 the archive has "I keep making plans to start a
   company and every one of them feels heavy before I even begin." On
   2025-07-15 he is back in line with the profile ("I would rather be trusted
   with hard problems than be the one who owns them"), but nothing says the
   company plans stopped. Was May a relapse that ended, or something still
   running? The archive ends 2025-07-15.
2. **"Get promoted" is on the should-want list** (2025-07-01), while the
   profile's current position is working toward the tech lead track. Is that
   a contradiction, or is promotion different from the track? I did not
   decide this. It is not written into any note as a conflict.
3. **"Make things that are mine" (2025-01) / "build one thing that is mine"
   (2025-07)** alongside the May 2025 company plans. These may or may not be
   the same want. I made no link beyond the fact that both phrases appear.

## Out of scope: flagged for the owner

- **Career cause, specific withheld:** the founder aim came from a saying of
  his father's (2024-03-02, turn 1). The note records it in general terms only
  ("a view about what real work is that he absorbed growing up"). Owner to
  decide whether the specific belongs in the note.
- **Wanting cause, quoted:** "it was easier to be the easy one in the house".
  I judged this in scope because it is Sam describing himself, not another
  family member, so it is quoted. The reader suggested general terms. Owner to
  cut it if he disagrees.

## Looked for, not supported

- Any turn where founding is held **without doubt** (the pure Was). There is
  none. The earliest turn is already questioning it.
- A **cause for the May 2025 return** of company plans. There is nothing in
  his words. The "borrowed" explanation is the assistant's.
- Any **2024-03 to 2025-01 material** on career. The archive has a 10-month
  gap. Absence is not evidence the position held steady or changed.
- Whether "pre-deciding" is his word. The assistant turn before it is cut off
  in the export (labeled **unverifiable**).

## Framing choices worth checking

- Current positions are written in the third person ("He wants..."). The
  template says "what you think now", and the profile uses "I". I kept model
  prose out of first person on unconfirmed notes so it does not read as his
  own words. Owner or orchestrator to decide.
- `technical-lead-track-not-founding` is `working`, not `provisional`. The
  profile confirms the current position, but the May 2025 evidence means it
  cannot be `core` until the owner answers question 1. The shortlist says
  delta rows should be `provisional` and the template's definitions point the
  other way. I followed the template.
