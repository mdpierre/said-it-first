# Dry run: a full pipeline run on invented data

A complete run of `/archive-synthesis` (stages 1 to 8) on the synthetic
`examples/sample-export/`, for a fictional owner, "Sam", a software engineer.
A person played Sam in chat and made every approval decision. Nothing here is
real data. What broke or was unclear is in [FINDINGS.md](FINDINGS.md).

Every command took `--config examples/dry-run/chat-synthesis.toml`.
`voice.chunk_tokens = 1000` is deliberately tiny so the sample splits into
3 chunks and exercises parallel chunk-readers.

## Stage-by-stage file map and counts

| Stage | Who | Files | Counts |
|---|---|---|---|
| 0 setup | orchestrator | `chat-synthesis.toml`, `profile.md` | 1 known position change (a 2nd, `business`, added in stage 8) |
| 1 parse | `synth parse` | `workspace/archive/conversations/`, `index.json` | 11 in = 10 parsed + 1 skipped; 953 of 1,427 user words authored, 461 pasted/clicked/quiz, 13 echoed; 1 own-voice memo, 1 coursework, 1 branch duplicate |
| 2 voice | `synth voice` | `workspace/archive/voice/`, `chunks/MANIFEST.md` | 10 conversations, ~2,318 tokens, 3 chunks |
| 3 rank | `synth rank` | `workspace/SHORTLIST.mechanical.md` | 9 scored, 2 delta candidates |
| 4a read | 3 `chunk-reader` agents in parallel | `workspace/staging/reading/chunk-0{1,2,3}.md` | 5 candidates, 17 position statements, 5 declines |
| 4b merge | `shortlist-reviewer` | `workspace/SHORTLIST.md`, `staging/_RANKING_NOTES.md` | 5 kept (Self 2, Career 3), 5 rejected, 3 proposed position changes |
| 4b merge | `delta-reconstructor` | `workspace/staging/deltas/` | 3 deltas, plus `_REPORT.md`, `_NOTES.md` |
| 5 verify | `synth verify` | (stdout) | 40 quotes, 0 failures, 5 labeled |
| 6 deltas | Sam, then `synth promote` | `staging/approved/`, `workspace/notes/` | 3 approved, 3 promoted; relapse resolved as "ended" |
| 7 Self | `section-extractor`, Sam | `staging/self-...-extraction.md` | 2 candidates: 1 struck, 1 merged (revised later), 2 notes cross-linked |
| 7 Career | `section-extractor`, Sam | `staging/career-...-extraction.md` | 3 candidates: 2 struck, 1 merged |
| 8 housekeeping | `synth ledger`, `synth rank --out` | `workspace/ledger.json`, `workspace/stage8/` | ledger 5 (all promoted), 5 unreviewed; 1 config change applied |

Final notes folder: 3 notes (`technical-lead-track-not-founding`,
`ambition-is-not-one-costume`, `letting-myself-want-things`), every one
through `synth promote`. `staging/approved/` matches `notes/`.

The reviewed `SHORTLIST.md` was never overwritten after review. The stage 8
comparison (`stage8/rerank.diff`) shows the approved config change removing
the D mark from the 2025-05-05 relapse row (FINDINGS E7).
