# Ranking notes (dry run, synthetic "Sam" archive, 2026-09-26)

Corpus: 10 conversations, 9 scored (1 branch duplicate). Kept 5, rejected 5. The mechanical top 5 matched the reviewed top 5, which is luck on a tiny synthetic corpus, not validation: three of the signals that put them there are wrong in ways that will matter on a real archive. Findings are ordered by how much they would cost at scale.

Per-signal contributions below were computed from `index.json` with the weights in `synth/config.py` (the dry-run config overrides no weights).

## 1. The return-visit signal punishes the one real return visit

`2024-03-02-rethinking-the-founder-plan` is the only conversation in the corpus where the owner came back to a thought on later days ("Okay I slept on it", "Coming back to this a week later"). It spans 189 hours over 3 days and contains the known position change. The score gives it:

- `return_visit`: **0**, because `content_days` is 0. `CONTENT_DAY_WORDS = 80` (`synth/parse.py`) and his turns are 74, 55 and 46 words. A terse typer never earns a content day.
- `routine`: **-1.66**, because `days_touched >= 3` and `175 / 3 = 58 < routine_min_wpd (80)`. The routine rule in `rank.score` fires on it the same way it fires on the 7-day to-do thread.

So the signal meant to tell "a thought you kept returning to" from "a standing-instruction thread" scores them the same direction. It only ranked 3rd because nothing else in the corpus competes.

Retune (all mechanical):
- Lower `CONTENT_DAY_WORDS` to about 30, or make it relative (a day counts if it holds at least 25% of the conversation's authored words).
- Gate the routine penalty on **repetition**, not words per day: `daily-check-in` has 7 byte-identical user turns. Normalized-turn duplication (share of user turns whose `norm()` text equals an earlier turn's) separates the two cleanly here: 6/7 for the check-in, 0/3 for the founder plan.
- Do not apply `routine` when `content_days` is 0 and `authored_turns` has no duplicates.

## 2. Duplicated text is counted as authored every time

Three conversations repeat the same block: the walk-home memo is pasted 3 times (368 own-voice words, ~123 unique), the daily check-in sends one prompt 7 times (98 words, 14 unique), the parser-bug function appears 6 times. Only the last was harmless (code is already pasted). The check-in scored 7.95 and outranked the code and coursework rows on `authored_words` (4.60), `turn_depth` (1.25) and `turn_length` (2.44), all earned by repetition. The walk-home memo would still be first after dedupe, but its `own_voice` and `authored_words` contributions are inflated about 3x in words.

Retune: count a repeated paragraph or repeated whole turn once in `authorship()` (`synth/parse.py`). Mechanical: dedupe on normalized sentences or 8-gram runs within the conversation's own user text, the same machinery `echo_share` already uses against assistant text.

## 3. Relapse is invisible to the ranker; the D on borrowed-ambition is an accident

`rank.delta_candidate` only flags conversations **before** a dated change. It has no notion of a conversation **after** a change that contradicts it. `2025-05-05-borrowed-ambition` (making plans to start a company 14 months after dropping that aim) got its D from the staleness fallback: `business` is in `volatile`, has no dated change, and every conversation is older than `stale_after_days = 120` because the review is running in 2026 on an archive ending 2025-07. That fallback would have marked any business conversation, relapse or not.

- Relapse detection needs knowing whether a conversation after the change *contradicts* it. Topic match plus date is not enough (said-it-first is after the change on the same subject and agrees with it). **This cannot be computed mechanically**; it is a reader judgment. What can be computed: a "post-change, same topic" flag (date > change date and topic matches) as a list for readers to check, shown separately from the "was" deltas.
- Staleness should be measured against the archive's last conversation date, not `date.today()`. Otherwise everything in a volatile topic is stale on any archive reviewed a few months after export.

## 4. Topic routing: the config's position-change topic never meets the relapse, and "self" never fires

Topics assigned by rank: founder plan `career, business`; borrowed-ambition `business`; everything else `-`. Five of nine conversations, including all three self/goals rows, get no topic.

- **Config mistake:** `position_changes` is on `career`, but the founder aim is vocabulary the `business` pattern catches (company, founder, business, sales). Borrowed-ambition has zero career terms, so the dated change can never apply to it. Recommend either adding `founder|company` style terms to `career` in the owner's config, or tagging the change with both topics (the loader has no multi-topic change; a second `[[position_changes]]` entry with `topic = "business"` and the same date works).
- **"want" is a stopword** (`STOP` in `synth/parse.py`). It is the single most important content word in this owner's reflective writing (walk-home, two-lists, the founder plan). It can never reach a topic regex. Also stopped: `think`, `need`, `thing`. Recommend removing `want` and `need` from `STOP`; they are not filler in a corpus about what someone wants.
- **`self` never matches** in this corpus. Its pattern is abstract nouns (identity, values, meaning, purpose) plus `fear\w*` and `feel\w*`. Sam reflects in plain verbs: want, care, hurt, settling, costume, ambition, goals. Adding `ambition|goals?|care|hurt|settl\w*` would route walk-home, two-lists, the founder plan and borrowed-ambition. Be honest about the limit: people reflect in feeling words that are also everyday words, and no pattern list will separate "I care about travel" from "take care". Use it for routing to a section, not for scoring.
- `min_term_hits = 2` is too strict for short conversations: two-lists has one career hit (`promoted`) and one creative hit (`write`); parser-bug has one tech hit (`python`; `parser` and `parse` are not in the tech pattern). Scale the threshold with authored words (1 hit under ~150 authored words) or add `pars\w*|bug|debug\w*|throw\w*` to tech.
- `health` (`gym`) and `creative` (`write`) each have exactly one hit; `relational` has none. Not errors; the corpus has no such material.
- The loader printed no unknown-key warnings for this config.

## 5. What actually separated thinking from noise here

In order of how cleanly they split kept from rejected in this corpus:

1. **Own-voice preamble** ("here's my voice memo"): exact, never wrong, already weighted up. Keep.
2. **Pasted / quiz / chip / code classification** in `parse.classify_turn`: correct on all four rejected rows and on the chip in borrowed-ambition. The quarterly report (337 pasted words, voice_score below floor) correctly scored 0. Keep.
3. **Echo detection with `own_before`**: after the fix it credits said-it-first correctly (0 echoed) and still catches the "Yes exactly, <assistant sentence>" in borrowed-ambition (13 echoed). Keep.
4. **Assistant turn shape** (a signal the score does not use): in every kept conversation the assistant turns are short prompts (17, 6, 28, 11, 25 words total) and the owner does the reasoning; in the rejected paste the assistant wrote 240 words. `assistant_words / authored_words` is already computed as the consumption skew, but only penalizes above 6x. A low ratio is positive evidence the owner was thinking, not reading. Mechanical; worth a small positive weight.
5. **First-person reasoning verbs** ("I think", "I realized", "I notice", "I keep", "my fear was"): present in all five kept rows, absent from all rejected rows. Countable, but on a real archive "I think" also opens every request for help. Use only as a tiebreak, and do not expect it to survive a larger corpus unchanged.

Signals that did not help: `turn_depth` (rewarded the 7-turn to-do loop most), raw `days_touched` (see 1), `longest_turn` beyond the own-voice case (the kept typed rows are all 39 to 74 words, same band as the parser bug).

## 6. Authorship cases the parser cannot catch

- **Agreement after a truncated assistant turn.** Walk-home: "That's right. I want to stop pre-deciding I don't care." follows "Here's a synthesis of your memo..." (cut off in the export). The echo check sees nothing to compare against and credits the line. Mechanical partial fix: when the previous assistant turn ends in "..." or is under ~10 words while the user turn opens with agreement ("that's right", "yes exactly", "exactly", "yes"), flag the turn `unverifiable` in the index so readers and verify see it. It cannot tell whether "pre-deciding" was coined by the assistant; only the full export could.
- **Agreement openers in general** ("Yes exactly", "That's right") are regex-detectable and worth surfacing as a per-conversation count for readers, not as a score term.
