# CLAUDE.md - chat-synthesis

A pipeline that turns a ChatGPT export into verified, human-approved notes.
Read `METHOD.md` before changing anything in `synth/`: most thresholds exist
because of a specific failure on a real archive.

## Running

- Full pipeline: the `archive-synthesis` skill. Start there for any user
  request about processing an archive.
- Scripts: `python3 -m synth <parse|voice|rank|verify|stats|run|paths>`,
  all taking `--config`.
- Tests: `python3 -m unittest discover tests`. Run after any change to `synth/`.

## Rules

- Python 3.11+, **stdlib only**. No dependencies.
- Personal values (topics, dates, platform names, weights) go in the user's
  `chat-synthesis.toml`, never in code. Code holds only what's true for any
  archive.
- **Never commit real archive data.** `workspace/`, `chat-synthesis.toml`,
  and `profile.md` are gitignored; tests use the synthetic fixture only. If you
  add a test case, add an invented conversation to `tests/make_fixture.py`.
- A new failure mode found on a real archive gets: a fix, a fixture
  conversation, a test, and a section in METHOD.md.
- Nothing is written to the user's notes folder without their explicit
  approval of that content. Staging is for drafts.
