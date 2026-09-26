"""
Stage 2: build a "your turns only" corpus from the parsed archive.

    python3 -m synth voice

The assistant's side of a chat archive is most of its volume (about 83% in the
reference corpus) and it is exactly the material that must not end up in your
notes as if you said it. Stripping it makes the corpus small enough for one
long-context read, and makes it the *right* corpus at the same time.

Output is grouped by year with a per-conversation anchor, so anything found
here traces back to the full transcript in conversations/.
"""

import argparse
import io
import json
import os
from collections import defaultdict

from . import config as cfgmod
from .parse import turns_from_markdown, WORD


def run(cfg, min_words=None):
    archive = cfg["paths"]["archive"]
    floor = cfg["parse"]["min_user_words"] if min_words is None else min_words
    style = cfg["output"]["link_style"]
    owner = cfg["owner"]

    with io.open(os.path.join(archive, "index.json"), encoding="utf-8") as fh:
        rows = json.load(fh)
    rows.sort(key=lambda r: r["date"])

    out_dir = os.path.join(archive, "voice")
    os.makedirs(out_dir, exist_ok=True)

    by_year = defaultdict(list)
    kept, words_in, words_out = 0, 0, 0
    for r in rows:
        if r["user_words"] < floor:
            continue
        path = os.path.join(archive, "conversations", r["file"])
        if not os.path.exists(path):
            continue
        turns = turns_from_markdown(path)
        if not turns:
            continue
        kept += 1
        words_in += r["user_words"]
        words_out += sum(len(WORD.findall(t)) for t in turns)
        stem = r["file"][:-3]
        anchor = (f"[[{stem}]]" if style == "wikilink"
                  else f"[{stem}](../conversations/{stem}.md)")
        head = (f"\n\n## {anchor} - {r['title']}\n"
                f"*{r['date']} · {r['user_words']}w · {r['user_turns']} turns · "
                f"{r['days_touched']} days*\n")
        by_year[r["date"][:4]].append(head + "\n---\n".join(turns))

    total = 0
    for year, blocks in sorted(by_year.items()):
        p = os.path.join(out_dir, f"{year}.md")
        who = "Your" if owner.lower() == "you" else f"{owner}'s"
        text = (f"# {who} turns - {year}\n\n"
                f"*{len(blocks)} conversations. User turns only; the assistant's "
                f"replies are stripped. Anchors link to the full transcript.*\n"
                + "".join(blocks) + "\n")
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        total += len(text)
        print(f"{year}  {len(blocks):>4} convos  {len(text):>9,} chars  ~{len(text)//4:>7,} tok")

    print(f"\nkept {kept} conversations -> {out_dir}")
    print(f"total {total:,} chars  ~{total//4:,} tokens")
    # The check that would have caught the truncation bug on day one.
    if words_in and words_out < words_in * 0.98:
        print(f"WARNING  voice corpus has {words_out:,} words but index.json "
              f"counts {words_in:,} user words. Turns are being dropped.")
    return kept


def main(argv=None):
    ap = argparse.ArgumentParser(prog="synth voice")
    ap.add_argument("--config")
    ap.add_argument("--min-words", type=int)
    args = ap.parse_args(argv)
    run(cfgmod.load(args.config), args.min_words)


if __name__ == "__main__":
    main()
