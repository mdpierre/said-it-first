"""
Stage 3: score parsed conversations and write a review shortlist.

    python3 -m synth rank [--top N] [--force]

The gate is not "is this relevant". Nearly everything is relevant to
something. The gate is "did this conversation change what I think, or is it
just a conversation I had?"

Signals (all computed on AUTHORED words, never raw user words):

  authored_words       your own words only; pastes, quiz picks and clicked
                       follow-up chips are excluded at parse time
  own_voice_words      dictated voice memos you pasted in. Weighted UP. They
                       look identical to a third-party paste by length.
  max_user_turn_words  one long turn beats many short ones
  content_days         days you actually wrote something, not days you pinged
                       a standing-instruction thread
  code_ratio           penalised; code sessions are work product, not belief
  consumption skew     penalised; lots of output, few of your words = reading
  coursework           penalised, and turn depth / return visits are zeroed:
                       one exam question per message is not depth

This is TRIAGE. It gets a thousand-plus conversations down to a few hundred.
Always follow it with a reading pass (the shortlist-reviewer agent).
"""

import argparse
import datetime as dt
import io
import json
import math
import os
import re
import sys

from . import config as cfgmod
from . import parse

# Fields parse adds that the score depends on.
NEW_FIELDS = ("authored_words", "own_voice_words", "max_user_turn_words",
              "content_days", "coursework", "terms")


def score(row, cfg):
    w = cfg["rank"]["weights"]
    p = cfg["rank"]["penalties"]
    aw = row["authored_words"]
    ow = row["own_voice_words"]
    asst = row["assistant_words"]
    coursework = bool(row.get("coursework"))

    s = 0.0
    s += w["authored_words"] * math.log1p(aw)
    s += w["own_voice"] * math.log1p(ow)
    s += w["longest_turn"] * math.log1p(row["max_user_turn_words"])

    if not coursework:
        s += w["turn_depth"] * math.log1p(row.get("authored_turns", 0))
        s += w["turn_length"] * math.log1p(row.get("avg_authored_turn_words", 0))

        days = row.get("content_days")
        if days is None:
            # Rescanned index with no timestamps: fall back to a ratio gate.
            days = row["days_touched"]
            if aw / max(row["days_touched"], 1) < w["routine_min_wpd"]:
                days = 1
        s += w["return_visit"] * min(max(days - 1, 0), w["return_cap"])

        # Many days, few words per day: a standing-instruction thread, not a
        # thought you kept returning to.
        if row["days_touched"] >= 3 and aw / row["days_touched"] < w["routine_min_wpd"]:
            s -= p["routine"] * math.log1p(row["days_touched"])

    s -= p["code"] * row["code_ratio"]
    if coursework:
        s -= p["coursework"]

    if aw > 0:
        skew = asst / aw
        if skew > 6 and row.get("avg_authored_turn_words", 0) < 40:
            s -= p["consumption"] * math.log1p(skew - 6)
    return round(s, 2)


def compile_topics(cfg):
    out = []
    for name, spec in cfg["topics"].items():
        if isinstance(spec, str):
            spec = {"pattern": spec}
        pats = [spec["pattern"]] if "pattern" in spec else list(spec.get("all_of", []))
        out.append((name, [re.compile(x, re.I) for x in pats],
                    set(spec.get("replaces", []))))
    return out


def topics_for(row, topics, min_hits):
    """
    Route on the title plus the body term bag, not the title alone.

    A topic needs `min_hits` distinct matching terms (per pattern, for
    all_of topics). One stray word in a 4,000-word memo is not what the
    conversation is about, and a one-hit rule hands long conversations most
    of the topic list, which fires the delta flag on everything.
    """
    text = (row.get("title") or "").lower()
    if row.get("terms"):
        text += " " + " ".join(row["terms"])
    found, drop = [], set()
    for name, pats, replaces in topics:
        if all(len({m if isinstance(m, str) else m[0] for m in pat.findall(text)})
               >= min_hits for pat in pats):
            found.append(name)
            drop |= replaces
    return [t for t in found if t not in drop]


def delta_candidate(row, age_days, cfg):
    """
    A delta candidate predates a dated position change in a topic it actually
    discusses. Volatile topics with no dated change fall back to staleness.
    """
    topics = set(row["topics"])
    changes = cfg["position_changes"]
    for c in changes:
        if c["topic"] in topics and row["date"] < c["date"]:
            return True
    landmarked = {c["topic"] for c in changes}
    return (age_days > cfg["rank"]["stale_after_days"]
            and bool((topics & set(cfg["volatile"])) - landmarked))


def rescan(rows, archive_dir):
    """
    Recompute authorship signals from conversations/*.md. Recovers everything
    except content_days, which needs per-turn timestamps only the export has.
    """
    conv_dir = os.path.join(archive_dir, "conversations")
    done = 0
    for row in rows:
        path = os.path.join(conv_dir, row["file"])
        if not os.path.exists(path):
            continue
        texts = parse.turns_from_markdown(path)
        auth = parse.authorship(texts)
        row["authored_words"] = auth["authored_words"]
        row["own_voice_words"] = auth["own_voice_words"]
        row["pasted_words"] = auth["pasted_words"]
        row["authored_turns"] = auth["authored_turns"]
        row["max_user_turn_words"] = auth["max_user_turn_words"]
        row["avg_authored_turn_words"] = (
            round(auth["authored_words"] / auth["authored_turns"], 1)
            if auth["authored_turns"] else 0)
        row["coursework"] = parse.is_coursework(texts)
        row["terms"] = parse.term_bag(
            [t for t, (lab, _) in zip(texts, auth["labels"])
             if lab in ("authored", "own_voice")])
        row.pop("content_days", None)
        done += 1
    parse.mark_branch_duplicates(rows)
    return done


def score_all(rows, cfg, today=None):
    topics = compile_topics(cfg)
    min_hits = cfg["rank"]["min_term_hits"]
    today = today or dt.date.today()
    for r in rows:
        r["topics"] = topics_for(r, topics, min_hits)
        try:
            age = (today - dt.date(*map(int, r["date"].split("-")))).days
        except (ValueError, TypeError):
            age = 0
        r["age_days"] = age
        r["delta_candidate"] = delta_candidate(r, age, cfg)
        r["score"] = score(r, cfg)
    scored = [r for r in rows if not r.get("branch_dup")]
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored


def render(scored, cfg, top_n, total_rows):
    style = cfg["output"]["link_style"]
    shortlist_dir = os.path.dirname(cfg["paths"]["shortlist"])
    rel = os.path.relpath(os.path.join(cfg["paths"]["archive"], "conversations"),
                          shortlist_dir) + "/"

    def ln(r, n):
        return cfgmod.link(r["file"][:-3], r["title"][:n], rel, style)

    top = scored[:top_n]
    lines = [
        "# Review Shortlist",
        "",
        f"*Generated {dt.date.today().isoformat()} from {total_rows} conversations "
        f"({total_rows - len(scored)} branch duplicates dropped). "
        "Ranked on the proxy: did this change what I think?*",
        "",
        "**Columns.** `My words` counts authored words only: pastes, quiz picks "
        "and clicked follow-up chips are excluded. `Voice` is dictated memo "
        "text, which is weighted up. `Longest` is the longest authored turn. "
        "`D` = delta candidate: predates a known position change in a topic it "
        "discusses. Route to notes as the *was* half of a change; keep it out "
        "of any current-context file.",
        "",
        "This is a triage list to read from, not a shortlist to ship. "
        "Authorship is detected mechanically and paste shapes vary too much "
        "for that to be complete.",
        "",
        "| OK | Score | Date | D | My words | Voice | Longest | Turns | Days | Topics | Title |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in top:
        warn = "D" if r["delta_candidate"] else ""
        topics = ", ".join(r["topics"]) or "-"
        if r.get("coursework"):
            topics = (topics + " *(coursework)*").strip()
        lines.append(
            f"| [ ] | {r['score']} | {r['date']} | {warn} | "
            f"{r['authored_words']} | {r['own_voice_words'] or ''} | "
            f"{r['max_user_turn_words']} | {r.get('authored_turns', 0)} | "
            f"{r['days_touched']} | {topics} | {ln(r, 70)} |")

    # Delta candidates are listed corpus-wide, not only where they land in the
    # top N. A delta is a routing decision, not a quality ranking: the threads
    # that most need flagging are often short.
    in_top = {r["file"] for r in top}
    all_deltas = [r for r in scored if r["delta_candidate"]]
    deltas_in_top = [r for r in top if r["delta_candidate"]]
    lines += [
        "", "---", "",
        "## Delta candidates",
        "",
        f"**{len(all_deltas)} in the corpus, {len(deltas_in_top)} of them in the "
        f"top {len(top)}.** Highest-value material for a record of how your "
        "thinking changed; lowest-value material for an AI's picture of who "
        "you are now. Same conversation, routed two ways.",
        "",
        "Do not discard an idea because you no longer believe it. The abandoned "
        "positions are what make the evolution legible.",
        "",
    ]
    if cfg["position_changes"]:
        lines += ["Known position changes (the *now* side is already known, so "
                  "finding the *was* side mostly completes the delta):", ""]
        for c in cfg["position_changes"]:
            lines.append(f"- **{c['date']}** `{c['topic']}` - {c.get('what', '')}")
    else:
        lines += ["*No `position_changes` in your config yet, so deltas are "
                  "flagged only by staleness in `volatile` topics. Add dated "
                  "changes to make this section useful.*"]

    delta_top = all_deltas[: max(top_n // 2, 20)]
    lines += [
        "",
        f"Highest-scoring {len(delta_top)} delta candidates. `*` = already in "
        "the table above.",
        "",
        "| OK | Score | Date | My words | Volatile topic | Title |",
        "|---|---|---|---|---|---|",
    ]
    vol = set(cfg["volatile"]) | {c["topic"] for c in cfg["position_changes"]}
    for r in delta_top:
        mark = "*" if r["file"] in in_top else ""
        dom = ", ".join(t for t in r["topics"] if t in vol) or "-"
        lines.append(f"| [ ]{mark} | {r['score']} | {r['date']} | "
                     f"{r['authored_words']} | {dom} | {ln(r, 60)} |")

    lines += [
        "", "---", "",
        "## Triage notes",
        "",
        "- Tick OK on anything worth extracting. Nothing enters your notes "
        "without a tick.",
        "- Extraction rule: the idea must be yours; the sentence need not be. "
        "Quote verbatim where the wording is yours; tag "
        "`source: chatgpt-synthesis` where it isn't.",
        "- Delta rows: write as **Was / Now / Because** with a dated source "
        "anchor and `stability: provisional`.",
        "- Your corrections to a draft are worth more than the draft. Skim and "
        "correct; never rubber-stamp.",
    ]
    return "\n".join(lines) + "\n", len(top), len(deltas_in_top)


def run(cfg, top_n=None, out=None, force=False, do_rescan=False):
    parse.configure(cfg)
    index_path = os.path.join(cfg["paths"]["archive"], "index.json")
    out = out or cfg["paths"]["shortlist"]
    top_n = top_n or cfg["rank"]["top"]

    with io.open(index_path, encoding="utf-8") as fh:
        rows = json.load(fh)

    stale = [f for f in NEW_FIELDS if rows and f not in rows[0]]
    if do_rescan or stale:
        if stale and not do_rescan:
            print(f"index.json is missing {', '.join(stale)}; rescanning "
                  f"conversations/. Re-run parse to persist them.")
        n = rescan(rows, cfg["paths"]["archive"])
        print(f"rescanned {n} conversations")
        if n == 0:
            sys.exit("no conversation files found; re-run parse")

    scored = score_all(rows, cfg)
    text, n_top, n_delta = render(scored, cfg, top_n, len(rows))

    if os.path.exists(out) and not force:
        sys.exit(f"{out} already exists and may be mid-review. "
                 f"Pass --force to overwrite, or --out to write elsewhere.")
    if os.path.dirname(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as fh:
        fh.write(text)

    course = sum(1 for r in scored if r.get("coursework"))
    print(f"scored    {len(scored)} conversations ({course} coursework, "
          f"{len(rows) - len(scored)} branch duplicates dropped)")
    print(f"shortlist {out} (top {n_top}, {n_delta} delta candidates in it)")
    return scored


def main(argv=None):
    ap = argparse.ArgumentParser(prog="synth rank")
    ap.add_argument("--config")
    ap.add_argument("--top", type=int)
    ap.add_argument("--out", help="override paths.shortlist")
    ap.add_argument("--rescan", action="store_true",
                    help="recompute authorship from conversations/*.md")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing shortlist")
    args = ap.parse_args(argv)
    run(cfgmod.load(args.config), args.top, args.out, args.force, args.rescan)


if __name__ == "__main__":
    main()
