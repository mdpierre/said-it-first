"""
Stage 1: parse a ChatGPT data export into linearized markdown + a metrics index.

    python3 -m synth parse <export.zip | conversations.json | export-dir>

Writes:
    <archive>/conversations/<date>-<slug>.md   one file per conversation (active branch)
    <archive>/index.json                       metrics for every conversation, for scoring

The important part is not the linearizing, it is the per-turn authorship
classification. See METHOD.md, "A third of your words aren't yours".
"""

import argparse
import datetime as dt
import glob
import io
import json
import os
import re
import sys
import unicodedata
import zipfile

from . import config as cfgmod

# Timezone used to turn timestamps into calendar dates. None = this machine's
# local zone. Set `timezone` under [parse] for reproducible dates.
TZ = None


def day(ts):
    return dt.datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%d")

# Roles we keep in the transcript. Everything else (system, tool, browsing) is dropped.
KEEP_ROLES = {"user", "assistant"}

# content_types that carry real conversational text. Reasoning traces and tool
# scaffolding are excluded: they inflate word counts without being your thinking.
TEXT_TYPES = {"text", "multimodal_text"}


def _shard_key(name):
    """Sort conversations-007.json before conversations-010.json."""
    m = re.search(r"(\d+)", os.path.basename(name))
    return int(m.group(1)) if m else 0


def load_conversations(path):
    """
    Accept a .zip, a conversations.json, or a directory.

    Large exports ship sharded (conversations-000.json through
    conversations-NNN.json) with no single conversations.json. Shards are
    concatenated in numeric order. A loader that only looks for
    conversations.json finds nothing and fails quietly.
    """
    if os.path.isdir(path):
        single = os.path.join(path, "conversations.json")
        if os.path.exists(single):
            path = single
        else:
            shards = sorted(glob.glob(os.path.join(path, "conversations-*.json")),
                            key=_shard_key)
            if not shards:
                sys.exit(f"No conversations.json or conversations-*.json in {path}")
            convos = []
            for s in shards:
                with io.open(s, encoding="utf-8") as fh:
                    convos.extend(json.load(fh))
            print(f"loaded   {len(convos)} conversations from {len(shards)} shards")
            return convos
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist()
                     if re.search(r"conversations(-\d+)?\.json$", n)]
            if not names:
                sys.exit("No conversations.json inside the zip.")
            exact = [n for n in names if n.endswith("conversations.json")]
            if exact:
                with z.open(exact[0]) as fh:
                    return json.load(io.TextIOWrapper(fh, encoding="utf-8"))
            convos = []
            for n in sorted(names, key=_shard_key):
                with z.open(n) as fh:
                    convos.extend(json.load(io.TextIOWrapper(fh, encoding="utf-8")))
            print(f"loaded   {len(convos)} conversations from {len(names)} shards")
            return convos
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def part_to_text(part):
    """A content part is usually a string; multimodal parts are dicts."""
    if isinstance(part, str):
        return part
    if isinstance(part, dict):
        # image/audio pointers carry no text worth keeping
        return part.get("text") or ""
    return ""


def message_text(msg):
    content = msg.get("content") or {}
    if content.get("content_type") not in TEXT_TYPES:
        return ""
    parts = content.get("parts") or []
    return "\n".join(p for p in (part_to_text(x) for x in parts) if p).strip()


def is_hidden(msg):
    meta = msg.get("metadata") or {}
    return bool(meta.get("is_visually_hidden_from_conversation"))


def linearize(convo):
    """
    Walk from current_node up through parents to the root, then reverse.

    This follows the *active* branch only. Abandoned edits and regenerated
    replies are excluded: it is the conversation as it actually stood, not
    every path explored.
    """
    mapping = convo.get("mapping") or {}
    node_id = convo.get("current_node")

    # Some exports omit current_node; fall back to the deepest leaf.
    if not node_id or node_id not in mapping:
        leaves = [k for k, v in mapping.items() if not (v.get("children") or [])]
        node_id = leaves[-1] if leaves else None

    chain = []
    seen = set()
    while node_id and node_id in mapping and node_id not in seen:
        seen.add(node_id)
        chain.append(mapping[node_id])
        node_id = mapping[node_id].get("parent")
    chain.reverse()

    out = []
    for node in chain:
        msg = node.get("message")
        if not msg or is_hidden(msg):
            continue
        role = ((msg.get("author") or {}).get("role") or "").lower()
        if role not in KEEP_ROLES:
            continue
        text = message_text(msg)
        if not text:
            continue
        out.append({"role": role, "text": text, "time": msg.get("create_time")})
    return out


CODE_FENCE = re.compile(r"```.*?```", re.S)
WORD = re.compile(r"\b[\w'-]+\b")

# --- authorship classification ---------------------------------------------
#
# Counting every word inside a user turn is not a count of what the user
# wrote. Long turns are two opposite things a word counter cannot tell apart:
#
#   third-party paste  a video transcript, a course page, a job posting,
#                      a follower export. Worth nothing.
#   own-voice paste    a voice memo you dictated and pasted in for synthesis.
#                      The most valuable material in the archive.
#
# So each user turn is classified and the classes are counted separately,
# instead of penalising length. A length penalty would delete exactly what the
# pipeline exists to collect.
#
# LIMIT: this is triage, not attribution. Paste shapes vary too much for a
# regex to catch all of them (song lyrics, a friend's text, a syllabus all
# look nothing alike). Anything reaching your notes still needs a reading
# pass. The honest upgrade is a cheap per-turn model classification pass.

LONG_TURN_WORDS = 300     # below this, a paste cannot move the score much

# First-person and spoken-filler density (per 100 words) separate your own
# text from a pasted document. Calibrated on one ~1,600-conversation English
# corpus: own dictation ran 10-15 first-person / 10-18 filler, own typed
# reflection 10-15 / 1-3, someone else's spoken transcript 1-4 / 5-8, a pasted
# document 0-1 / 0-1. Re-check AUTHORED_FLOOR against your own archive
# (`python3 -m synth stats`) before trusting it.
FIRST_PERSON = re.compile(
    r"\b(i|i'm|im|i've|ive|i'd|i'll|my|me|myself|mine)\b", re.I)
SPOKEN_FILLER = re.compile(
    r"\b(like|yeah|yep|um|uh|okay|ok|you know|i mean|kinda|kind of|sorta|"
    r"sort of|gonna|wanna|cuz|honestly|literally|basically|right|so|actually|"
    r"just)\b", re.I)
AUTHORED_FLOOR = 12.0     # 2*first_person_rate + filler_rate

# The instruction you type before pasting your own voice memo. Detected on the
# preamble, never on length.
OWN_VOICE_BASE = [
    r"voice\s+(note|memo|journal|recording)",
    r"audio\s+(note|memo|recording)",
    r"transcript\s+of\s+(a|my|this)\s+voice",
    r"synthesi[sz]e\s+(this|my)\s+(voice|memo)",
    r"(here|heres|here's|here.s)\s+(is\s+)?(the|a|my)\s+transcript",
    r"my\s+journal",
    r"i\s+voice\s+noted",
]
OWN_VOICE_HEAD = 220      # chars of preamble to look at

# Platform chrome and boilerplate that only ever appears in pasted material.
# Deliberately narrow: no generic academic vocabulary, because people's own
# voice memos mention assignments and classes constantly.
THIRD_PARTY_BASE = [
    r"skip to main content", r"skip to search", r"notifications total",
    r"you are provided the title and transcript",
    r"instagram followers",
    r"smartbook", r"mylab", r"brightspace", r"question content area",
    r"multiple (choice|select) question\.",
    r"select an answer and submit", r"time remaining", r"group starts",
    r"question\s+\d+\s+\(mandatory\)", r"question\s+\d+\s+options:",
    r"assignment sheet",
]
# Markers strong enough on their own to flag a whole conversation as coursework.
COURSEWORK_BASE = [
    r"smartbook", r"mylab", r"brightspace", r"question content area",
    r"multiple (choice|select) question\.", r"assignment sheet",
    r"question\s+\d+\s+\(mandatory\)", r"question\s+\d+\s+options:",
]


def _alt(parts):
    return re.compile("|".join(parts), re.I)


OWN_VOICE = _alt(OWN_VOICE_BASE)
THIRD_PARTY = _alt(THIRD_PARTY_BASE)
COURSEWORK_MARKERS = _alt(COURSEWORK_BASE)


def configure(cfg):
    """Fold the config's extra markers and timezone into module state."""
    global OWN_VOICE, THIRD_PARTY, COURSEWORK_MARKERS, TZ
    p = cfg.get("parse", {})
    tz = p.get("timezone")
    if tz:
        from zoneinfo import ZoneInfo
        TZ = ZoneInfo(tz)
    else:
        TZ = None
    OWN_VOICE = _alt(OWN_VOICE_BASE + list(p.get("extra_own_voice_preambles", [])))
    THIRD_PARTY = _alt(THIRD_PARTY_BASE + list(p.get("extra_paste_markers", [])))
    COURSEWORK_MARKERS = _alt(COURSEWORK_BASE + list(p.get("extra_coursework_markers", [])))


# Three or more timestamps in one turn: a video/podcast transcript.
TIMESTAMPS = re.compile(r"\b\d{1,2}:\d{2}:\d{2}\b")

# A turn that is mostly a pasted link. In the reference corpus one thread was
# hundreds of turns of search URLs with exam questions in the query string;
# the query strings tokenised into thousands of "words".
URL = re.compile(r"https?://\S+")
URL_SHARE = 0.40

# A bare option pick. Not coursework-specific: people answer ChatGPT's
# numbered reflection menus the same way in personal threads.
OPTION_PICK = re.compile(
    r"^\s*(\(?[a-eA-E]\)?|[0-9]{1,3}|true|false)"
    r"([\s,]+and\s+|[\s,]+)?((\(?[a-eA-E]\)?|[0-9]{1,3})\s*)*[.)]?\s*$", re.I)
OPTION_BLOCK = re.compile(
    r"(^|\n)\s*[a-eA-E][.)]\s+\S.*(\n\s*[a-eA-E][.)]\s+\S.*){2,}")

# ChatGPT's suggested-follow-up chips, clicked rather than written.
# Recognisable as second-person fragments with no first-person pronoun,
# usually bullet-joined. Kept narrow on purpose: a broad "lowercase imperative
# opener" rule swallows every ordinary short instruction you type.
CHIP_VERB = re.compile(
    r"^\s*(?:[-*•]\s*)?(map|pressure-?test|stress-?test|simulate|"
    r"formalize|translate this into|design (a|the)|identify (the|your)|"
    r"explore (the|your|how|why)|break down (your|the|how)|build (a|the|your)|"
    r"turn this into)\b", re.I)
SECOND_PERSON = re.compile(r"\byour\b|\byou\b", re.I)
BULLET = re.compile(r"[•]|\n\s*[-*]\s")
CHIP_MAX_WORDS = 70

# Coursework. Turn-shape drilling is a secondary signal only, gated on an
# actual option block or academic vocabulary, because without that gate it
# flags personal threads where you are picking from ChatGPT's own menus.
DRILL = re.compile(
    r"^\s*(solve|answer|do)\s+(this|these|it|the following|another)"
    r"|^\s*another one\s*$|^\s*next (one|question)\s*$|^\s*same thing", re.I)
SCHOOL_VOCAB = re.compile(
    r"\b(exam|midterm|final|quiz|homework|professor|semester|syllabus|"
    r"assignment|textbook|study guide|coursework|lecture|problem set|"
    r"multiple choice)\b", re.I)


def _rate(pat, text, n_words):
    return len(pat.findall(text)) * 100.0 / max(n_words, 1)


def voice_score(text):
    n = len(WORD.findall(text))
    return 2 * _rate(FIRST_PERSON, text, n) + _rate(SPOKEN_FILLER, text, n)


def classify_turn(text):
    """
    Label one user turn. Order of precedence matters:

      own_voice   beats everything. An explicit "here's my voice memo"
                  preamble is the one signal that is never wrong, and getting
                  it wrong is the expensive direction.
      pasted      explicit third-party chrome.
      quiz        a bare option pick, or a pasted option block.
      suggestion  a clicked ChatGPT follow-up chip.
      authored    everything short, plus long turns that carry your voice.
    """
    n = len(WORD.findall(text))
    if OWN_VOICE.search(text[:OWN_VOICE_HEAD]) and n >= LONG_TURN_WORDS:
        return "own_voice"
    if THIRD_PARTY.search(text) or len(TIMESTAMPS.findall(text)) >= 3:
        return "pasted"
    links = URL.findall(text)
    if links and sum(len(u) for u in links) / max(len(text), 1) > URL_SHARE:
        return "pasted"
    if OPTION_PICK.match(text) or OPTION_BLOCK.search(text):
        return "quiz"
    if n <= CHIP_MAX_WORDS and not FIRST_PERSON.search(text):
        frag = bool(BULLET.search(text)) or len(text.strip().split("\n")) >= 2
        if CHIP_VERB.match(text) or (frag and SECOND_PERSON.search(text)
                                     and not text.rstrip().endswith("?")):
            return "suggestion"
    if n >= LONG_TURN_WORDS:
        # A long turn showing no evidence of authorship is not credited. We do
        # not claim to know what it is, only that nothing marks it as yours.
        return "authored" if voice_score(text) >= AUTHORED_FLOOR else "pasted"
    return "authored"


def is_coursework(user_texts):
    """Conversation-level coursework flag. Precision over recall on purpose."""
    body = "\n".join(user_texts)
    if THIRD_PARTY.search(body) and SCHOOL_VOCAB.search(body):
        return True
    if COURSEWORK_MARKERS.search(body):
        return True
    if len(user_texts) >= 4:
        drills = sum(1 for t in user_texts
                     if OPTION_PICK.match(t) or OPTION_BLOCK.search(t)
                     or DRILL.match(t))
        if (drills >= 4 and drills / len(user_texts) >= 0.30
                and (OPTION_BLOCK.search(body) or SCHOOL_VOCAB.search(body))):
            return True
    return False


# Words that carry no topic signal. Small on purpose: the bag is only ever fed
# to topic regexes, so a stopword that slips through costs nothing.
STOP = set("""
the a an and or but if then than that this these those there here it its it's
is are was were be been being am do does did doing have has had having i im
i'm ive i've me my myself we our us you your he she they them his her their
of in on at to for with from by as into about over after before under between
not no nor so too very just really can could would should will shall may might
must one two three what when where which who whom why how all any both each
few more most other some such only own same don't now up down out off
again further once because while during against above below yours like
get got go going make made say said know think want need thing things lot
""".split())
TERM = re.compile(r"[a-z][a-z'-]{2,}")
TERM_CAP = 150


def term_bag(user_texts):
    """
    A frequency-ranked content-word bag from your own turns, so rank can route
    topics on the body instead of the title. Titles are auto-generated from
    whatever line opened the thread, which is usually a throwaway or a paste.

    Ranked and capped, not a flat set. A flat set of every distinct word in a
    4,000-word turn matches nearly every topic at least once, which turns
    topic routing back into noise and fires the delta flag on everything.
    """
    counts = {}
    for t in user_texts:
        for w in TERM.findall(t.lower()):
            w = w.strip("'-")
            if len(w) < 3 or w in STOP:
                continue
            counts[w] = counts.get(w, 0) + 1
    ranked = sorted(counts, key=lambda w: (-counts[w], w))
    return ranked[:TERM_CAP]


# A day only counts as a return visit if you actually put words down that day.
# Without this a daily one-line check-in thread earns the same bonus as a day
# spent working through a problem.
CONTENT_DAY_WORDS = 80


# --- echoes ----------------------------------------------------------------
#
# "Yes exactly, <the assistant's last sentence>" is not your thinking. Words in
# a user turn that sit inside an 8+ word run the assistant said in the turn
# just before are counted as `echoed`, not authored. Detecting the overlap is
# mechanical; whether you made the idea your own is not, so the words are only
# withheld from the score. verify flags echoes in quotes separately.

ECHO_RUN = 8


def norm(s):
    """Lowercase, fold typography, keep only [a-z0-9 ]. Shared with verify."""
    s = unicodedata.normalize("NFKC", s)
    for a, b in [("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), ("…", "...")]:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s.lower())).strip()


def ngrams(text, n):
    w = text.split()
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def echo_share(text, prev_assistant):
    """Fraction of `text`'s words inside runs copied from `prev_assistant`."""
    if not prev_assistant:
        return 0.0
    grams = ngrams(norm(prev_assistant), ECHO_RUN)
    toks = norm(text).split()
    if not grams or len(toks) < ECHO_RUN:
        return 0.0
    covered = [False] * len(toks)
    for i in range(len(toks) - ECHO_RUN + 1):
        if " ".join(toks[i:i + ECHO_RUN]) in grams:
            covered[i:i + ECHO_RUN] = [True] * ECHO_RUN
    return sum(covered) / len(toks)


def authorship(user_texts, prev_assistant=None):
    """
    Split a conversation's user turns by who actually wrote them.

    `prev_assistant[i]` is the assistant turn right before user turn i (or
    None). Without it, echoes are not detected.
    """
    counts = {"authored": 0, "own_voice": 0, "pasted": 0,
              "quiz": 0, "suggestion": 0}
    words = dict.fromkeys(counts, 0)
    echoed = 0
    labels = []
    prev_assistant = prev_assistant or [None] * len(user_texts)
    for text, prev in zip(user_texts, prev_assistant):
        # Code pasted inside a message is not prose you wrote. Classify and
        # credit the prose; the code's words count as pasted.
        prose = CODE_FENCE.sub(" ", text)
        code_n = len(WORD.findall(text)) - len(WORD.findall(prose))
        lab = classify_turn(prose)
        n = len(WORD.findall(prose))
        if lab in ("authored", "own_voice"):
            e = round(n * echo_share(prose, prev))
            echoed += e
            n -= e
        counts[lab] += 1
        words[lab] += n
        words["pasted"] += code_n
        labels.append((lab, n))
    mine = [n for lab, n in labels if lab in ("authored", "own_voice")]
    return {
        "labels": labels,
        "authored_words": words["authored"] + words["own_voice"],
        "own_voice_words": words["own_voice"],
        "pasted_words": words["pasted"] + words["quiz"] + words["suggestion"],
        "authored_turns": counts["authored"] + counts["own_voice"],
        "max_user_turn_words": max(mine) if mine else 0,
        "echoed_words": echoed,
    }


def previous_assistant(turns):
    """For each user turn, the text of the assistant turn just before it."""
    out, last = [], None
    for t in turns:
        if t["role"] == "assistant":
            last = t["text"]
        else:
            out.append(last)
            last = None
    return out


def metrics(turns):
    user = [t for t in turns if t["role"] == "user"]
    asst = [t for t in turns if t["role"] == "assistant"]

    def words(ts):
        return sum(len(WORD.findall(t["text"])) for t in ts)

    all_text = "\n".join(t["text"] for t in turns)
    code_chars = sum(len(m) for m in CODE_FENCE.findall(all_text))

    times = sorted(t["time"] for t in turns if t.get("time"))
    days = {
        day(t) for t in times
    }
    span_h = round((times[-1] - times[0]) / 3600.0, 2) if len(times) > 1 else 0.0

    user_texts = [t["text"] for t in user]
    auth = authorship(user_texts, previous_assistant(turns))

    # Authored words per calendar day, so a "day touched" has to earn it.
    per_day = {}
    for turn, (lab, n) in zip(user, auth["labels"]):
        if lab not in ("authored", "own_voice") or not turn.get("time"):
            continue
        d = day(turn["time"])
        per_day[d] = per_day.get(d, 0) + n
    content_days = sum(1 for n in per_day.values() if n >= CONTENT_DAY_WORDS)

    uw = words(user)
    aw = auth["authored_words"]
    return {
        "user_turns": len(user),
        "assistant_turns": len(asst),
        "user_words": uw,
        "assistant_words": words(asst),
        "avg_user_turn_words": round(uw / len(user), 1) if user else 0,
        "days_touched": len(days),
        "span_hours": span_h,
        "code_ratio": round(code_chars / len(all_text), 3) if all_text else 0.0,
        "chars": len(all_text),
        "authored_words": aw,
        "own_voice_words": auth["own_voice_words"],
        "pasted_words": auth["pasted_words"],
        "echoed_words": auth["echoed_words"],
        "authored_turns": auth["authored_turns"],
        "max_user_turn_words": auth["max_user_turn_words"],
        "avg_authored_turn_words": (round(aw / auth["authored_turns"], 1)
                                    if auth["authored_turns"] else 0),
        "content_days": content_days,
        "coursework": is_coursework(user_texts),
        "terms": term_bag([t for t, (lab, _) in zip(user_texts, auth["labels"])
                           if lab in ("authored", "own_voice")]),
    }


# --- branch deduplication --------------------------------------------------
#
# ChatGPT's "branch" feature files the forked thread as a new conversation
# titled "Branch <parent title>", carrying the whole parent transcript with it.
# Left alone these double-count in every aggregate. Keep the longer of the
# pair and mark the other, rather than deleting either, so the transcripts on
# disk stay complete.

BRANCH_TITLE = re.compile(r"^\s*branch\s*[·–—:>-]*\s*", re.I)


def mark_branch_duplicates(index):
    """Flag the shorter half of each Branch/parent pair. Mutates `index`."""
    for row in index:
        row.setdefault("branch_dup", False)
        row.setdefault("branch_of", None)
    by_title = {}
    for row in index:
        by_title.setdefault(row["title"].strip().lower(), []).append(row)
    pairs = 0
    for row in index:
        title = row["title"].strip()
        if not BRANCH_TITLE.match(title):
            continue
        parent_title = BRANCH_TITLE.sub("", title).strip().lower()
        for parent in by_title.get(parent_title, []):
            if parent is row:
                continue
            loser = parent if row["user_words"] >= parent["user_words"] else row
            keeper = row if loser is parent else parent
            loser["branch_dup"] = True
            loser["branch_of"] = keeper["file"]
            row["branch_of"] = row["branch_of"] or keeper["file"]
            pairs += 1
            break
    return pairs


# --- reading the parsed markdown back in -----------------------------------
#
# The linearised markdown is a lossless round-trip of the user turns, so the
# authorship signals can be recomputed from conversations/*.md without the
# original export on disk.

ME_TURN = re.compile(r"^## Me\n(.*?)(?=^## Me$|^### ChatGPT$|\Z)", re.S | re.M)
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


SPEAKER = re.compile(r"(?m)^(## Me|### ChatGPT)$")


def dialogue_from_markdown(path):
    """Return [{"role", "text"}] for every turn of a parsed conversation file."""
    with io.open(path, encoding="utf-8") as fh:
        body = FRONTMATTER.sub("", fh.read())
    segs = SPEAKER.split(body)
    return [{"role": "user" if segs[i] == "## Me" else "assistant",
             "text": segs[i + 1].strip()}
            for i in range(1, len(segs) - 1, 2) if segs[i + 1].strip()]


def turns_from_markdown(path):
    """Return the user turns of a parsed conversation file, in order."""
    with io.open(path, encoding="utf-8") as fh:
        body = fh.read()
    # Strip the frontmatter block only. Splitting on "\n---\n" instead
    # truncates every conversation containing a horizontal rule. That exact
    # bug once dropped a quarter of a corpus without any error.
    body = FRONTMATTER.sub("", body)
    return [m.group(1).strip() for m in ME_TURN.finditer(body) if m.group(1).strip()]


def slug(title, n=60):
    s = re.sub(r"[^\w\s-]", "", (title or "untitled").lower()).strip()
    s = re.sub(r"[\s_]+", "-", s)
    return (s[:n].rstrip("-")) or "untitled"


def render(convo, turns, meta):
    created = convo.get("create_time")
    date = day(created) if created else "unknown"
    fm = {
        "title": convo.get("title") or "Untitled",
        "date": date,
        "source": "chatgpt-export",
        "conversation_id": convo.get("conversation_id") or convo.get("id") or "",
    }
    lines = ["---"]
    for k, v in fm.items():
        lines.append(f'{k}: "{v}"' if isinstance(v, str) else f"{k}: {v}")
    lines.append(f"user_turns: {meta['user_turns']}")
    lines.append(f"user_words: {meta['user_words']}")
    lines.append(f"days_touched: {meta['days_touched']}")
    lines.append("---\n")
    lines.append(f"# {fm['title']}\n")
    for t in turns:
        who = "## Me" if t["role"] == "user" else "### ChatGPT"
        lines.append(f"{who}\n\n{t['text']}\n")
    return "\n".join(lines)


def run(export, cfg, out=None, limit=0, min_user_words=None):
    configure(cfg)
    out = out or cfg["paths"]["archive"]
    floor = cfg["parse"]["min_user_words"] if min_user_words is None else min_user_words

    convos = load_conversations(export)
    total_in = len(convos)
    if limit:
        convos = convos[:limit]

    conv_dir = os.path.join(out, "conversations")
    os.makedirs(conv_dir, exist_ok=True)

    index, empty, short, seen_names = [], 0, 0, {}
    for convo in convos:
        turns = linearize(convo)
        if not turns:
            empty += 1
            continue
        meta = metrics(turns)
        if meta["user_words"] < floor:
            short += 1
            continue

        created = convo.get("create_time")
        date = day(created) if created else "0000-00-00"
        base = f"{date}-{slug(convo.get('title'))}"
        seen_names[base] = seen_names.get(base, 0) + 1
        if seen_names[base] > 1:
            base = f"{base}-{seen_names[base]}"
        fname = base + ".md"

        with io.open(os.path.join(conv_dir, fname), "w", encoding="utf-8") as fh:
            fh.write(render(convo, turns, meta))

        index.append({
            "file": fname,
            "conversation_id": convo.get("conversation_id") or convo.get("id") or "",
            "title": convo.get("title") or "Untitled",
            "date": date,
            "create_time": created,
            **meta,
        })

    pairs = mark_branch_duplicates(index)

    with io.open(os.path.join(out, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2)

    # Account for every conversation. If these don't add up, something was
    # dropped silently, and silent drops are the failure mode that bites.
    accounted = len(index) + empty + short
    course = sum(1 for r in index if r["coursework"])
    own = sum(1 for r in index if r["own_voice_words"])
    uw = sum(r["user_words"] for r in index)
    aw = sum(r["authored_words"] for r in index)
    print(f"input    {total_in} conversations"
          + (f" (limited to {len(convos)})" if limit else ""))
    print(f"parsed   {len(index)} -> {conv_dir}")
    print(f"skipped  {empty} empty, {short} under {floor} user words")
    print(f"authored {aw:,} of {uw:,} user words ({(aw / uw * 100) if uw else 0:.1f}%); "
          f"{sum(r['pasted_words'] for r in index):,} pasted/clicked/quiz, "
          f"{sum(r['echoed_words'] for r in index):,} echoed")
    print(f"flagged  {course} coursework, {own} with own-voice memos, "
          f"{pairs} branch duplicates")
    if accounted != len(convos):
        print(f"WARNING  {len(convos) - accounted} conversations unaccounted for")
    return index


def main(argv=None):
    ap = argparse.ArgumentParser(prog="synth parse")
    ap.add_argument("export")
    ap.add_argument("--config")
    ap.add_argument("--out", help="override paths.archive")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-user-words", type=int)
    args = ap.parse_args(argv)
    cfg = cfgmod.load(args.config)
    run(args.export, cfg, args.out, args.limit, args.min_user_words)


if __name__ == "__main__":
    main()
