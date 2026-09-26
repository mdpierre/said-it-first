"""
chat-synthesis command line.

    python3 -m synth parse <export>   stage 1: export -> markdown + index.json
    python3 -m synth voice            stage 2: your turns only, by year
    python3 -m synth rank             stage 3: score -> SHORTLIST.md
    python3 -m synth verify           stage 5: check every staged quote is yours
    python3 -m synth stats            calibrate the authorship classifier
    python3 -m synth run <export>     stages 1-3 in one go
    python3 -m synth paths            print resolved paths (for agents)

All commands take --config PATH (default ./chat-synthesis.toml).
Stages 4, 6 and 7 are model and human passes; see .claude/skills/.
"""

import sys

from . import parse, rank, stats, verify, voice
from . import config as cfgmod

COMMANDS = {"parse": parse.main, "voice": voice.main, "rank": rank.main,
            "verify": verify.main, "stats": stats.main}


def run_all(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="synth run")
    ap.add_argument("export")
    ap.add_argument("--config")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    cfg = cfgmod.load(args.config)
    print(f"config   {cfg['_source']}\n")
    parse.run(args.export, cfg)
    print()
    voice.run(cfg)
    print()
    rank.run(cfg, force=args.force)


def paths(argv):
    import argparse
    import json
    ap = argparse.ArgumentParser(prog="synth paths")
    ap.add_argument("--config")
    cfg = cfgmod.load(ap.parse_args(argv).config)
    print(json.dumps({"config": cfg["_source"], "owner": cfg["owner"],
                      "link_style": cfg["output"]["link_style"],
                      **cfg["paths"]}, indent=2))


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, argv = sys.argv[1], sys.argv[2:]
    if cmd == "run":
        return run_all(argv)
    if cmd == "paths":
        return paths(argv)
    if cmd not in COMMANDS:
        sys.exit(f"unknown command {cmd!r}\n{__doc__}")
    COMMANDS[cmd](argv)


if __name__ == "__main__":
    main()
