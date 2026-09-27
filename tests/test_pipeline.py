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
from synth import config, ledger, parse, promote, rank, schema, verify, voice  # noqa: E402


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
        cfg["parse"]["timezone"] = "UTC"
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

    def test_echoed_words_not_credited(self):
        # "Yes exactly, <assistant's sentence>" is not authored thinking.
        r = self.all_rows["Borrowed ambition"]
        self.assertGreaterEqual(r["echoed_words"], 12)  # the 13-word phrase
        self.assertEqual(self.all_rows["Rethinking the founder plan"]["echoed_words"], 0)

    def test_owner_repeating_own_line_not_echoed(self):
        # The assistant quoted the owner's line back; repeating it is not an echo.
        self.assertEqual(self.all_rows["Said it first"]["echoed_words"], 0)

    def test_stats_split_matches_parse(self):
        # Regression (dry run): stats classified turns with code still in
        # them, so its authored share disagreed with parse on the same archive.
        from synth import stats
        words = quiet(stats.run, self.cfg)
        mine = sum(r["authored_words"] + r["echoed_words"] for r in self.index)
        self.assertEqual(words["authored"] + words["own_voice"], mine)
        self.assertEqual(words["pasted"] + words["quiz"] + words["suggestion"],
                         sum(r["pasted_words"] for r in self.index))

    def test_conversation_id_in_index(self):
        self.assertTrue(all(r["conversation_id"] for r in self.index))

    def test_routine_thread_content_days(self):
        r = self.all_rows["Daily check-in"]
        self.assertGreaterEqual(r["days_touched"], 7)
        self.assertEqual(r["content_days"], 0)

    # --- stage 2: voice ---------------------------------------------------

    def _voice_text(self):
        d = os.path.join(self.cfg["paths"]["archive"], "voice")
        return "".join(verify._read(os.path.join(d, f)) for f in os.listdir(d)
                       if f.endswith(".md"))

    def test_voice_has_no_assistant_text(self):
        self.assertNotIn("The first list is about expression", self._voice_text())

    def test_horizontal_rule_does_not_truncate(self):
        # Regression: splitting on "\n---\n" once silently dropped 24% of a corpus.
        v = self._voice_text()
        self.assertIn("Travel more, write every week", v)
        self.assertIn("Get promoted, buy a nicer car", v)

    def test_chunks_split_and_complete(self):
        d = os.path.join(self.cfg["paths"]["archive"], "voice")
        quiet(voice.run, self.cfg, chunk_tokens=400)
        chunks = sorted(f for f in os.listdir(os.path.join(d, "chunks"))
                        if f.startswith("chunk-"))
        self.assertGreater(len(chunks), 1)
        body = "".join(verify._read(os.path.join(d, "chunks", c)) for c in chunks)
        # every conversation appears exactly once, none split
        for r in self.index:
            self.assertEqual(body.count(f"[[{r['file'][:-3]}]]"), 1, r["file"])
        quiet(voice.run, self.cfg)   # restore default chunking

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

    def test_owner_said_it_first_then_repeated_with_more_not_echo(self):
        # Regression (dry run): the owner's line, quoted back by the assistant,
        # then repeated with a reason added, was flagged as the assistant's.
        self.assertEqual(self._status(
            '> "I would rather be trusted with hard problems than be the one who '
            'owns them, because ownership is mostly admin to me."'),
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

    def test_plain_word_between_bold_spans_is_not_a_label(self):
        # Regression (dry run): "**Trap:** ... clicked ... **Why**" paired the
        # close of one bold span with the open of the next, so the plain word
        # "clicked" between them counted as a **clicked** label.
        self.assertEqual(self._status(
            '**Trap:** turn 3 is where he clicked through, see **Why**\n'
            '> "Map which of your goals are chosen versus inherited"'),
            [("not_authored", False)])

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
            config.load(os.path.join(ROOT, "said-it-first.example.toml"))
        self.assertEqual(err.getvalue(), "")


class LedgerAndPromote(unittest.TestCase):
    """Rerun memory and the promote gate, on a fresh workspace."""

    GOOD = """---
position-since: 2024-03
stability: provisional
source: chatgpt-synthesis
---

# Ambition as costume

> "I think I was confusing ambition with a specific costume of ambition."

*Sources:* [[2024-03-02-rethinking-the-founder-plan]]
"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        export = os.path.join(self.tmp, "conversations.json")
        with open(export, "w") as fh:
            json.dump(make_fixture.CONVERSATIONS, fh)
        cfg = copy.deepcopy(config.DEFAULTS)
        cfg["paths"] = {k: os.path.join(self.tmp, os.path.basename(v))
                        for k, v in cfg["paths"].items()}
        cfg["parse"]["timezone"] = "UTC"
        self.cfg = cfg
        quiet(parse.run, export, cfg)
        quiet(voice.run, cfg)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _titles(self):
        return {r["title"]: r for r in quiet(rank.run, self.cfg, force=True)}

    def _stage(self, name, text):
        d = os.path.join(self.tmp, "staged")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, name)
        with open(p, "w") as fh:
            fh.write(text)
        return p

    # --- ledger -----------------------------------------------------------

    def test_ticked_rows_skipped_next_run(self):
        self.assertIn("Rethinking the founder plan", self._titles())
        sl = self.cfg["paths"]["shortlist"]
        with open(sl) as fh:
            lines = fh.read().split("\n")
        lines = [l.replace("| [ ] |", "| [x] |", 1)
                 if "rethinking-the-founder-plan" in l and "branch" not in l else l
                 for l in lines]
        with open(sl, "w") as fh:
            fh.write("\n".join(lines))
        self.assertGreaterEqual(quiet(ledger.sync, self.cfg), 1)
        self.assertNotIn("Rethinking the founder plan", self._titles())

    def test_continued_conversation_comes_back(self):
        quiet(ledger.mark_stems, self.cfg, ["2024-03-02-rethinking-the-founder-plan"], "reviewed")
        led = ledger.load(self.cfg)
        for v in led["conversations"].values():
            v["user_turns"] -= 1          # as if turns were added after review
        ledger.save(self.cfg, led)
        r = self._titles()["Rethinking the founder plan"]
        self.assertEqual(r["review_state"], "continued")

    def test_reviewed_left_out_of_chunks(self):
        quiet(ledger.mark_stems, self.cfg, ["2024-03-02-rethinking-the-founder-plan"], "reviewed")
        quiet(voice.run, self.cfg)
        d = os.path.join(self.cfg["paths"]["archive"], "voice")
        body = "".join(verify._read(os.path.join(d, "chunks", c))
                       for c in os.listdir(os.path.join(d, "chunks")))
        self.assertNotIn("[[2024-03-02-rethinking-the-founder-plan]]", body)
        self.assertIn("[[2024-03-02-rethinking-the-founder-plan]]",
                      verify._read(os.path.join(d, "2024.md")))

    def test_include_reviewed_flag(self):
        quiet(ledger.mark_stems, self.cfg, ["2024-03-02-rethinking-the-founder-plan"], "reviewed")
        rows = quiet(rank.run, self.cfg, force=True, include_reviewed=True)
        self.assertIn("Rethinking the founder plan", {r["title"] for r in rows})

    # --- promote ----------------------------------------------------------

    def _notes(self):
        d = self.cfg["paths"]["notes"]
        return sorted(os.listdir(d)) if os.path.isdir(d) else []

    def test_good_note_promoted_and_ledgered(self):
        p = self._stage("ambition-as-costume.md", self.GOOD)
        self.assertEqual(quiet(promote.run, self.cfg, [p]), 0)
        self.assertEqual(self._notes(), ["ambition-as-costume.md"])
        statuses = {v["status"] for v in ledger.load(self.cfg)["conversations"].values()}
        self.assertEqual(statuses, {"promoted"})

    def test_note_failing_verify_refused(self):
        bad = self.GOOD.replace("I think I was confusing ambition with a specific costume of ambition.",
                                "I realized I had mistaken ambition for one particular costume of it.")
        p = self._stage("bad.md", bad)
        self.assertEqual(quiet(promote.run, self.cfg, [p]), 1)
        self.assertEqual(self._notes(), [])

    def test_note_without_sources_refused(self):
        p = self._stage("nosrc.md", self.GOOD.replace("*Sources:*", "See also:"))
        self.assertEqual(quiet(promote.run, self.cfg, [p]), 1)

    def test_note_citing_missing_conversation_refused(self):
        p = self._stage("ghost.md", self.GOOD + "*Sources:* [[2020-01-01-never-happened]]\n")
        self.assertEqual(quiet(promote.run, self.cfg, [p]), 1)

    def test_existing_note_needs_replace(self):
        p = self._stage("ambition-as-costume.md", self.GOOD)
        quiet(promote.run, self.cfg, [p])
        self.assertEqual(quiet(promote.run, self.cfg, [p]), 1)
        self.assertEqual(quiet(promote.run, self.cfg, [p], replace=True), 0)

    def test_check_only_writes_nothing(self):
        p = self._stage("ambition-as-costume.md", self.GOOD)
        self.assertEqual(quiet(promote.run, self.cfg, [p], check_only=True), 0)
        self.assertEqual(self._notes(), [])


class ExportFormat(unittest.TestCase):
    """The export format is undocumented and drifts. A change must fail
    loudly, never parse cleanly with less of the owner's text in it."""

    def _convos(self):
        return copy.deepcopy(make_fixture.CONVERSATIONS)

    def _user_nodes(self, convos):
        for c in convos:
            for n in c["mapping"].values():
                m = n.get("message")
                if m and m["author"]["role"] == "user":
                    yield m

    def test_fixture_is_clean(self):
        errors, warnings, stats = schema.validate(self._convos())
        self.assertEqual((errors, warnings), ([], []))
        self.assertGreater(stats["user_messages_with_text"], 0)

    def test_expected_drops_do_not_warn(self):
        convos = self._convos()
        c = convos[0]
        c["mapping"]["t"] = {"id": "t", "parent": None, "message": {
            "author": {"role": "assistant"},
            "content": {"content_type": "thoughts", "thoughts": []}}}
        self.assertEqual(schema.validate(convos)[1], [])

    def test_unknown_user_content_type_warns_with_words(self):
        convos = self._convos()
        for m in self._user_nodes(convos[:3]):
            m["content"]["content_type"] = "rich_text_v2"
        errors, warnings, _ = schema.validate(convos)
        self.assertEqual(errors, [])
        self.assertTrue(any(w.startswith("USER TEXT DROPPED") and "rich_text_v2" in w
                            for w in warnings), warnings)

    def test_every_user_type_changed_is_an_error(self):
        convos = self._convos()
        for m in self._user_nodes(convos):
            m["content"]["content_type"] = "rich_text_v2"
        errors, _, _ = schema.validate(convos)
        self.assertTrue(any("no user message with text" in e for e in errors))

    def test_non_list_export_is_an_error(self):
        errors, _, _ = schema.validate({"conversations": self._convos()})
        self.assertTrue(errors)

    def test_missing_mapping_is_an_error(self):
        convos = self._convos()
        for c in convos:
            c["messages"] = c.pop("mapping")
        errors, _, _ = schema.validate(convos)
        self.assertTrue(any("mapping" in e for e in errors))

    def test_parse_refuses_and_writes_nothing(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        export = os.path.join(tmp, "conversations.json")
        convos = self._convos()
        for m in self._user_nodes(convos):
            m["content"]["content_type"] = "rich_text_v2"
        with open(export, "w") as fh:
            json.dump(convos, fh)
        cfg = copy.deepcopy(config.DEFAULTS)
        cfg["paths"]["archive"] = os.path.join(tmp, "archive")
        with self.assertRaises(SystemExit):
            quiet(parse.run, export, cfg)
        self.assertFalse(os.path.exists(cfg["paths"]["archive"]))

    def test_strict_fails_on_warnings(self):
        convos = self._convos()
        next(self._user_nodes(convos))["content"]["content_type"] = "rich_text_v2"
        with self.assertRaises(SystemExit):
            quiet(schema.check, convos, strict=True)
        quiet(schema.check, convos)   # not strict: warns, continues

    def test_shard_that_is_not_a_list_is_refused(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        with open(os.path.join(tmp, "conversations-000.json"), "w") as fh:
            json.dump({"a": 1}, fh)
        with self.assertRaises(SystemExit):
            quiet(parse.load_conversations, tmp)

    def test_missing_current_node_without_children_keys(self):
        # Real exports carry no `children`; the fallback must use parents.
        c = copy.deepcopy(make_fixture.CONVERSATIONS[0])
        want = [t["text"] for t in parse.linearize(c)]
        c.pop("current_node")
        for n in c["mapping"].values():
            n.pop("children", None)
        self.assertEqual([t["text"] for t in parse.linearize(c)], want)


if __name__ == "__main__":
    unittest.main()
