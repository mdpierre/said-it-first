---
name: archive-synthesis
description: Run the chat-archive synthesis pipeline on a ChatGPT export. Parses, strips to the owner's own words, ranks, dispatches reading agents, verifies every quote, and walks the owner through section-by-section review before anything is written to their notes. Use when the user says "synthesize my archive", "run the pipeline", "process my ChatGPT export", or names a stage.
---

# Archive synthesis

You are orchestrating. Scripts do the counting, subagents do the reading, the
**owner decides**. Nothing reaches the notes folder without the owner's
explicit approval of that specific content, and **only through
`synth promote`**, which refuses any note that fails verification. Never
write into the notes folder directly. That gate is the point of the
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

`parse` validates the export format first. An `ERROR` line means nothing was
written: report it to the owner, don't use `--skip-check` without their say.
A `USER TEXT DROPPED` warning means some of the owner's messages use a
content type the parser doesn't know. Stop and show the owner the warning;
the fix is one line in `synth/parse.py` (`TEXT_TYPES`) or `synth/schema.py`
(`EXPECTED_DROPS`).

Then **check the counts** in the output before moving on:
- `input` = `parsed` + `skipped`; any "unaccounted" or "WARNING" line stops
  the run until explained.
- the voice stage must not warn about dropped words or oversized chunks.
- Report to the owner: conversations, date range, authored vs pasted vs
  echoed share, own-voice memos found, how many were skipped as already
  reviewed (the ledger), and the number of reading chunks.

**Repeat runs.** The ledger (`paths.ledger`) remembers every conversation
reviewed on earlier runs. `rank` and the voice chunks skip them, and bring a
conversation back marked *continued* if the owner added turns since. A
second export therefore reads only what's new. If the owner reviewed a
shortlist before the ledger existed, run `synth ledger sync --shortlist
<that file>` first.

**Chunk size.** `voice.chunk_tokens` (default 60k) must fit a reader's
context with room to work. Raise it on long-context models to cut the number
of readers; if a chunk-reader reports running out of room, lower it and
re-run `synth voice`.

Optional but recommended on a first archive: `python3 -m synth stats`, and
read the samples near the floor with the owner. If their own writing is being
classed as pasted, lower `AUTHORED_FLOOR` in `synth/parse.py` and re-run.

## Stage 4: reading (subagents)

**4a. Chunk readers.** Read `<archive>/voice/chunks/MANIFEST.md`. Dispatch
one `chunk-reader` per chunk, in parallel (batches of about five), each told
its chunk file and the resolved paths. Each writes
`<staging>/reading/chunk-NN.md`.

When they're done, check every chunk has a reading file. A missing or
near-empty one gets re-dispatched, not skipped: the merge can only rank what
someone read.

**4b. Merge.** Dispatch both, in parallel, with the resolved paths:
- `shortlist-reviewer`: merges the reading notes into a judged, sectioned
  SHORTLIST.md plus `_RANKING_NOTES.md`.
- `delta-reconstructor`: works from the readers' position statements and
  the transcripts; writes staged deltas plus `_REPORT.md`.

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
they approve:

1. If a note on that idea already exists in the notes folder, **merge in
   staging**: copy the existing note into `<staging>/approved/`, fold the
   delta in (current position on top, history below). Never create a dated
   duplicate.
2. Otherwise put the approved delta in `<staging>/approved/` as is, with the
   owner's corrections applied.
3. `python3 -m synth promote <staging>/approved/<note>.md` (add `--replace`
   for a merge). If it refuses, show the owner the reasons; fix or label,
   then promote again. Never work around a refusal.

## Stage 7: section loop

For each section of the reviewed shortlist, in the order the owner picks
(suggest own-voice memos first; they have the highest yield):

1. Dispatch `section-extractor` with the section name.
2. Present the sheet summary: candidates, merge questions, anything flagged.
   Ask the open questions **before** writing.
3. The owner ticks, strikes, corrects. Write each approved note, in note
   format with a `*Sources:*` line, to `<staging>/approved/`, merging with
   any existing note as in stage 6.
4. `synth promote <staging>/approved/<note>.md` for each. Refusals go back to
   the owner.
5. Tick the section's rows in the shortlist as *read and dispositioned* (a
   tick does not mean promoted; declined rows count), then
   `synth ledger sync` so the next export skips them.
6. Report: notes new / merged / declined, quotes verified.

The archive lags. If a note would record something as dead or abandoned,
**ask the owner** whether that is still true. The export cannot see anything
after its date.

## Stage 8: housekeeping

- `synth ledger sync` once more, and `synth ledger show` for the owner.
- If _RANKING_NOTES.md recommends weight or marker changes, show the owner the
  diff to `chat-synthesis.toml`, apply on approval, and re-run rank to
  `--out` a temp path to compare. Never overwrite a shortlist mid-review.

## Rules that hold at every stage

- Staging is for drafts; notes are for approved content only, and only
  `synth promote` writes there.
- Quote verbatim or don't use quotation marks.
- Old positions are history, not errors. Record them, never delete them.
- Follow the profile's framing and writing rules in everything you write.
