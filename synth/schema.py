"""
Export format check: fail loudly when the export isn't the shape parse expects.

    python3 -m synth check <export>

`parse` runs this first. The export format is undocumented and changes. The
danger is not a crash, it's a quiet drop: a new content_type for user
messages would make parse skip that text and report a clean run with less of
you in it. So:

  errors (parse stops)   the file isn't a list of conversations; most
                         conversations have no `mapping`; no user message
                         with text anywhere
  warnings (parse runs)  a content_type or role this code doesn't know,
                         with a count and how many user words it holds;
                         malformed nodes; missing timestamps or current_node

Known types that are dropped on purpose are listed in EXPECTED_DROPS, so
they don't warn every run.
"""

import argparse
import sys
from collections import Counter

from . import config as cfgmod
from . import parse

# Seen in real exports and dropped deliberately.
EXPECTED_DROPS = {
    "thoughts",               # assistant reasoning trace
    "reasoning_recap",        # "Thought for 12s"
    "user_editable_context",  # custom instructions, not a turn
    "code",                   # tool-call payloads
    "execution_output",
    "tether_browsing_display",
    "tether_quote",
    "system_error",
    "sonic_webpage",
    "computer_output",
    "app_pairing_content",
}
KNOWN_ROLES = parse.KEEP_ROLES | {"system", "tool"}

# Share of conversations that may lack a mapping before we call it a format change.
MAX_BAD_SHARE = 0.10


def _words(parts):
    return sum(len(p.split()) for p in (parse.part_to_text(x) for x in parts) if p)


def validate(convos):
    """Return (errors, warnings, stats). Pure: reads, never writes."""
    errors, warnings = [], []
    stats = Counter()
    if not isinstance(convos, list):
        return ([f"export is a {type(convos).__name__}, expected a list of "
                 "conversations"], [], stats)

    unknown_types = Counter()      # (role, content_type) -> messages
    unknown_words = Counter()      # (role, content_type) -> words carried
    unknown_roles = Counter()
    for c in convos:
        stats["conversations"] += 1
        if not isinstance(c, dict):
            stats["not_a_dict"] += 1
            continue
        if not c:
            stats["empty_objects"] += 1
            continue
        mapping = c.get("mapping")
        if not isinstance(mapping, dict):
            stats["no_mapping"] += 1
            continue
        if not c.get("create_time"):
            stats["no_create_time"] += 1
        cur = c.get("current_node")
        if not cur or cur not in mapping:
            stats["no_current_node"] += 1
        for node in mapping.values():
            if not isinstance(node, dict):
                stats["bad_nodes"] += 1
                continue
            msg = node.get("message")
            if msg is None:
                continue
            if not isinstance(msg, dict):
                stats["bad_nodes"] += 1
                continue
            role = ((msg.get("author") or {}).get("role") or "").lower()
            if role not in KNOWN_ROLES:
                unknown_roles[role or "(none)"] += 1
            content = msg.get("content")
            if not isinstance(content, dict):
                stats["no_content"] += 1
                continue
            ctype = content.get("content_type") or "(none)"
            parts = content.get("parts")
            if parts is not None and not isinstance(parts, list):
                stats["bad_parts"] += 1
                parts = None
            if role not in parse.KEEP_ROLES:
                continue
            if ctype in parse.TEXT_TYPES:
                stats[f"{role}_messages"] += 1
                if role == "user" and _words(parts or []):
                    stats["user_messages_with_text"] += 1
            elif ctype not in EXPECTED_DROPS:
                unknown_types[(role, ctype)] += 1
                # Some types carry text outside `parts`.
                n = _words(parts or []) + len(str(content.get("text") or "").split())
                unknown_words[(role, ctype)] += n

    n = stats["conversations"]
    bad = stats["no_mapping"] + stats["not_a_dict"]
    if n == 0:
        errors.append("export contains no conversations")
    elif bad > max(1, n * MAX_BAD_SHARE):
        errors.append(f"{bad} of {n} conversations have no `mapping` object. The "
                      "export format has probably changed; parse would drop them")
    elif stats["user_messages_with_text"] == 0:
        errors.append("no user message with text found anywhere. The content "
                      "format has probably changed")

    for (role, ctype), k in unknown_types.most_common():
        w = unknown_words[(role, ctype)]
        loud = role == "user" and w
        warnings.append(
            f"{'USER TEXT DROPPED: ' if loud else ''}{k} {role} messages with "
            f"unknown content_type '{ctype}' ({w:,} words) are skipped. If this "
            "is conversation text, add it to TEXT_TYPES in synth/parse.py; if "
            "not, to EXPECTED_DROPS in synth/schema.py")
    for role, k in unknown_roles.most_common():
        warnings.append(f"{k} messages with unknown role '{role}' are skipped")
    if bad:
        warnings.append(f"{bad} conversations have no mapping and are skipped")
    for key, what in (("bad_nodes", "malformed nodes"),
                      ("bad_parts", "messages whose parts aren't a list"),
                      ("no_content", "messages with no content object"),
                      ("no_create_time", "conversations with no create_time "
                       "(dated 0000-00-00)"),
                      ("no_current_node", "conversations with no valid current_node "
                       "(parse falls back to the last leaf)")):
        if stats[key]:
            warnings.append(f"{stats[key]} {what}")
    return errors, warnings, stats


def report(errors, warnings, stats, out=None):
    out = out or sys.stdout
    print(f"format   {stats['conversations']} conversations, "
          f"{stats['user_messages']:,} user / {stats['assistant_messages']:,} "
          f"assistant text messages"
          + (f", {stats['empty_objects']} empty" if stats["empty_objects"] else ""),
          file=out)
    for w in warnings:
        print(f"WARNING  {w}", file=out)
    for e in errors:
        print(f"ERROR    {e}", file=out)


def check(convos, strict=False):
    """Validate, print, and exit on errors (or on warnings when strict)."""
    errors, warnings, stats = validate(convos)
    report(errors, warnings, stats)
    if errors or (strict and warnings):
        sys.exit("Export format check failed. Nothing was written. "
                 "(--skip-check to parse anyway)")
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(prog="synth check")
    ap.add_argument("export")
    ap.add_argument("--config")
    ap.add_argument("--strict", action="store_true", help="fail on warnings too")
    args = ap.parse_args(argv)
    cfgmod.load(args.config)
    errors, warnings, stats = validate(parse.load_conversations(args.export))
    report(errors, warnings, stats)
    raise SystemExit(1 if errors or (args.strict and warnings) else 0)


if __name__ == "__main__":
    main()
