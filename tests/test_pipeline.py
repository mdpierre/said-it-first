"""
End-to-end tests on the synthetic export. Each test pins one failure mode that
actually happened on a real archive (see METHOD.md).

    python3 -m unittest discover tests
"""

import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

import make_fixture  # noqa: E402
from synth import config, parse, rank, verify, voice  # noqa: E402


def quiet(fn, *a, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **kw)


class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        export = os.path.join(cls.tmp, "conversations.json")
        with open(export, "w") as fh:
            json.dump(make_fixture.CONVERSATIONS, fh)
        cfg = copy.deepcopy(config.DEFAULTS)
        cfg["paths"] = {k: os.path.join(cls.tmp, os.path.basename(v))
                        for k, v in cfg["paths"].items()}
        cfg["volatile"] = ["career", "business"]
        cfg["position_changes"] = [{"date": "2024-06-01", "topic": "career",
                                    "what": "dropped the founder plan"}]
        cls.cfg = cfg
        cls.index = quiet(parse.run, export, cfg)
        quiet(voice.run, cfg)
        cls.scored = quiet(rank.run, cfg, force=True)
        cls.by_title = {r["title"]: r for r in cls.scored}
        cls.all_rows = {r["title"]: r for r in cls.index}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    # --- stage 1: parse ---------------------------------------------------

    def test_trivial_conversation_skipped(self):
        self.assertNotIn("Quick question", self.all_rows)

    def test_own_voice_memo_detected(self):
        self.assertGreater(self.all_rows["Walk home thoughts"]["own_voice_words"], 300)

    def test_pasted_document_not_credited(self):
        r = self.all_rows["Quarterly report summary"]
        self.assertGreater(r["user_words"], 300)
        self.assertLess(r["authored_words"], 10)

    def test_coursework_flagged(self):
        self.assertTrue(self.all_rows["Stats review"]["coursework"])
        self.assertFalse(self.all_rows["Rethinking the founder plan"]["coursework"])

    def test_branch_duplicate_flagged_and_dropped(self):
        self.assertTrue(self.all_rows["Branch · Rethinking the founder plan"]["branch_dup"])
        self.assertNotIn("Branch · Rethinking the founder plan", self.by_title)

    def test_suggestion_chip_not_credited(self):
        labels = [parse.classify_turn(t) for t in [
            "Map which of your goals are chosen versus inherited\n"
            "• Identify the strongest inherited one"]]
        self.assertEqual(labels, ["suggestion"])

    def test_routine_thread_content_days(self):
        r = self.all_rows["Daily check-in"]
        self.assertGreaterEqual(r["days_touched"], 7)
        self.assertEqual(r["content_days"], 0)

    # --- stage 2: voice ---------------------------------------------------

    def _voice_text(self):
        d = os.path.join(self.cfg["paths"]["archive"], "voice")
        return "".join(verify._read(os.path.join(d, f)) for f in os.listdir(d))

    def test_voice_has_no_assistant_text(self):
        self.assertNotIn("The first list is about expression", self._voice_text())

    def test_horizontal_rule_does_not_truncate(self):
        # Regression: splitting on "\n---\n" once silently dropped 24% of a corpus.
        v = self._voice_text()
        self.assertIn("Travel more, write every week", v)
        self.assertIn("Get promoted, buy a nicer car", v)

    # --- stage 3: rank ----------------------------------------------------

    def test_memo_outranks_equal_length_paste(self):
        self.assertGreater(self.by_title["Walk home thoughts"]["score"],
                           self.by_title["Quarterly report summary"]["score"])

    def test_reflection_outranks_routine_and_coursework(self):
        top = self.by_title["Rethinking the founder plan"]["score"]
        self.assertGreater(top, self.by_title["Daily check-in"]["score"])
        self.assertGreater(top, self.by_title["Stats review"]["score"])

    def test_delta_candidate_before_position_change(self):
        r = self.by_title["Rethinking the founder plan"]
        self.assertIn("career", r["topics"])
        self.assertTrue(r["delta_candidate"])

    def test_shortlist_refuses_overwrite(self):
        with self.assertRaises(SystemExit):
            quiet(rank.run, self.cfg)

    # --- stage 5: verify --------------------------------------------------

    def _verify(self, text):
        staging = self.cfg["paths"]["staging"]
        os.makedirs(staging, exist_ok=True)
        with open(os.path.join(staging, "draft.md"), "w") as fh:
            fh.write(text)
        return verify.check(staging, self.cfg["paths"]["archive"])

    def test_verbatim_quote_passes(self):
        q, uns, echo = self._verify(
            '> "I think I was confusing ambition with a specific costume of ambition."')
        self.assertEqual((len(q), uns, echo), (1, [], []))

    def test_paraphrase_in_quotes_fails(self):
        _, uns, _ = self._verify(
            '> "I realized I had mistaken ambition for one particular costume of it."')
        self.assertEqual(len(uns), 1)

    def test_assistant_coined_phrase_flagged(self):
        _, uns, echo = self._verify(
            '> "ambition that has been borrowed from someone else rather than chosen by you"')
        self.assertEqual(uns, [])
        self.assertEqual(len(echo), 1)


if __name__ == "__main__":
    unittest.main()
