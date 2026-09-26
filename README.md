# chat-synthesis

Turn years of ChatGPT conversations into a record of how your thinking
changed, without putting the model's words in your mouth.

If you think out loud in ChatGPT, your chat history is your real journal, but
it is buried under homework, code, pasted articles, and the assistant's half of
every thread. This pipeline digs out what's yours, ranks it by *did this change
what I think*, has Claude read the candidates, **verifies every quote against
the source**, and walks you through approving notes one section at a time.

Built on and tested against a real 4,164-conversation archive. See
[METHOD.md](METHOD.md) for what broke and why each piece exists.

```
export  ->  parse  ->  voice  ->  rank  ->  read (Claude)  ->  verify  ->  you approve  ->  notes
           (whose     (your       (triage)   (judgment)        (every       (nothing
            words?)    turns                                    quote)        skips this)
                       only)
```

## What makes it different

- **Authorship-aware.** Every user turn is classified: written by you,
  dictated by you, pasted, a quiz answer, or a clicked suggestion. On the
  reference archive, 33% of "user" words weren't the user's.
- **Voice memos weighted up, not down.** Long pasted turns are either
  someone else's article or your own dictated thinking. It decides by voice,
  not length.
- **Deltas, not snapshots.** Notes record *Was / Now / Because*, so you can see
  what you thought in 2023, what you think now, and what changed it.
- **Verified.** `synth verify` catches paraphrase in quotation marks and lines
  the assistant coined that you echoed back. The model's own reports never
  flagged either.
- **Local, stdlib-only Python.** No dependencies. The scripts never touch the
  network.

## Quickstart

Requires Python 3.11+ and [Claude Code](https://claude.com/claude-code) for
the reading stages.

```bash
git clone <this repo> && cd chat-synthesis
python3 -m unittest discover tests          # 16 tests on a synthetic export
python3 -m synth run examples/sample-export # try the scripts on fake data
```

Then with your own export (ChatGPT: Settings -> Data controls -> Export data):

```bash
cp chat-synthesis.example.toml chat-synthesis.toml
cp templates/profile.example.md profile.md    # or let the skill interview you
claude
> /archive-synthesis ~/Downloads/<your-export>.zip
```

The skill runs the scripts, checks the counts, dispatches the reading agents,
runs verification, and stops for your approval at every step that writes to
your notes.

## Stages

| # | Stage | Who | Output |
|---|---|---|---|
| 1 | `synth parse` | script | one markdown file per conversation + `index.json` |
| 2 | `synth voice` | script | your turns only, by year (the corpus models read) |
| 3 | `synth rank` | script | `SHORTLIST.md`, triage by authored words, voice, depth |
| 4 | reading passes | `shortlist-reviewer`, `delta-reconstructor` agents | judged shortlist, staged deltas |
| 5 | `synth verify` | script | every quote checked against source |
| 6 | delta review | **you** | approved deltas written as notes |
| 7 | section loop | `section-extractor` agent + **you** | extraction sheet -> approved notes |
| 8 | housekeeping | Claude + you | sources, retuned config |

Utilities: `synth stats` (calibrate authorship on your archive), `synth paths`.

## Configure

Everything personal lives in `chat-synthesis.toml` (gitignored): your topics,
dated position changes, platform markers, weights. See
[chat-synthesis.example.toml](chat-synthesis.example.toml). `profile.md` tells
the agents who you are now, so they can tell an old position from a current
one.

Point `paths.notes` at your Obsidian vault (or any folder). Links default to
`[[wikilinks]]`; set `link_style = "markdown"` otherwise.

## Privacy

Your archive is about as personal as data gets.

- The scripts are local. `workspace/`, your config, and your profile are
  gitignored.
- **Stages 4 and 7 send conversation text to the model** through Claude Code.
  Decide what you're comfortable with before running them; the profile has an
  out-of-scope section for topics that should never be extracted.
- Never commit your workspace. `git status` before every push.

## Layout

```
synth/                  the pipeline (parse, voice, rank, verify, stats)
.claude/skills/         archive-synthesis: the orchestrator
.claude/agents/         shortlist-reviewer, delta-reconstructor, section-extractor
templates/              note format, extraction sheet, profile
examples/sample-export/ synthetic export (tests/make_fixture.py builds it)
tests/                  one test per failure mode in METHOD.md
```

## License

MIT
