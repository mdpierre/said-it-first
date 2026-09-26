"""
Stage 2: build a "your turns only" corpus from the parsed archive.

    python3 -m synth voice

The assistant's side of a chat archive is most of its volume (about 83% in the
reference corpus) and it is exactly the material that must not end up in your
notes as if you said it. Stripping it makes the corpus small enough for one
long-context read, and makes it the *right* corpus at the same time.

Output:
  voice/<year>.md        everything, grouped by year, for humans and grep
  voice/chunks/          unreviewed conversations only, in chronological
                         chunks of <= voice.chunk_tokens, for chunk-readers
  voice/chunks/MANIFEST.md

Every conversation carries an anchor back to its full transcript.
"""

import argparse
import io
import json
import os
import shutil
from collections import defaultdict

from . import config as cfgmod
from . import ledger
from .parse import turns_from_markdown, WORD


def tokens(text):
    return len(text) // 4          # rough, and conservative for English


def write_chunks(out_dir, blocks, budget, owner_who):
    """
    Split chronological conversation blocks into files of at most `budget`
    tokens, never splitting a conversation. Readers take one chunk each, so
    an archive of any size is read by agents with ordinary context windows.
    """
    cdir = os.path.join(out_dir, "chunks")
    shutil.rmtree(cdir, ignore_errors=True)
    os.makedirs(cdir)
    chunks, cur, cur_tok = [], [], 0
    for b in blocks:
        t = tokens(b["text"])
        if cur and cur_tok + t > budget:
            chunks.append(cur)
            cur, cur_tok = [], 0
        cur.append(b)
        cur_tok += t
    if cur:
        chunks.append(cur)

    manifest = ["# Voice chunks", "",
                f"*Unreviewed conversations only, oldest first, <= ~{budget:,} "
                "tokens per chunk. One chunk-reader per chunk.*", "",
                "| Chunk | From | To | Conversations | ~Tokens |",
                "|---|---|---|---|---|"]
    oversized = 0
    for i, ch in enumerate(chunks, 1):
        name = f"chunk-{i:02d}.md"
        body = "".join(b["text"] for b in ch)
        tok = tokens(body)
        oversized += tok > budget
        with io.open(os.path.join(cdir, name), "w", encoding="utf-8") as fh:
            fh.write(f"# {owner_who} turns - chunk {i} of {len(chunks)} "
                     f"({ch[0]['date']} to {ch[-1]['date']})\n\n"
                     f"*{len(ch)} conversations, ~{tok:,} tokens.*\n" + body + "\n")
        manifest.append(f"| {name} | {ch[0]['date']} | {ch[-1]['date']} | "
                        f"{len(ch)} | {tok:,} |")
    with io.open(os.path.join(cdir, "MANIFEST.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(manifest) + "\n")
    return len(chunks), oversized


def run(cfg, min_words=None, chunk_tokens=None, include_reviewed=False):
    archive = cfg["paths"]["archive"]
    floor = cfg["parse"]["min_user_words"] if min_words is None else min_words
    style = cfg["output"]["link_style"]
    owner = cfg["owner"]

    with io.open(os.path.join(archive, "index.json"), encoding="utf-8") as fh:
        rows = json.load(fh)
    rows.sort(key=lambda r: r["date"])

    out_dir = os.path.join(archive, "voice")
    os.makedirs(out_dir, exist_ok=True)

    led = ledger.load(cfg)
    budget = chunk_tokens or cfg["voice"]["chunk_tokens"]
    by_year = defaultdict(list)
    chunk_blocks, reviewed = [], 0
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
        block = head + "\n---\n".join(turns)
        by_year[r["date"][:4]].append(block)
        if ledger.state(led, r) == "reviewed" and not include_reviewed:
            reviewed += 1
        else:
            chunk_text = block if style == "wikilink" else block.replace(
                "](../conversations/", "](../../conversations/", 1)
            chunk_blocks.append({"date": r["date"], "text": chunk_text})

    total = 0
    who = "Your" if owner.lower() == "you" else f"{owner}'s"
    for year, blocks in sorted(by_year.items()):
        p = os.path.join(out_dir, f"{year}.md")
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
    n, over = write_chunks(out_dir, chunk_blocks, budget, who)
    print(f"chunks {n} of <= ~{budget:,} tokens -> {out_dir}/chunks "
          f"({len(chunk_blocks)} unreviewed conversations, {reviewed} already "
          f"reviewed left out)")
    if over:
        print(f"WARNING  {over} chunk(s) exceed the budget: a single "
              f"conversation is larger than --chunk-tokens")
    # The check that would have caught the truncation bug on day one.
    if words_in and words_out < words_in * 0.98:
        print(f"WARNING  voice corpus has {words_out:,} words but index.json "
              f"counts {words_in:,} user words. Turns are being dropped.")
    return kept


def main(argv=None):
    ap = argparse.ArgumentParser(prog="synth voice")
    ap.add_argument("--config")
    ap.add_argument("--min-words", type=int)
    ap.add_argument("--chunk-tokens", type=int,
                    help="max tokens per reading chunk (default: voice.chunk_tokens)")
    ap.add_argument("--include-reviewed", action="store_true",
                    help="put already-reviewed conversations in the chunks too")
    args = ap.parse_args(argv)
    run(cfgmod.load(args.config), args.min_words, args.chunk_tokens,
        args.include_reviewed)


if __name__ == "__main__":
    main()
