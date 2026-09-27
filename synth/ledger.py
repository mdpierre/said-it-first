"""
The ledger: which conversations you've already reviewed, across exports.

    python3 -m synth ledger sync      record every ticked [x] row in SHORTLIST.md
    python3 -m synth ledger mark <stem>... [--status reviewed|promoted]
    python3 -m synth ledger show

Every export contains your whole history again. Without a record of what you
already read, the second run's shortlist is mostly the first run's. `rank`
skips ledgered conversations by default, and brings one back (marked
"continued") if you added turns to it after you reviewed it.

`synth promote` does not write entries directly. It records the conversations
a promoted note cites under "pending". `sync` turns those into `promoted`
entries once their shortlist row is ticked (or if they are not on the
shortlist), so nothing is skipped before the section read has seen it.

Keyed by ChatGPT's conversation_id, which is stable across exports; file
names are not (a renamed conversation gets a new slug).
"""

import argparse
import datetime as dt
import io
import json
import os
import re
import sys

from . import config as cfgmod

STATUSES = ("reviewed", "promoted")   # promoted outranks reviewed
TICKED = re.compile(r"^\|\s*\[[xX]\]")
STEM = re.compile(r"\[\[([^\]|\\]+)|\]\(([^)]+?)\.md\)")


def path_of(cfg):
    return cfg["paths"]["ledger"]


def load(cfg):
    p = path_of(cfg)
    if not os.path.exists(p):
        return {"version": 1, "conversations": {}}
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def save(cfg, led):
    p = path_of(cfg)
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    tmp = p + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump(led, fh, indent=1, sort_keys=True)
    os.replace(tmp, p)


def key(row):
    return row.get("conversation_id") or row["file"]


CONV_ID = re.compile(r'(?m)^conversation_id:\s*"?([^"\n]+)"?\s*$')


def load_index(cfg):
    """index.json rows, with conversation_id filled in from each file's
    frontmatter when the index predates that field."""
    archive = cfg["paths"]["archive"]
    with io.open(os.path.join(archive, "index.json"), encoding="utf-8") as fh:
        rows = json.load(fh)
    for r in rows:
        if r.get("conversation_id"):
            continue
        p = os.path.join(archive, "conversations", r["file"])
        if os.path.exists(p):
            with io.open(p, encoding="utf-8") as fh:
                m = CONV_ID.search(fh.read(2000))
            if m:
                r["conversation_id"] = m.group(1).strip()
    return rows


def mark(led, row, status, today=None):
    """Record a row. Never downgrades promoted -> reviewed."""
    k = key(row)
    cur = led["conversations"].get(k)
    if cur and STATUSES.index(cur["status"]) > STATUSES.index(status):
        status = cur["status"]
    led["conversations"][k] = {
        "file": row["file"],
        "title": row["title"],
        "status": status,
        "date": (today or dt.date.today()).isoformat(),
        "user_turns": row["user_turns"],
    }


def pend(led, row, note):
    """Record that `note` cites this conversation. `sync` finalizes it."""
    rec = led.setdefault("pending", {}).setdefault(
        key(row), {"conversation_id": row.get("conversation_id"),
                   "file": row["file"], "title": row["title"],
                   "user_turns": row["user_turns"], "notes": []})
    if note not in rec["notes"]:
        rec["notes"].append(note)


def finalize(led, hold=(), today=None):
    """Move pending promotions into the ledger as `promoted`, except those
    whose file stem is in `hold` (on the shortlist, not ticked yet: the
    section read has not reached them). Returns how many moved."""
    pending = led.get("pending", {})
    done = [k for k, rec in pending.items() if rec["file"][:-3] not in hold]
    for k in done:
        mark(led, pending.pop(k), "promoted", today)
    if not pending:
        led.pop("pending", None)
    return len(done)


def state(led, row):
    """None (not reviewed), 'reviewed', or 'continued' (turns added since)."""
    rec = led["conversations"].get(key(row))
    if not rec:
        return None
    return "continued" if row["user_turns"] > rec["user_turns"] else "reviewed"


def stems_in(text):
    for m in STEM.finditer(text):
        s = (m.group(1) or os.path.basename(m.group(2) or "")).strip()
        if s:
            yield s


def sync(cfg, shortlist=None):
    shortlist = shortlist or cfg["paths"]["shortlist"]
    rows = load_index(cfg)
    by_stem = {r["file"][:-3]: r for r in rows}
    led = load(cfg)
    before = len(led["conversations"])
    ticked, unknown, unticked = 0, [], set()
    with io.open(shortlist, encoding="utf-8") as fh:
        for line in fh:
            if not TICKED.match(line):
                if line.startswith("|"):
                    unticked.update(stems_in(line))
                continue
            for s in stems_in(line):
                if s in by_stem:
                    mark(led, by_stem[s], "reviewed")
                    ticked += 1
                    break
            else:
                unknown.append(line.strip()[:90])
    promoted = finalize(led, hold=unticked)
    save(cfg, led)
    print(f"ticked rows  {ticked} recorded as reviewed")
    print(f"promotions   {promoted} cited conversations recorded as promoted"
          + (f", {len(led['pending'])} held until their shortlist row is ticked"
             if led.get("pending") else ""))
    print(f"ledger       {before} -> {len(led['conversations'])} conversations "
          f"({path_of(cfg)})")
    for u in unknown:
        print(f"  WARNING no conversation found for: {u}")
    return ticked


def mark_stems(cfg, stems, status):
    rows = {r["file"][:-3]: r for r in load_index(cfg)}
    led = load(cfg)
    missing = [s for s in stems if s not in rows]
    for s in stems:
        if s in rows:
            mark(led, rows[s], status)
    save(cfg, led)
    return missing


def show(cfg):
    led = load(cfg)
    rows = load_index(cfg)
    counts = {}
    for r in rows:
        st = state(led, r) or "unreviewed"
        counts[st] = counts.get(st, 0) + 1
    promoted = sum(1 for v in led["conversations"].values() if v["status"] == "promoted")
    print(f"ledger     {path_of(cfg)}")
    print(f"recorded   {len(led['conversations'])} ({promoted} promoted into notes)")
    if led.get("pending"):
        print(f"pending    {len(led['pending'])} cited by promoted notes, recorded "
              "at the next `synth ledger sync`")
    for k in ("unreviewed", "reviewed", "continued"):
        print(f"{k:<10} {counts.get(k, 0)} in the current archive")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="synth ledger")
    ap.add_argument("action", choices=["sync", "mark", "show"])
    ap.add_argument("stems", nargs="*")
    ap.add_argument("--config")
    ap.add_argument("--shortlist", help="shortlist to sync (default: paths.shortlist)")
    ap.add_argument("--status", choices=STATUSES, default="reviewed")
    args = ap.parse_args(argv)
    cfg = cfgmod.load(args.config)
    if args.action == "sync":
        sync(cfg, args.shortlist)
    elif args.action == "mark":
        missing = mark_stems(cfg, args.stems, args.status)
        for s in missing:
            print(f"WARNING not in index: {s}", file=sys.stderr)
        print(f"marked {len(args.stems) - len(missing)} as {args.status}")
    else:
        show(cfg)


if __name__ == "__main__":
    main()
