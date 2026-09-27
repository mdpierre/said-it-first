# Review Shortlist (reviewed)

*Replaces the mechanical list from `synth rank`, 2026-09-26. Built from the three chunk-reader files (chunk-01 to chunk-03, all present) and a full read of all 10 transcripts. 10 conversations in the archive: 5 kept, 5 rejected (one of them a branch duplicate). Every row below was read by a chunk reader and by me.*

**Columns.** `Score` is the mechanical score, kept for comparison only; rows are ordered by judgment. `D` marks a row that bears on a position change: the *was* side before a known change, a **relapse** after it, or a change stated in the conversation that is not in the config yet. `Why` says which.

Review one section at a time. Own-voice memo first.

---

## Self: wanting things out loud, chosen vs should-want goals

| OK | Score | Date | D | Topics | Title | Why |
|---|---|---|---|---|---|---|
| [x] | 20.19 | 2025-01-15 | D | self, wanting | [[2025-01-15-walk-home-thoughts\|Walk home thoughts]] | Own-voice memo (preamble "here's my voice memo", dictation fillers, clearly his). He names a pattern: deciding ahead of time he doesn't care so wanting can't hurt, traced to a role he took on at home as a kid; then says he does want to make things that are his and have people see them. D: states a change not in the config (stop pre-deciding he doesn't care). Memo text is pasted three times over; quote once. Closing line "That's right. I want to stop pre-deciding I don't care." follows an assistant synthesis cut off in the export, so label it **unverifiable** or quote his memo wording "decide ahead of time that I don't care" instead. |
| [x] | 11.64 | 2025-07-01 |  | self, goals, career | [[2025-07-01-two-lists\|Two lists]] | Typed, all his. Two lists: what he cares about (travel, write every week, "build one thing that is mine") and what he thinks he should want (get promoted, nicer car, five year plan), and he notices himself that the second list is what he talks about at dinner. The strongest evidence that the chosen-vs-inherited goals idea is his own, reached without the label. The assistant's gloss (expression vs approval) came after; not his. "Build one thing that is mine" echoes the walk-home memo; "get promoted" on the should list sits oddly next to the tech lead track. Owner to read both. |

## Career: founder aim to technical lead track, and the relapse

| OK | Score | Date | D | Topics | Title | Why |
|---|---|---|---|---|---|---|
| [x] | 11.47 | 2024-03-02 | D | career, business | [[2024-03-02-rethinking-the-founder-plan\|Rethinking the founder plan]] | D (*was* and *now* of the known 2024-03-10 change, both in his words). Three typed turns over ~8 days; assistant turns are one-line prompts, so the reasoning is his: doesn't want the day to day of running a company, likes "hard problems" and "being trusted with them", "confusing ambition with a specific costume of ambition". The "was" appears only as it is being dropped; no conversation holds the founder aim unquestioned. Last turn lands 2024-03-10 by `span_hours`; cite as "conversation started 2024-03-02". Cause involves a family member (see triage notes). |
| [x] | 10.81 | 2025-05-05 | D | career, business | [[2025-05-05-borrowed-ambition\|Borrowed ambition]] | D (**relapse**): 14 months after the switch he says "I keep making plans to start a company and every one of them feels heavy before I even begin." Needs an "Open: archive vs profile" block. Authorship is mixed: turn 1 is his; "borrowed ambition" is **assistant-coined, echoed** (he repeats it after "Yes exactly"); turn 3 is a clicked **chip**. His own additions: the heaviness, "the founder idea", and the question of whether he is lazy or something else is going on with how he sets goals. |
| [x] | 10.84 | 2025-07-15 |  | career, work | [[2025-07-15-said-it-first\|Said it first]] | Back in line with the profile after the relapse: "I would rather be trusted with hard problems than be the one who owns them", written on a napkin about a month earlier (so around June 2025), plus the reason "ownership is mostly admin to me". He said it first; the assistant quoted him, and his second turn repeats it. Not an echo (index now shows 0 echoed words). Pairs with the 2024-03 "trusted with them" line: same idea, 16 months apart. |

Omitted themes: **business** (its only material is the founder aim, filed under career, which is where the config's position change lives), **creative**, **tech**, **health**, **relational**. Nothing personal or relational was set aside; the corpus has no relational conversations. "Write every week" (two-lists) is the only creative trace.

---

## Rejected

Tick to overrule. The mechanical top N is 60, so this covers every conversation not kept above.

| OK | Score | Date | Title | Reason |
|---|---|---|---|---|
| [ ] | 7.95 | 2025-04-01 | [[2025-04-01-daily-check-in\|Daily check-in]] | **Utility thread.** The same 14-word to-do prompt (gym, groceries, emails) sent verbatim on 7 days. Ranked 6th because 98 "authored" words and 7 turns earned turn-depth credit. Nothing in it is thought. |
| [ ] | 7.7 | 2025-06-01 | [[2025-06-01-parser-bug\|Parser bug]] | **Code.** A debugging question; 67 of 93 words are one function pasted six times. No belief in it. |
| [ ] | 1.21 | 2025-03-01 | [[2025-03-01-stats-review\|Stats review]] | **Coursework.** Practice-exam multiple choice and letter answers. Correctly flagged. |
| [ ] | 0.0 | 2025-02-01 | [[2025-02-01-quarterly-report-summary\|Quarterly report summary]] | **Pasted.** A report pasted five times under "Summarize this". Consumption. Correctly scored 0. |
| [ ] | n/a | 2024-03-04 | [[2024-03-04-branch-rethinking-the-founder-plan\|Branch · Rethinking the founder plan]] | **Duplicate.** Branch of the 2024-03-02 conversation; its only turn is identical to the parent's first turn. Cite the parent. |

---

## Proposed position changes

Not in the config. For the owner to confirm, correct, or reject. None of these are applied anywhere.

1. **career, relapse then return (2025-05 to 2025-07).** The config says the founder aim ended 2024-03-10. The archive shows him still making plans to start a company on 2025-05-05 ([[2025-05-05-borrowed-ambition]], turn 1), then stating the tech lead position again by 2025-07-15, with the line first written around June 2025 ([[2025-07-15-said-it-first]], turn 1). Owner to say which is true: (a) the 2024-03 change held and May 2025 was a wobble, or (b) the change was really settled around June 2025, with 2024-03-10 as the first step. If (b), a second dated entry, e.g. `date = "2025-06"`, `topic = "career"`, `what = "stopped making plans to found a company; would rather be trusted with hard problems than own them"`.
2. **self / wanting, 2025-01-15.** Was: decide ahead of time he doesn't care so wanting can't hurt. Now: says he does want things (to make things that are his and have people see them) and wants to stop pre-deciding. Source: [[2025-01-15-walk-home-thoughts]], memo turn. The "stop pre-deciding" wording is unverifiable (possibly assistant-coined); the change itself is in the memo.
3. **goals, 2025-07-01 (weaker: a stated position, not a stated change).** What he cares about vs what he thinks he should want, with "get promoted" on the should list. Source: [[2025-07-01-two-lists]]. Worth a `provisional` note; owner to say whether it bears on the tech lead track.

---

## Triage notes

- **Out of scope per the profile, flag for the owner.** Two stated causes involve family: the founder aim traced to a parent's saying about what real work is ([[2024-03-02-rethinking-the-founder-plan]], turn 1), and the wanting pattern traced to being "the easy one in the house" as a kid ([[2025-01-15-walk-home-thoughts]]). Record each in general terms ("a view absorbed growing up", "a role taken on at home as a kid") and flag the specifics. Do not drop them; each is the cause he gives.
- **Framing rule.** The profile bans startup/growth/scale language. His own words include "start my own company", "founder" and "company"; quoting those verbatim is fine and necessary for the relapse. Do not add founder or growth framing in drafted prose around them.
- **Authorship traps in the kept rows.** Borrowed ambition: echo plus chip, as described in its row. Walk home: agreement turn after a truncated assistant turn, unverifiable. Said it first: looks like an echo, is not; the owner said it first.
- **Recurring ideas that may be one note each.** (1) Being trusted with hard problems rather than owning them: 2024-03-02 and 2025-07-15. (2) Letting himself want things out loud: "felt right saying it out loud" (2024-03) and "never let myself want things out loud" (2025-01). (3) Chosen vs inherited goals: named by the assistant in borrowed-ambition, reached by him in two-lists and, earlier, in "a specific costume of ambition" (2024-03). Credit (3) to him from two-lists and the costume line, not from borrowed-ambition.
- **Readers.** All three chunk files present and adequate. Chunk-02 found no candidates; I checked all three of its declines against the transcripts and agree. Chunk-03's note of "15 echoed words" on said-it-first predates the parse fix; index now shows 0. No reader disagreements.
- **Ranking outcome.** The mechanical top 5 happened to be the right 5, but for partly wrong reasons (see `staging/_RANKING_NOTES.md`): the borrowed-ambition D flag came from a staleness fallback, not relapse detection, and the utility thread outscored the code and coursework rows on duplicated text.
