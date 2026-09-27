"""
The promote gate: the only way a note should reach your notes folder.

    python3 -m synth promote <staged-note.md>... [--replace] [--check]

Refuses a note unless:
  - every quote passes `synth verify` (or carries a bold label)
  - it has frontmatter with a `source:` key
  - it has a `*Sources:*` line citing at least one conversation, and every
    dated conversation it cites exists in the archive
  - no note with that name exists yet, unless --replace (for a merge you
    wrote in staging: current position on top, history below)

On success it copies the note into paths.notes and records the cited
conversations as pending promotions. They are not skipped yet: `synth ledger
sync`, run after each section read (stage 7), turns them into `promoted`
ledger entries once their shortlist row is ticked. A run that stops between the two leaves them in the next
export's shortlist and chunks instead of silently dropping them.

Why a script and not an instruction: in the reference run, the notes that
reached the folder with an assistant-written line in them had passed a
human-supervised process. A gate that cannot be skipped by a busy
orchestrator is the fix.
"""

import argparse
import io
import os
import re
import shutil
import sys

from . import config as cfgmod
from . import ledger, verify

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
SOURCES_LINE = re.compile(r"^\*?Sources?:\*?(.*)$", re.M | re.I)
DATED_STEM = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def problems(path, cfg, replace=False):
    """Return (list of reasons to refuse, cited conversation stems)."""
    out = []
    with io.open(path, encoding="utf-8") as fh:
        text = fh.read()

    fm = FRONTMATTER.match(text)
    if not fm:
        out.append("no frontmatter block")
    elif not re.search(r"(?m)^source:\s*\S", fm.group(1)):
        out.append("frontmatter has no `source:`")

    cited = []
    for line in SOURCES_LINE.findall(text):
        cited += [s for s in ledger.stems_in(line) if DATED_STEM.match(s)]
    conv_dir = os.path.join(cfg["paths"]["archive"], "conversations")
    missing = [s for s in cited if not os.path.exists(os.path.join(conv_dir, s + ".md"))]
    if not cited:
        out.append("no `*Sources:*` line citing a conversation")
    for s in missing:
        out.append(f"cites a conversation not in the archive: {s}")

    fails = verify.failures(verify.check(path, cfg))
    for r in fails:
        out.append(f"verify: {r['status']} at line {r['line']}: {r['quote'][:80]}"
                   + (f" ({r['detail']})" if r["detail"] else ""))

    target = os.path.join(cfg["paths"]["notes"], os.path.basename(path))
    if os.path.exists(target) and not replace:
        out.append(f"a note named {os.path.basename(path)} already exists. Merge "
                   "into the staged copy (current position on top, history "
                   "below), then promote with --replace")
    return out, [s for s in cited if s not in missing]


def run(cfg, files, replace=False, check_only=False):
    notes = cfg["paths"]["notes"]
    led = ledger.load(cfg)
    rows = {r["file"][:-3]: r for r in ledger.load_index(cfg)}
    refused = 0
    for f in files:
        reasons, cited = problems(f, cfg, replace)
        name = os.path.basename(f)
        if reasons:
            refused += 1
            print(f"REFUSED  {name}")
            for r in reasons:
                print(f"  - {r}")
            continue
        if check_only:
            print(f"ok       {name} (check only, not written)")
            continue
        os.makedirs(notes, exist_ok=True)
        shutil.copyfile(f, os.path.join(notes, name))
        for s in cited:
            if s in rows:
                ledger.pend(led, rows[s], name)
        print(f"promoted {name} -> {notes}  ({len(cited)} source conversations)")
    if not check_only:
        ledger.save(cfg, led)
    return 1 if refused else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="synth promote")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--config")
    ap.add_argument("--replace", action="store_true",
                    help="overwrite an existing note (after merging in staging)")
    ap.add_argument("--check", action="store_true",
                    help="run every check, write nothing")
    args = ap.parse_args(argv)
    raise SystemExit(run(cfgmod.load(args.config), args.files, args.replace, args.check))


if __name__ == "__main__":
    main()
