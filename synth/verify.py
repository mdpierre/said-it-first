"""
Stage 5: verify that every quotation in staged drafts is actually yours.

    python3 -m synth verify [--dir FILE_OR_DIR]

A model drafting notes from a multi-year corpus breaks authorship in ways
that never show up in its own report. Every quote of 40+ characters is
checked against the full transcripts:

  unsourced     not verbatim in any of your turns: paraphrase in quotation
                marks, silent cleanup of your wording, or a line the
                assistant said that you never did
  echoed        a run of 7+ words the assistant said earlier in the same
                conversation, anywhere in the quote. "Yes exactly, <their
                phrase>" is still their phrase.
  not authored  verbatim in one of your turns, but a turn the parser
                classified as pasted text, a quiz answer, or a clicked
                follow-up chip: someone else's words in your message

A quote can be kept deliberately by labeling it on the same line, up to
three lines before it, or on the line right after: `assistant-coined` / `echoed` for echoes, `cleaned` /
`paraphrase` for reworded quotes, `pasted` / `chip` for not-authored ones.
Labels count only in bold (`**cleaned**`); `**unverifiable**` accepts any
status. Labeled quotes are listed but do not fail.

LIMITS: only quotes of 40+ characters are checked, so short quotes need a
hand check. A quote whose assistant context is missing from the export
passes as ok; label it `**unverifiable**` yourself. Anything unlabeled fails with
exit code 1, so verify can gate a script.

Files whose names start with `_` (reports, notes) are skipped.
"""

import argparse
import glob
import io
import os
import re

from . import config as cfgmod
from . import parse

# A straight-quoted span must open after whitespace/start and close before
# whitespace/punctuation, so `said "yes" and "no ..."` doesn't pair the
# inner quotes across the prose between them.
QUOTE_PATTERNS = [
    re.compile(r'(?:^|(?<=[\s(>\[*_]))"(?=\S)([^"\n]{40,}?)(?<=\S)"(?=[\s.,;:!?)\]*_]|$)'),
    re.compile(r'“([^”\n]{40,})”'),
]
# Quote content that is structure or code, not a quotation.
SKIP = ("[[", "source:", "`")
# Labels only count in their bold form, e.g. **assistant-coined, echoed**.
# Plain words ("none cleaned", "he pasted it") must not pass a quote.
def _bold(words):
    return re.compile(r"\*\*[^*\n]*\b(" + words + r")\b[^*\n]*\*\*", re.I)


UNVERIFIABLE = _bold(r"unverifiable")
LABELS = {
    "echoed": _bold(r"assistant[- ]coined|echoed"),
    "unsourced": _bold(r"cleaned|paraphrase"),
    "not_authored": _bold(r"pasted|chip|clicked"),
}
ECHO_NGRAM = 7          # shared words that count as the assistant's phrasing
MIN_SEGMENT = 20        # chars; shorter elision fragments are not checked
MINE = ("authored", "own_voice")


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


norm = parse.norm


def segments(q):
    """Split on elisions; each surviving piece must be verbatim."""
    parts = [norm(p) for p in re.split(r"\.\.\.|…|\[\.\.\.\]", q)]
    return [p for p in parts if len(p) >= MIN_SEGMENT] or [norm(q)]


def ngrams(text, n=ECHO_NGRAM):
    return parse.ngrams(text, n)


def load_turns(archive):
    """[(conversation file, [(speaker, label, normalized text), ...]), ...]"""
    convos = []
    for path in sorted(glob.glob(os.path.join(archive, "conversations", "*.md"))):
        body = parse.FRONTMATTER.sub("", _read(path))
        segs = re.split(r"(?m)^(## Me|### ChatGPT)$", body)
        turns = []
        for i in range(1, len(segs) - 1, 2):
            raw = segs[i + 1].strip()
            if segs[i] == "## Me":
                turns.append(("me", parse.classify_turn(raw), norm(raw)))
            else:
                turns.append(("assistant", None, norm(raw)))
        convos.append((os.path.basename(path), turns))
    return convos


def collect_quotes(target):
    """[(file, line number, quote, label-context), ...]"""
    files = ([target] if os.path.isfile(target)
             else sorted(glob.glob(os.path.join(target, "**", "*.md"), recursive=True)))
    out = []
    for f in files:
        if os.path.basename(f).startswith("_"):
            continue
        lines = _read(f).split("\n")
        rel = os.path.relpath(f, target) if os.path.isdir(target) else f
        for i, line in enumerate(lines):
            # a label may sit on the quote's line, up to 3 lines before it
            # (a lead-in sentence, then a blank line), or on the line after
            context = " ".join(lines[max(i - 3, 0):i + 2])
            for pat in QUOTE_PATTERNS:
                for q in pat.findall(line):
                    q = q.replace("**", "")
                    if any(b in q for b in SKIP) or len(norm(q)) < 30:
                        continue
                    out.append((rel, i + 1, q, context))
    return out


def check_quote(q, convos):
    """Return (status, detail): ok | unsourced | echoed | not_authored."""
    segs = segments(q)
    qgrams = ngrams(norm(q))
    hits, in_assistant = [], None
    for fname, turns in convos:
        for idx, (spk, label, text) in enumerate(turns):
            if all(s in text for s in segs):
                if spk == "me":
                    hits.append((fname, turns, idx, label))
                elif in_assistant is None:
                    in_assistant = fname
    if not hits:
        detail = f"said by the assistant in {in_assistant}" if in_assistant else ""
        return "unsourced", detail
    authored = [h for h in hits if h[3] in MINE]
    if not authored:
        return "not_authored", f"{hits[0][3]} turn in {hits[0][0]}"
    # Echoed only if EVERY place you said it was preceded by the assistant
    # saying it. If you said it first anywhere, it is yours, even when the
    # assistant later quoted it back and you repeated it.
    echo = None
    for fname, turns, idx, _ in authored:
        shared = set()
        for spk, _, text in turns[:idx]:
            if spk == "assistant":
                shared |= qgrams & ngrams(text)
        if not shared:
            return "ok", ""
        echo = echo or f"{fname}: \"...{sorted(shared)[0]}...\""
    return "echoed", echo


def check(target, cfg):
    parse.configure(cfg)
    archive = cfg["paths"]["archive"]
    if not glob.glob(os.path.join(archive, "conversations", "*.md")):
        raise SystemExit(f"no conversations in {archive}; run `synth parse` first")
    convos = load_turns(archive)
    results = []
    for f, ln, q, ctx in collect_quotes(target):
        status, detail = check_quote(q, convos)
        labeled = status != "ok" and bool(LABELS[status].search(ctx)
                                          or UNVERIFIABLE.search(ctx))
        results.append({"file": f, "line": ln, "quote": q, "status": status,
                        "detail": detail, "labeled": labeled})
    return results


def failures(results):
    return [r for r in results if r["status"] != "ok" and not r["labeled"]]


def run(cfg, target=None):
    target = target or cfg["paths"]["staging"]
    results = check(target, cfg)
    fails = failures(results)
    count = lambda s, lab: sum(1 for r in results if r["status"] == s and r["labeled"] == lab)

    print(f"quotes checked                {len(results)}")
    print(f"not verbatim in your turns    {count('unsourced', False)}")
    print(f"assistant's phrasing echoed   {count('echoed', False)}")
    print(f"pasted / clicked, not yours   {count('not_authored', False)}")
    labeled = [r for r in results if r["labeled"]]
    print(f"labeled, kept deliberately    {len(labeled)}\n")
    for r in fails + labeled:
        tag = r["status"] + (" (labeled)" if r["labeled"] else "")
        print(f"  [{tag}] {r['file']}:{r['line']}\n    {r['quote'][:140]}")
        if r["detail"]:
            print(f"    -> {r['detail']}")
        print()
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="synth verify")
    ap.add_argument("--config")
    ap.add_argument("--dir", help="file or folder to check (default: paths.staging)")
    args = ap.parse_args(argv)
    raise SystemExit(run(cfgmod.load(args.config), args.dir))


if __name__ == "__main__":
    main()
