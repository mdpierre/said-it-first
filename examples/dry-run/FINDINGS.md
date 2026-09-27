# Findings from the dry run

A full run of `/archive-synthesis` on the synthetic export, with a fictional
owner ("Sam") played by a person in chat. This file lists every place the
skill, an agent file, or the scripts were ambiguous, wrong, or failed.

**Agent types.** All four resolved and ran as their named types:
`chunk-reader` (x3, in parallel), `shortlist-reviewer`,
`delta-reconstructor`, `section-extractor`. No fallback to a
general-purpose agent was needed.

Line numbers refer to the commit this file was added in. Bugs in `synth/` were
fixed, each with a regression test. Problems in instruction files (skill,
agents, templates) are listed here, not rewritten.

---

## A. Bugs fixed in `synth/`

### A1. verify: a plain word between two bold spans counted as a label
`synth/verify.py` `_bold()` (was line 54). The regex
`\*\*[^*\n]*\b(chip|...)\b[^*\n]*\*\*` matched from the *closing* `**` of one
bold span to the *opening* `**` of the next. So in
`**Trap:** turn 3 is where he clicked through, see **Why**`, the plain word
"clicked" labeled a chip quote as deliberately kept, and verify passed it.
Found when the chunk-03 reader saw a quote counted as labeled before it had
added any label.
**Fix:** bold spans are paired left to right and only their insides are
searched; the label context is joined with newlines so a span can't pair
across lines. Test: `test_plain_word_between_bold_spans_is_not_a_label`.

### A2. verify and parse: the owner's own line, quoted back, counted as an echo
`synth/verify.py` `check_quote()` and `synth/parse.py` `echo_share()` /
`authorship()`. The fixture's "Said it first" conversation: Sam writes a line,
the assistant quotes it back ("You wrote: ..."), Sam repeats it with a reason
added. The existing test only covered quoting the bare first line. Quoting the
second turn (line + reason) was flagged **echoed**, and `index.json` gave the
conversation 15 `echoed_words`, lowering its score.
**Fix:** a word run the owner wrote in an earlier authored turn is not an echo
even if the assistant repeated it in between. Tests:
`test_owner_said_it_first_then_repeated_with_more_not_echo`,
`test_owner_repeating_own_line_not_echoed`. Effect on this archive: echoed
words 28 -> 13; the said-it-first score went 10.32 -> 10.84.

### A3. stats disagreed with parse on the same archive
`synth/stats.py` `run()`. `stats` classified whole turns with fenced code
still in them; `parse` strips code first and counts it as pasted. On this
archive `stats` reported 1,033 authored words and `parse` 966 (938 + 28
echoed) for the same turns. A calibration tool that classifies differently
from the classifier it calibrates is misleading.
**Fix:** stats classifies the prose the way parse does and counts code as
pasted. `run()` now returns the word counts. Test:
`test_stats_split_matches_parse`.

---

## B. Skill: `.claude/skills/archive-synthesis/SKILL.md`

- **B1. line 41-43: "date range" is asked for but nothing prints it.**
  `synth run` reports counts, not dates. I read it off `MANIFEST.md`
  (chunk From/To). Either print it in `parse` or point at the manifest.
- **B2. lines 34, 59: re-running `synth run` stops at rank.** After a parse
  fix (or after lowering `AUTHORED_FLOOR`, as line 59 suggests), `synth run`
  re-parses and re-voices, then rank refuses because `SHORTLIST.md` exists
  (`synth/rank.py:327`). That guard is right, but the skill never mentions
  `--force` for a shortlist nobody has reviewed yet, or `--out`.
- **B3. line 15-17 vs code blocks at 34 and 84.** "Pass `--config` to every
  command" is in prose; the command blocks omit it. Fine for a careful reader,
  easy to miss when copying commands.
- **B4. Stage 6 (lines 93-104) has no step for resolving an
  `## Open: archive vs profile` section.** The owner answered it ("May was a
  relapse that ended"). I turned the Open section into a history entry
  (`2025-05 -> 2025-07 (relapse, ended)`, cause "not in the archive") and
  recorded that the owner confirmed it on review. The skill and
  `templates/note-format.md:94-108` say to add the section and ask, but not
  what the note should look like after the owner answers. Also unstated:
  whether a position that survived a relapse moves to `core` (the template's
  `core` definition, note-format.md:112, suggests so). I left it `working`.
- **B5. Stage 6 promote ledgers conversations before stage 7 reads them.**
  `synth promote` marks every cited conversation `promoted` in the ledger
  (`synth/promote.py:92-94`). Here the three deltas cited all five shortlist
  rows, so after stage 6 the ledger already skipped every conversation the
  section loop had yet to read. If a run stops between stages 6 and 7, the
  next export will never show those rows again. The skill (lines 119-121)
  treats the ledger as stage 7's job. This is a design question (what should
  "promoted" skip?), so it is listed, not changed.
- **B6. Stage 7 (lines 108-122) assumes sections are unread.** When stage 6
  already promoted notes built from a section's conversations, the extractor
  can only propose small merges. The extractor handled it ("strike, already
  covered"), but the extraction sheet has no box for that outcome
  (`templates/extraction-sheet.md:17`).
- **B7. Stage 5 (line 84) says `python3 -m synth verify` checks staging, but
  `_`-prefixed files are skipped** (`synth/verify.py:119`). `_REPORT.md` and
  `_RANKING_NOTES.md` carry verbatim quotes that nobody verifies. The
  delta-reconstructor noticed this itself.

- **B8. No path for reopening a closed section.** After the Career section,
  the owner revised two Self decisions (merge instead of strike; cross-link
  instead of leave as is). The skill's stage 7 is one pass per section. I
  merged in `staging/approved/`, promoted with `--replace`, and appended a
  "revised" block to the Self sheet keeping the first decisions for the
  record. The skill should say that this is allowed and how to record it.
- **B9. Do the shortlist's Rejected rows get ticked?** Line 119-120 says
  "declined rows count" as dispositioned, but the Rejected section is the
  reviewer's declines, not the owner's. Unticked, they come back on the next
  export (here: 4 of them). The owner was asked and did not answer, so they
  were left unticked. The skill should say which is the default.
- **B10. Stage 8 re-rank (line 132-133) doesn't mention `--include-reviewed`.**
  After stage 7 the ledger skips every reviewed row, so a plain
  `rank --out` shows only the leftovers and can't be compared with the
  shortlist the owner reviewed. The comparison here used
  `--include-reviewed` (`workspace/stage8/rerank.diff`); the plain run is
  kept too (`workspace/stage8/SHORTLIST.next-export.md`).
- **B11. Owner answers can arrive out of order.** Sam answered stage 7 Self
  questions in reply to a stage 8 question, and later said "get promoted
  stays open" after giving a clarification that was already promoted. I kept
  the promoted clarification (it was explicit) and asked. The skill's stops
  could restate which questions are still open each time.

## C. Agent files

### `.claude/agents/chunk-reader.md`
- **C1. line 39: "~<words> owner words" is ambiguous.** All three readers
  asked: all user words, or authored only? Branch duplicates and the memo
  repeated within a turn included? The chunk header and `MANIFEST.md` give
  tokens, not words. Each reader picked something different.
- **C2. line 65-66: "high-scoring in `index.json`".** `index.json` has no
  score field (score is computed by rank and appears only in `SHORTLIST.md`).
- **C3. lines 71-73: verify's 40-character floor is not mentioned.** Two
  readers put short assistant phrases in quotation marks; verify passed them
  (under 40 characters). `templates/note-format.md:38-39` says to hand-check
  short quotes, but chunk-reader.md tells readers to rely on verify.
  The same applies to `delta-reconstructor.md:73-78` and
  `section-extractor.md:47-49`: all three agents found short assistant phrases
  in their own drafts by hand. (The section-extractor concluded verify skips
  inline quotes; it does not. Inline quotes of 40+ characters are checked; the
  ones it found were short.)
- **C4. line 72: `--dir <your reading file>`.** Works with a file, but the
  flag name reads as a directory. The CLI help (`synth/verify.py`) says
  "file or folder"; the agent file doesn't.
- **C5. lines 29-30: `index.json` shape.** It's a list keyed by `file`
  (with `.md`), not a map keyed by stem. One reader noted the easy mistake.
- **C6. lines 44, 57-61: where a D mark's explanation goes.** Unclear whether
  a relapse marked D in Candidates also needs a Position-statement bullet.
  One reader did both.
- **C7. No guidance for empty sections** (chunk-02 had no candidates). The
  reader kept the table header and wrote "None".

### `.claude/agents/shortlist-reviewer.md`
- **C8. lines 83-85: "Write only to those two paths" leaves no room for
  scratch work.** The reviewer ran `synth rank --out /private/tmp/...` to
  see topic routing, broke the rule, and deleted the file. Say whether a
  scratch `--out` or an in-process `rank.score_all` call is allowed.
- **C9. lines 62-64, 70: sizes assume a large archive.** "60 to 120 rows" and
  "Rejected covers the mechanical top N" (N = 60) both exceed a 9-row corpus.
  "Fewer is right" rescued it.
- **C10. line 53: no Authorship column,** though readers report authorship
  per row. The reviewer packed it into `Why`, making cells very long.
- **C11. line 67: no heading given for triage notes.** Reviewer used
  `## Triage notes`.
- **C12. Profile framing rule vs verbatim quotes.** The profile bans
  startup/growth/scale language; Sam's own words include "start my own
  company" and "founder". Neither this file nor `templates/note-format.md`
  says the framing rules bind drafted prose but not verbatim quotes. The
  reviewer and the delta agent both reached that reading independently.
- **C13. Out-of-scope rule has no instruction for the shortlist or reading
  notes.** The reading files name the father directly; the reviewer
  generalized it in the shortlist. chunk-reader.md:77-78 says "flag, don't
  drop" but not whether to name.

### `.claude/agents/delta-reconstructor.md`
- **C14. Stability conflict.** The mechanical shortlist's triage notes say
  delta rows are `stability: provisional` (`synth/rank.py:298`);
  `templates/note-format.md:112-116` defines `working` for a current,
  untested position the owner holds. The agent followed the template
  (`working` for the known change).
- **C15. Voice of the current position.** `templates/note-format.md:77` says
  "what you think now" and the profile is in first person; the agent wrote
  third person ("He wants...") so model prose doesn't read as the owner's
  words on unconfirmed notes. Owner kept it. The template should decide.
- **C16. One delta's frontmatter disagrees with its heading.**
  `ambition-is-not-one-costume.md` has `position-since: 2024-03` and
  `## Current position (2025-07)`. The note covers two steps; the template
  doesn't say which date `position-since` takes. Promote doesn't check it.

### `.claude/agents/section-extractor.md`
- **C17. line 47: slug example vs a reviewer-written heading.** The rule
  applied to the reviewer's long heading gives a 60-character file name. Not
  wrong, but the reviewer's instructions don't ask for short section names.
- **C18. Word count again** (line 62): "each distinct turn once" doesn't cover
  one turn repeating its own text.

## D. Verify output that misled three agents (not yet fixed)

- **D1. `**unverifiable**` is invisible in the summary.** A quote whose
  assistant context is cut off passes as `ok`, so its label is never counted
  (`synth/verify.py:181`, `labeled` is computed only for non-ok statuses).
  The chunk-01 reader, the delta agent and the extractor each reported
  "0 labeled" while holding an unverifiable quote and wondered whether the
  label was seen. The docstring says the label "accepts any status", which
  reads as if it is counted.

## E. Scoring and routing (reported by the shortlist-reviewer, spot-checked)

Recommendations, not bugs; they are the owner's to apply per the skill's
stage 8. Full detail in `workspace/staging/_RANKING_NOTES.md`.

- **E1. Staleness is measured against today, not the export's end**
  (`synth/rank.py:129`, `score_all` uses `dt.date.today()`). "Borrowed
  ambition" got its D from staleness in `business`, not from relapse
  detection. On any export run months later, every volatile row is stale.
- **E2. The dry-run config's position change is tagged `career`, but the
  founder vocabulary routes only to `business`** (`synth/config.py:96-97`).
  So the dated change never reached "Borrowed ambition". A config lesson worth
  a line in `said-it-first.example.toml`: tag a change with every topic its
  conversations actually route to.
- **E3. "want" is a stop word** (`synth/parse.py:364`), and the `self` topic
  matched nothing here. The self material is phrased in wanting words.
- **E4. `CONTENT_DAY_WORDS = 80`** (`synth/parse.py:394`) gave the only real
  return-visit conversation (founder plan, 46-74 word turns over 8 days) zero
  return credit and a routine penalty.
- **E5. Rank's summary line reads as if coursework was dropped:**
  "scored 9 conversations (1 coursework, 1 branch duplicates dropped)"
  (`synth/rank.py:336`). Coursework is scored and penalized; only the branch
  duplicate is dropped.
- **E6. Voice chunks include branch duplicates.** Rank drops them, but
  `synth/voice.py` does not, so chunk-01 contains
  `2024-03-04-branch-rethinking-the-founder-plan` and a reader spent time
  declining it. Whether a branch can hold new material after the fork point
  is a design question, so this is not changed.

- **E7. The approved config change removed the relapse's D mark.** Stage 8
  added `[[position_changes]]` 2024-03-10 with `topic = "business"` (owner
  approved). Re-ranking shows "Borrowed ambition" (2025-05-05) **losing** its
  D: `business` is now landmarked, so the staleness fallback no longer
  fires, and the conversation is after the change, so `delta_candidate`
  (`synth/rank.py:118-131`) can't flag it. The mark it had was an accident
  (E1); the fix for the relapse case is reader judgment or a separate
  "post-change, same topic" list, not config. Kept as approved.
- **E8. Owner decisions on code recommendations.** Staleness vs today (E1),
  "want" as a stop word (E3) and `CONTENT_DAY_WORDS` (E4) were declined as
  code changes and stay here as findings. Widening the `self` topic was not
  applied (it would copy all seven default topics into the config).

## F. Fixture and environment

- **F1. The fixture memo is its own text three times**
  (`tests/make_fixture.py:77-85`, `* 3` to reach the long-turn threshold).
  Every agent read it as a real dictation artifact, counted `own_voice_words`
  (368) as ~3x inflated, and wrote caveats into notes ("the memo appears three
  times in the export"). Harmless, but it teaches readers a pattern real
  exports don't have. Three distinct paragraphs would test the same thing.
- **F2. zsh: `echo =====` fails** (`=word` expansion). Hit by me and by an
  agent using separators in Bash. Environment, not pipeline.
