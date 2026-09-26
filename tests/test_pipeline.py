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

    def test_code_block_not_credited_as_authored(self):
        # Regression (dry run): pasted code counted as the owner's words and
        # put a debugging thread in the top 5.
        r = self.all_rows["Parser bug"]
        self.assertLess(r["authored_words"], 40)
        self.assertGreater(r["pasted_words"], 40)

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
        return verify.check(staging, self.cfg)

    def _status(self, text):
        return [(r["status"], r["labeled"]) for r in self._verify(text)]

    def test_verbatim_quote_passes(self):
        self.assertEqual(self._status(
            '> "I think I was confusing ambition with a specific costume of ambition."'),
            [("ok", False)])

    def test_paraphrase_in_quotes_fails(self):
        self.assertEqual(self._status(
            '> "I realized I had mistaken ambition for one particular costume of it."'),
            [("unsourced", False)])

    def test_assistant_coined_phrase_flagged(self):
        self.assertEqual(self._status(
            '> "ambition that has been borrowed from someone else rather than chosen by you"'),
            [("echoed", False)])

    def test_owner_said_it_first_not_echo(self):
        self.assertEqual(self._status(
            '> "I would rather be trusted with hard problems than be the one who owns them"'),
            [("ok", False)])

    def test_prefixed_echo_flagged(self):
        # Regression: the first verify compared only the opening words, so
        # "Yes exactly, <assistant phrase>" passed as the owner's own line.
        self.assertEqual(self._status(
            '> "Yes exactly, ambition that has been borrowed from someone else '
            'rather than chosen by you."'), [("echoed", False)])

    def test_labeled_echo_is_kept_not_failed(self):
        res = self._verify(
            '> "Yes exactly, ambition that has been borrowed from someone else '
            'rather than chosen by you." **assistant-coined, echoed**')
        self.assertEqual([(r["status"], r["labeled"]) for r in res], [("echoed", True)])
        self.assertEqual(verify.failures(res), [])

    def test_plain_word_near_quote_is_not_a_label(self):
        # Regression (dry run): "none cleaned" in a nearby note let a
        # paraphrase in quotation marks pass as labeled.
        self.assertEqual(self._status(
            'Quotes below are verbatim, none cleaned.\n\n'
            '> "I realized I had mistaken ambition for one particular costume of it."'),
            [("unsourced", False)])

    def test_quoting_a_clicked_chip_flagged(self):
        self.assertEqual(self._status(
            '> "Map which of your goals are chosen versus inherited"'),
            [("not_authored", False)])

    def test_quoting_pasted_text_flagged(self):
        self.assertEqual(self._status(
            '> "Operating margins remained stable despite increased investment in '
            'research and development."'), [("not_authored", False)])

    def test_elided_quote_checks_each_segment(self):
        self.assertEqual(self._status(
            '> "I keep telling myself I want to start my own company ... I don\'t '
            'want the sales calls or the hiring."'), [("ok", False)])

    def test_short_quotes_on_one_line_not_paired(self):
        # Regression: `"yes" ... "no, ..."` paired the inner quote marks.
        self.assertEqual(self._status(
            'He said "yes" and I said "no" and then went on for a long while about other things.'),
            [])


class Config(unittest.TestCase):
    def test_misplaced_top_level_key_warns(self):
        # Regression: `volatile` written below a [table] header was silently
        # ignored, in the example config and in the first real config.
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as fh:
            fh.write('[rank]\ntop = 5\nvolatile = ["career"]\n')
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                cfg = config.load(fh.name)
        finally:
            os.unlink(fh.name)
        self.assertEqual(cfg["volatile"], [])
        self.assertIn("rank.volatile", err.getvalue())

    def test_example_config_loads_cleanly(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            config.load(os.path.join(ROOT, "chat-synthesis.example.toml"))
        self.assertEqual(err.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
