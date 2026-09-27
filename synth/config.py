"""
Load said-it-first.toml and merge it over the defaults.

Everything that is about *you* (topics, dated position changes, platform
markers specific to your school or job, weights you retuned) lives in the
config file. The code only holds what should be true for anyone's archive.

Resolution order for the config path:
    --config PATH  ->  ./said-it-first.toml  ->  built-in defaults
"""

import copy
import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    sys.exit("said-it-first needs Python 3.11+ (for tomllib).")

DEFAULT_PATH = "said-it-first.toml"

DEFAULTS = {
    # Used in headers of generated files. "you" reads fine if left alone.
    "owner": "you",

    "paths": {
        "archive": "workspace/archive",     # parsed conversations + index.json + voice/
        "staging": "workspace/staging",     # model drafts wait here for your tick
        "shortlist": "workspace/SHORTLIST.md",
        "notes": "workspace/notes",         # where approved notes are written
        "ledger": "workspace/ledger.json",  # conversations already reviewed
        "profile": "profile.md",            # who you are now; the agents read it
    },

    "output": {
        # "wikilink" -> [[file|title]]   (Obsidian, Logseq, Foam)
        # "markdown" -> [title](path)    (anything else)
        "link_style": "wikilink",
    },

    "parse": {
        "min_user_words": 50,
        # IANA zone for calendar dates ("America/New_York"). Empty = this
        # machine's local zone. Set it so dates don't shift between machines.
        "timezone": "",
        # Extra third-party markers for platforms you pasted from (your LMS,
        # your employer's intranet...). Case-insensitive regex fragments.
        "extra_paste_markers": [],
        # Extra markers that flag a whole conversation as coursework.
        "extra_coursework_markers": [],
        # Extra phrasings you use when pasting your OWN dictated notes.
        "extra_own_voice_preambles": [],
    },

    "voice": {
        # Tokens per reading chunk. One chunk-reader agent reads one chunk,
        # so this must fit comfortably in your model's context with room to
        # think and write: ~150k suits a 1M window at a steady pace, ~60k a
        # 200k window.
        "chunk_tokens": 60000,
    },

    "rank": {
        "top": 60,
        "stale_after_days": 120,
        "min_term_hits": 2,
        "weights": {
            "authored_words": 1.00,
            "own_voice": 0.70,
            "turn_depth": 0.60,
            "turn_length": 0.90,
            "longest_turn": 0.80,
            "return_visit": 0.90,
            "return_cap": 4,
            "routine_min_wpd": 80,
        },
        "penalties": {
            "code": 2.00,
            "consumption": 1.50,
            "routine": 1.20,
            "coursework": 4.00,
        },
    },

    # Topic routing. Each topic is either
    #   pattern = '<regex>'                         (needs min_term_hits distinct hits)
    #   all_of  = ['<regex>', '<regex>']            (each needs min_term_hits hits)
    #   replaces = ['other-topic']                  (drop these when this one matches)
    # Patterns run against the conversation title plus a bag of the most
    # frequent content words from YOUR turns. Write stems as `\w*` explicitly:
    # `\bapplicat\b` does not match "application".
    "topics": {
        "career": {"pattern": r"\b(job|jobs|resume|interview\w*|recruit\w*|"
                              r"applicat\w*|salary|linkedin|career|promot\w*|manager)\b"},
        "business": {"pattern": r"\b(client\w*|business|startup|compan\w*|revenue|pricing|"
                                r"offer\w*|customer\w*|founder|market\w*|sales)\b"},
        "creative": {"pattern": r"\b(writ\w*|music|photo\w*|design\w*|art|"
                                r"draw\w*|film\w*|creative|creativity)\b"},
        "tech": {"pattern": r"\b(code|coding|python|javascript|api|script\w*|"
                            r"automat\w*|deploy\w*|agent\w*|llm|prompt\w*)\b"},
        "health": {"pattern": r"\b(workout\w*|gym|sleep|diet|protein|lift\w*|"
                              r"run\w*|training|weight|health\w*)\b"},
        "relational": {"pattern": r"\b(friend\w*|relationship\w*|dating|partner|"
                                  r"family|lonely|loneliness|trust|social|"
                                  r"vulnerab\w*|intimacy)\b"},
        "self": {"pattern": r"\b(identity|belief\w*|meaning|purpose|values|ego|"
                            r"discipline|spiritual|philosoph\w*|awareness|fear\w*|"
                            r"emotion\w*|feel\w*)\b"},
    },

    # Domains where your position changed. Old conversations in them are DELTA
    # candidates: the "was" half of how your thinking moved.
    "volatile": [],

    # Dated position changes: [{date = "2025-06-01", topic = "career", what = "..."}]
    "position_changes": [],
}


def _merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict) and k != "topics":
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def _unknown(over, base, where=""):
    """Keys in the user's file that the defaults don't define (likely typos or
    keys placed under the wrong [table] header)."""
    out = []
    for k, v in over.items():
        here = f"{where}{k}"
        if k not in base:
            out.append(here)
        elif k == "topics" and isinstance(v, dict):
            for name, spec in v.items():
                for sk in (spec if isinstance(spec, dict) else {}):
                    if sk not in ("pattern", "all_of", "replaces"):
                        out.append(f"topics.{name}.{sk}")
        elif isinstance(v, dict) and isinstance(base[k], dict):
            out += _unknown(v, base[k], here + ".")
    return out


def load(path=None):
    """Return the merged config dict. Paths are resolved against the config's dir."""
    cfg = copy.deepcopy(DEFAULTS)
    chosen = path or (DEFAULT_PATH if os.path.exists(DEFAULT_PATH) else None)
    base_dir = os.getcwd()
    if chosen:
        if not os.path.exists(chosen):
            sys.exit(f"config not found: {chosen}")
        with open(chosen, "rb") as fh:
            user = tomllib.load(fh)
        for key in _unknown(user, DEFAULTS):
            hint = ""
            top = key.rsplit(".", 1)[-1]
            if "." in key and top in DEFAULTS:
                hint = (f" (did you mean top-level `{top}`? Move it above the "
                        f"first [table] header)")
            print(f"WARNING  unknown config key `{key}`, ignored{hint}", file=sys.stderr)
        _merge(cfg, user)
        base_dir = os.path.dirname(os.path.abspath(chosen))
    cfg["_source"] = os.path.abspath(chosen) if chosen else "(built-in defaults)"
    for k, v in cfg["paths"].items():
        cfg["paths"][k] = os.path.normpath(os.path.join(base_dir, os.path.expanduser(v)))
    return cfg


def link(file_stem, title, rel_prefix="", style="wikilink"):
    """Render a link to a parsed conversation in the configured style."""
    safe = title.replace("|", "\\|")
    if style == "markdown":
        return f"[{safe}]({rel_prefix}{file_stem}.md)"
    return f"[[{file_stem}\\|{safe}]]"
