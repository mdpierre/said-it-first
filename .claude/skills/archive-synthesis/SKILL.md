---
name: archive-synthesis
description: Run the chat-archive synthesis pipeline on a ChatGPT export. Parses, strips to the owner's own words, ranks, dispatches reading agents, verifies every quote, and walks the owner through section-by-section review before anything is written to their notes. Use when the user says "synthesize my archive", "run the pipeline", "process my ChatGPT export", or names a stage.
---

# Archive synthesis

You are orchestrating. Scripts do the counting, subagents do the reading, the
**owner decides**. Nothing reaches the notes folder without the owner's
explicit approval of that specific content. That gate is the point of the
pipeline, not a formality.

Always start with `python3 -m synth paths` and use the paths it prints. Pass
`--config <path>` to every command if the owner uses a config outside the
repo root.

## Stage 0: setup (first run only)

1. `chat-synthesis.toml` exists? If not, copy `chat-synthesis.example.toml`
   and ask the owner for: where approved notes should go (`paths.notes`),
   link style, and any known position changes with dates.
2. Profile exists? If not, copy `templates/profile.example.md` to the profile
   path and **interview the owner** to fill it: current positions, known
   changes, framing to avoid, writing rules, out-of-scope topics. Keep it
   short. Do not invent positions for them.
3. Tell the owner plainly: the model passes send their conversation text to
   the model provider. The scripts are local only.

## Stages 1-3: mechanical (scripts)

```
python3 -m synth run <export.zip | export-dir>
```

Then **check the counts** in the output before moving on:
- `input` = `parsed` + `skipped`; any "unaccounted" or "WARNING" line stops
  the run until explained.
- the voice stage must not warn about dropped words.
- Report to the owner: conversations, date range, authored vs pasted share,
  own-voice memos found, voice corpus size in tokens.

Optional but recommended on a first archive: `python3 -m synth stats`, and
read the samples near the floor with the owner. If their own writing is being
classed as pasted, lower `AUTHORED_FLOOR` in `synth/parse.py` and re-run.

## Stage 4: reading passes (subagents, in parallel)

Dispatch both, each with the resolved paths in the prompt:
- `shortlist-reviewer`: replaces SHORTLIST.md with a judged, sectioned list
  plus RANKING_NOTES.md.
- `delta-reconstructor`: writes staged delta files plus `_REPORT.md`.

Both need the voice corpus in context. Use the longest-context model
available. If the corpus is larger than context, tell them to work year by
year.

When they return, **do not relay their summaries as fact.** Spot-check: open
two or three rows of the new shortlist and one delta against the source.

## Stage 5: verify

```
python3 -m synth verify
```

Every failure goes to the owner with the quote and file. Unsourced means
paraphrase in quotation marks; echoed means the assistant said it first. The
owner decides: cut, fix, or keep with a label. Never silently fix and move on.

## Stage 6: owner reviews deltas

Point the owner at `<staging>/deltas/` and `_REPORT.md`. Wait. For each delta
they approve, write it into the notes folder in `templates/note-format.md`
shape. If a note on that idea already exists, **merge** (current position on
top, history below); never create a dated duplicate. Run `synth verify --dir
<notes>` on what you wrote.

## Stage 7: section loop

For each section of the reviewed shortlist, in the order the owner picks
(suggest own-voice memos first; they have the highest yield):

1. Dispatch `section-extractor` with the section name.
2. Present the sheet summary: candidates, merge questions, anything flagged.
   Ask the open questions **before** writing.
3. The owner ticks, strikes, corrects. Write only the approved notes, in note
   format, with `*Sources:*` lines.
4. `synth verify --dir <notes>`; fix or label every failure.
5. Tick the section's rows in the shortlist as *read and dispositioned* (a
   tick does not mean promoted; declined rows count).
6. Report: notes new / merged / declined, quotes verified.

The archive lags. If a note would record something as dead or abandoned,
**ask the owner** whether that is still true. The export cannot see anything
after its date.

## Stage 8: housekeeping

- Every new note cites a source conversation (grep for notes without
  `*Sources:*`).
- If RANKING_NOTES.md recommends weight or marker changes, show the owner the
  diff to `chat-synthesis.toml`, apply on approval, and re-run rank to
  `--out` a temp path to compare. Never overwrite a shortlist mid-review.

## Rules that hold at every stage

- Staging is for drafts; notes are for approved content only.
- Quote verbatim or don't use quotation marks.
- Old positions are history, not errors. Record them, never delete them.
- Follow the profile's framing and writing rules in everything you write.
