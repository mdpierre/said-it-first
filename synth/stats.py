"""
Calibration report: is the authorship classifier right for YOUR archive?

    python3 -m synth stats [--samples N]

The voice-density threshold (parse.AUTHORED_FLOOR) was measured on one
person's English corpus. Before trusting rank output on yours, look at how
your long turns are split and read a few from each side of the line. If your
own writing lands under the floor (terse typist, second language, formal
register), lower `AUTHORED_FLOOR`; if pasted documents land above it, raise it.
"""

import argparse
import glob
import io
import json
import os
import random
from collections import Counter

from . import config as cfgmod
from . import parse


def run(cfg, samples=3, seed=0):
    parse.configure(cfg)
    archive = cfg["paths"]["archive"]
    with io.open(os.path.join(archive, "index.json"), encoding="utf-8") as fh:
        rows = json.load(fh)

    labels, words = Counter(), Counter()
    long_turns = []
    for path in glob.glob(os.path.join(archive, "conversations", "*.md")):
        for t in parse.turns_from_markdown(path):
            lab = parse.classify_turn(t)
            n = len(parse.WORD.findall(t))
            labels[lab] += 1
            words[lab] += n
            if n >= parse.LONG_TURN_WORDS:
                long_turns.append((parse.voice_score(t), lab,
                                   os.path.basename(path), t))

    total = sum(words.values()) or 1
    print(f"{len(rows)} conversations, {sum(labels.values())} user turns\n")
    print(f"{'label':<11} {'turns':>7} {'words':>10} {'share':>7}")
    for lab in ("authored", "own_voice", "pasted", "quiz", "suggestion"):
        print(f"{lab:<11} {labels[lab]:>7} {words[lab]:>10,} "
              f"{words[lab] * 100 / total:>6.1f}%")

    print(f"\nlong turns (>= {parse.LONG_TURN_WORDS} words): {len(long_turns)}")
    buckets = Counter(int(s // 4) * 4 for s, *_ in long_turns)
    for b in sorted(buckets):
        mark = " <- floor" if b <= parse.AUTHORED_FLOOR < b + 4 else ""
        print(f"  voice score {b:>3}-{b + 3:<3} {'#' * min(buckets[b], 60)} "
              f"{buckets[b]}{mark}")

    rnd = random.Random(seed)
    floor = parse.AUTHORED_FLOOR
    near = [x for x in long_turns if x[1] != "own_voice" and abs(x[0] - floor) < 6]
    print(f"\n{min(samples, len(near))} samples near the floor ({floor}). "
          "Read them: are the 'pasted' ones really someone else's text?\n")
    for s, lab, f, t in rnd.sample(near, min(samples, len(near))):
        print(f"--- {lab} (score {s:.1f}) {f}\n{t[:400]}\n")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="synth stats")
    ap.add_argument("--config")
    ap.add_argument("--samples", type=int, default=3)
    args = ap.parse_args(argv)
    run(cfgmod.load(args.config), args.samples)


if __name__ == "__main__":
    main()
