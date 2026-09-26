"""
Build a small synthetic ChatGPT export that exercises every failure mode the
pipeline was built to handle. No real data: every line here is invented.

    python3 tests/make_fixture.py            -> examples/sample-export/conversations.json

Each conversation is named for the case it tests.
"""

import datetime as dt
import json
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "examples", "sample-export", "conversations.json")


def ts(date, hour=12, minute=0):
    return dt.datetime(*map(int, date.split("-")), hour, minute).timestamp()


def convo(title, turns):
    """turns: list of (role, text, 'YYYY-MM-DD', hour)."""
    mapping, parent = {}, None
    root = str(uuid.uuid5(uuid.NAMESPACE_DNS, title + "root"))
    mapping[root] = {"id": root, "message": None, "parent": None, "children": []}
    parent = root
    for i, (role, text, date, hour) in enumerate(turns):
        nid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{title}{i}"))
        mapping[nid] = {
            "id": nid,
            "parent": parent,
            "children": [],
            "message": {
                "id": nid,
                "author": {"role": role},
                "create_time": ts(date, hour, i % 60),
                "content": {"content_type": "text", "parts": [text]},
                "metadata": {},
            },
        }
        mapping[parent]["children"].append(nid)
        parent = nid
    first = turns[0][2]
    return {
        "title": title,
        "create_time": ts(first, turns[0][3]),
        "conversation_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, title)),
        "current_node": parent,
        "mapping": mapping,
    }


U, A = "user", "assistant"

REFLECTION_1 = (
    "I keep telling myself I want to start my own company, but when I actually "
    "picture the day to day I don't want the sales calls or the hiring. I think "
    "what I like is being the person who figures out how the thing works and "
    "then makes it run. My dad always said real work means being your own boss "
    "and I think I absorbed that without ever checking whether it fit me.")
REFLECTION_2 = (
    "Okay I slept on it. I think the honest version is that I like hard problems "
    "and I like being trusted with them, and none of that requires owning the "
    "business. I'm going to stop pitching myself as a future founder in "
    "interviews because I don't believe it and people can tell.")
REFLECTION_3 = (
    "Coming back to this a week later. I told my manager I want the technical "
    "lead track, not the management track, and it felt right saying it out loud. "
    "My fear was that I'd be settling, but I think I was confusing ambition with "
    "a specific costume of ambition.")

MEMO = ("here's my voice memo from the walk, can you synthesize it\n\n" + (
    "So yeah I was walking home and I realized I um I basically never let "
    "myself want things out loud, like I just kind of decide ahead of time that "
    "I don't care so that it can't hurt. And honestly I think I've been doing "
    "that since I was a kid, you know, because it was easier to be the easy one "
    "in the house. I mean I'm not mad about it, it's just like I notice it now. "
    "And the thing is I actually do want stuff, I want to make things that are "
    "mine and I want people to see them, and I'm so used to saying it doesn't "
    "matter that I believe it for a second. ") * 3)

ARTICLE = ("Summarize this\n\n" + (
    "The quarterly report indicates that regional revenue increased by eight "
    "percent year over year, driven primarily by expansion in the enterprise "
    "segment. Operating margins remained stable despite increased investment "
    "in research and development. The board approved a revised capital "
    "allocation framework that prioritizes debt reduction over share "
    "repurchases through the end of the fiscal year. Analysts expect continued "
    "headwinds in the consumer division as discretionary spending softens. ") * 5)

CHECKIN = "Check in: what's on the list for today? Keep it short."

COINED_BY_ASSISTANT = (
    "It sounds like you're describing ambition that has been borrowed from "
    "someone else rather than chosen by you.")
ECHO = ("Yes exactly, ambition that has been borrowed from someone else rather "
        "than chosen by you. That's the thing I keep running into with the "
        "founder idea and it explains why every plan feels heavy.")

CODE = ("Why does this throw? I want the parser to skip empty lines.\n\n```python\n"
        + "def parse(lines):\n    for line in lines:\n        yield line.split(',')[1]\n" * 6
        + "```\nIt fails on the blank line at the end of the file every time.")

CONVERSATIONS = [
    # authored reflection across several days, before the career position change
    convo("Rethinking the founder plan", [
        (U, REFLECTION_1, "2024-03-02", 21), (A, "What do you like about the work itself?", "2024-03-02", 21),
        (U, REFLECTION_2, "2024-03-03", 9), (A, "That's a clear distinction.", "2024-03-03", 9),
        (U, REFLECTION_3, "2024-03-10", 18), (A, "How did your manager respond?", "2024-03-10", 18),
    ]),
    # the same thread, forked with "Branch"; shorter, should be flagged branch_dup
    convo("Branch · Rethinking the founder plan", [
        (U, REFLECTION_1, "2024-03-04", 10), (A, "Say more.", "2024-03-04", 10),
    ]),
    # own-voice memo: long, dictated, preamble says so -> weighted UP
    convo("Walk home thoughts", [
        (U, MEMO, "2025-01-15", 19), (A, "Here's a synthesis of your memo...", "2025-01-15", 19),
        (U, "That's right. I want to stop pre-deciding I don't care.", "2025-01-15", 19),
    ]),
    # long third-party paste: same length as the memo, worth nothing
    convo("Quarterly report summary", [
        (U, ARTICLE, "2025-02-01", 14), (A, "The report says revenue grew 8%... " * 40, "2025-02-01", 14),
    ]),
    # coursework: platform chrome, option picks, drill turns
    convo("Stats review", [
        (U, "Question 3 options: a) 0.25 b) 0.5 c) 0.75 d) 1.0 for the midterm "
            "practice exam in my statistics class, what is the probability of "
            "two heads in two fair coin flips given the first is heads", "2025-03-01", 20),
        (A, "b) 0.5", "2025-03-01", 20),
        (U, "B", "2025-03-01", 20), (A, "Correct.", "2025-03-01", 20),
        (U, "another one", "2025-03-01", 20), (A, "Next question...", "2025-03-01", 20),
        (U, "solve this: a) 1 b) 2 c) 3 which is the mean of 1 2 3", "2025-03-01", 20),
        (A, "b) 2", "2025-03-01", 20),
        (U, "C", "2025-03-01", 20), (A, "Actually b.", "2025-03-01", 20),
    ]),
    # routine standing-instruction thread: touched on many days, few words
    convo("Daily check-in", [
        (U, CHECKIN + " " + "Gym, groceries, emails.", f"2025-04-0{d}", 8)
        if i % 2 == 0 else (A, "Got it: gym, groceries, emails.", f"2025-04-0{d}", 8)
        for d in range(1, 8) for i in range(2)
    ]),
    # assistant coins a phrase, user echoes it; verify must flag a quote of it
    convo("Borrowed ambition", [
        (U, "I keep making plans to start a company and every one of them feels "
            "heavy before I even begin. I can't tell if I'm lazy or if something "
            "else is going on with how I set goals for myself.", "2025-05-05", 22),
        (A, COINED_BY_ASSISTANT, "2025-05-05", 22),
        (U, ECHO, "2025-05-05", 22),
        (A, "What would a chosen ambition look like?", "2025-05-05", 22),
        # a clicked follow-up chip: second-person, no first person
        (U, "Map which of your goals are chosen versus inherited\n"
            "• Identify the strongest inherited one", "2025-05-05", 22),
        (A, "Here's a map...", "2025-05-05", 22),
    ]),
    # code session: penalised, not belief
    convo("Parser bug", [
        (U, CODE, "2025-06-01", 11), (A, "```python\nfor line in lines:\n    if line.strip(): ...\n```", "2025-06-01", 11),
    ]),
    # a user turn with a horizontal rule: regression test for the truncation bug
    convo("Two lists", [
        (U, "Here are my two lists of what I want this year, first the ones I "
            "actually care about and then the ones I think I should want.\n\n"
            "Travel more, write every week, build one thing that is mine\n\n---\n\n"
            "Get promoted, buy a nicer car, have a five year plan, and I notice the "
            "second list is the one I talk about at dinner", "2025-07-01", 9),
        (A, "The first list is about expression; the second is about approval.", "2025-07-01", 9),
    ]),
    # trivial: under the word floor, skipped
    convo("Quick question", [(U, "What's 15% of 80?", "2025-08-01", 12), (A, "12.", "2025-08-01", 12)]),
]


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(CONVERSATIONS, fh, indent=1)
    print(f"wrote {len(CONVERSATIONS)} synthetic conversations -> {os.path.normpath(OUT)}")


if __name__ == "__main__":
    main()
