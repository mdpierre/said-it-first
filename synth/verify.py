"""
Stage 5: verify that every quotation in staged drafts is actually yours.

    python3 -m synth verify [--dir DIR]

A model drafting notes from a multi-year corpus has three ways to break
authorship, and none of them announce themselves in its own report:

  1. paraphrase presented inside quotation marks
  2. language the assistant coined that you then echoed back, quoted as yours
  3. silent typo/grammar normalization of your actual wording

Every quote of 40+ characters is checked against the voice corpus (your turns
only) and then against the full transcripts, to find lines the assistant said
first. Run it on every batch before review, and again on notes before they
are promoted. Exit code 1 if anything fails, so it can gate a script.

Files whose names start with `_` (reports, notes) are skipped.
"""

import argparse
import glob
import io
import os
import re
import unicodedata

from . import config as cfgmod

PAIRS = [re.compile(r'"([^"\n]{40,})"'), re.compile(r'“([^”\n]{40,})”')]
# Lines containing these are structure, not quotations.
SKIP = ("**", "[[", "source:", "Was:", "Now:", "Because:", "`")


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    for a, b in [("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), ("…", "...")]:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s.lower())).strip()


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def probe_of(q):
    """First contiguous run before any elision. That much must be verbatim."""
    return norm(re.split(r"\.\.\.", q)[0])[:60]


def speaker_turns(path):
    with io.open(path, encoding="utf-8") as fh:
        raw = fh.read()
    segs = re.split(r"(?m)^(## Me|### ChatGPT)$", raw)
    return [(segs[i], norm(segs[i + 1])) for i in range(1, len(segs) - 1, 2)]


def collect_quotes(target):
    quotes = []
    files = ([target] if os.path.isfile(target)
             else glob.glob(os.path.join(target, "**", "*.md"), recursive=True))
    for f in files:
        if os.path.basename(f).startswith("_"):
            continue
        txt = _read(f)
        for pat in PAIRS:
            for q in pat.findall(txt):
                if any(b in q for b in SKIP):
                    continue
                p = probe_of(q)
                if len(p) >= 30:
                    rel = os.path.relpath(f, target) if os.path.isdir(target) else f
                    quotes.append((rel, p, q))
    return quotes


def check(target, archive):
    voice_files = glob.glob(os.path.join(archive, "voice", "*.md"))
    if not voice_files:
        raise SystemExit(f"no voice corpus in {archive}/voice; run `synth voice` first")
    voice = norm("\n".join(_read(f) for f in voice_files))

    quotes = collect_quotes(target)
    unsourced = [(f, q) for f, p, q in quotes if p not in voice]

    echoed = []
    for path in glob.glob(os.path.join(archive, "conversations", "*.md")):
        turns = speaker_turns(path)
        if not turns:
            continue
        for f, p, q in quotes:
            me = gpt = None
            for i, (spk, body) in enumerate(turns):
                if p in body:
                    if spk == "## Me" and me is None:
                        me = i
                    elif spk == "### ChatGPT" and gpt is None:
                        gpt = i
            if me is not None and gpt is not None and gpt < me:
                echoed.append((f, os.path.basename(path), q))
    return quotes, unsourced, echoed


def run(cfg, target=None):
    target = target or cfg["paths"]["staging"]
    quotes, unsourced, echoed = check(target, cfg["paths"]["archive"])

    print(f"quotes checked               {len(quotes)}")
    print(f"not verbatim in your turns   {len(unsourced)}")
    print(f"assistant-coined, you echoed {len(echoed)}\n")
    for f, q in unsourced:
        print(f"  [unsourced] {f}\n    {q[:140]}\n")
    seen = set()
    for f, c, q in echoed:
        if q in seen:
            continue
        seen.add(q)
        print(f"  [echoed] {f} <- {c}\n    {q[:140]}\n")
    return 1 if (unsourced or echoed) else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="synth verify")
    ap.add_argument("--config")
    ap.add_argument("--dir", help="file or folder to check (default: paths.staging)")
    args = ap.parse_args(argv)
    raise SystemExit(run(cfgmod.load(args.config), args.dir))


if __name__ == "__main__":
    main()
