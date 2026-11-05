"""The rules of a Lexicon turn, checked without git or the network: python3 -m unittest discover -s tests"""

import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import lexicon as lx  # noqa: E402


def game(turn=1, letters=None, **rules):
    return {"name": "t", "players": [{"player": "ana", "handle": "ana.delve.town"}, {"player": "bo"},
                                     {"player": "cy"}],
            "letters": letters or lx.LETTERS, "rules": {**lx.DEFAULT_RULES, **rules}, "turn": turn, "history": []}


def entry(title, author, turn, *cites):
    body = " ".join(f"[[{c}]]" for c in cites)
    return lx.Entry(title, author, turn, body, pathlib.Path(f"{lx.key(title)}.md"), list(cites))


def problems(g, entries):
    return lx.check(g, entries)[0]


class TurnOne(unittest.TestCase):
    def test_two_phantoms_pass(self):
        self.assertEqual(problems(game(), [entry("Ash Tithe", "ana", 1, "Bell Road", "Cold Ledger")]), [])

    def test_one_phantom_is_not_enough(self):
        p = problems(game(), [entry("Ash Tithe", "ana", 1, "Bell Road")])
        self.assertTrue(any("needs 2 phantom" in x for x in p), p)

    def test_the_title_must_take_the_turns_letter_after_a_leading_article(self):
        self.assertEqual(problems(game(), [entry("The Ash Tithe", "ana", 1, "Bell Road", "Cold Ledger")]), [])
        p = problems(game(), [entry("Bell Road", "ana", 1, "Cold Ledger", "Dun Gate")])
        self.assertTrue(any("does not start with A" in x for x in p), p)


class LaterTurns(unittest.TestCase):
    def setUp(self):
        self.t1 = [entry("Ash Tithe", "ana", 1, "Bell Road", "Cold Ledger"),
                   entry("Amber Well", "bo", 1, "Bell Road", "Dun Gate")]

    def test_a_good_turn_two(self):
        e = entry("Bell Road", "cy", 2, "Amber Well", "Eel Market")
        self.assertEqual(problems(game(2), self.t1 + [e]), [])

    def test_turn_two_must_cite_something_written(self):
        p = problems(game(2), self.t1 + [entry("Bell Road", "cy", 2, "Eel Market")])
        self.assertTrue(any("earlier turns, has 0" in x for x in p), p)

    def test_turn_two_must_add_a_new_phantom_not_reuse_one(self):
        p = problems(game(2), self.t1 + [entry("Bell Road", "cy", 2, "Amber Well", "Cold Ledger")])
        self.assertTrue(any("new phantom" in x for x in p), p)

    def test_no_citing_your_own_entry(self):
        p = problems(game(2), self.t1 + [entry("Bell Road", "cy", 2, "Amber Well", "Eel Market"),
                                         entry("Brass Key", "ana", 2, "Ash Tithe", "Fen Lamp")])
        self.assertTrue(any("which ana wrote" in x for x in p), p)

    def test_you_may_not_write_a_phantom_you_cited(self):
        p = problems(game(2), self.t1 + [entry("Bell Road", "ana", 2, "Amber Well", "Eel Market")])
        self.assertTrue(any("ana cited 'Bell Road' as a phantom" in x for x in p), p)

    def test_a_phantom_under_a_passed_letter_can_never_be_written(self):
        later = [entry("Bell Road", "cy", 2, "Amber Well", "Eel Market"),
                 entry("Cold Ledger", "bo", 3, "Bell Road", "Bone Mill")]
        p = problems(game(3), self.t1 + later)
        self.assertTrue(any("'Bone Mill' files under a letter whose turn has passed" in x for x in p), p)

    def test_same_turn_citations_are_off_by_default(self):
        two = [entry("Bell Road", "cy", 2, "Amber Well", "Eel Market"),
               entry("Brass Key", "bo", 2, "Bell Road", "Ash Tithe", "Fen Lamp")]
        self.assertTrue(any("same turn" in x for x in problems(game(2), self.t1 + two)))
        self.assertEqual(problems(game(2, cite_same_turn=True), self.t1 + two), [])

    def test_the_last_turn_needs_no_phantom(self):
        t1 = [entry("Ash Tithe", "ana", 1, "Bell Road", "Brass Key")]
        e = entry("Bell Road", "cy", 2, "Ash Tithe")
        self.assertEqual(problems(game(2, ["A", "B"]), t1 + [e]), [])

    def test_a_grouped_turn_takes_any_of_its_letters(self):
        letters = ["A", "XYZ"]
        e = entry("Bell Road", "cy", 2, "Amber Well")
        self.assertTrue(problems(game(2, letters), self.t1 + [e]))
        t1 = [entry("Ash Tithe", "ana", 1, "Yew Court", "Zinc Bell")]
        self.assertEqual(problems(game(2, letters), t1 + [entry("Yew Court", "bo", 2, "Ash Tithe")]), [])


class Bookkeeping(unittest.TestCase):
    def test_one_title_one_entry_whatever_the_spelling(self):
        p = problems(game(), [entry("Ash Tithe", "ana", 1, "Bell Road", "Cold Ledger"),
                              entry("ash  tithe", "bo", 1, "Bell Road", "Dun Gate")])
        self.assertTrue(any("already written" in x for x in p), p)

    def test_one_entry_per_player_per_turn(self):
        p = problems(game(), [entry("Ash Tithe", "ana", 1, "Bell Road", "Cold Ledger"),
                              entry("Amber Well", "ana", 1, "Bell Road", "Dun Gate")])
        self.assertTrue(any("already wrote" in x for x in p), p)

    def test_a_turn_that_is_not_open_yet(self):
        p = problems(game(1), [entry("Bell Road", "ana", 2, "Ash Tithe", "Cold Ledger")])
        self.assertTrue(any("not open yet" in x for x in p), p)

    def test_strangers_are_refused(self):
        p = problems(game(), [entry("Ash Tithe", "zed", 1, "Bell Road", "Cold Ledger")])
        self.assertTrue(any("not a player" in x for x in p), p)

    def test_status_names_who_owes_and_what_is_claimable(self):
        es = [entry("Ash Tithe", "ana", 1, "Bell Road", "Cold Ledger"), entry("Amber Well", "bo", 1, "Bell Road")]
        s = lx.status(game(), es)
        self.assertEqual(s["owing"], ["cy"])
        s2 = lx.status(game(2), es)
        self.assertEqual(s2["claimable"], {"Bell Road": ["ana", "bo"]})

    def test_the_opener_tags_who_still_owes(self):
        text = lx.opener(game(), [entry("Amber Well", "bo", 1, "Bell Road", "Cold Ledger")], "https://x")
        self.assertIn("Turn 1, the letter A", text)
        self.assertIn("@ana.delve.town cy", text)
        self.assertNotIn("bo", text.split("Still to write:")[1])

    def test_fold_records_the_missed_and_advances(self):
        g, line = lx.fold(game(), [entry("Ash Tithe", "ana", 1, "Bell Road", "Cold Ledger")])
        self.assertEqual(g["turn"], 2)
        self.assertEqual(g["history"], [{"turn": 1, "letters": "A", "written": ["ana"], "missed": ["bo", "cy"]}])
        self.assertIn("missed: bo, cy", line)

    def test_fold_refuses_a_turn_that_does_not_check(self):
        with self.assertRaises(ValueError):
            lx.fold(game(), [entry("Ash Tithe", "ana", 1)])

    def test_the_index_shows_written_and_unwritten(self):
        md = lx.index_md(game(), [entry("Ash Tithe", "ana", 1, "Bell Road", "Cold Ledger")])
        self.assertIn("[Ash Tithe](articles/ash-tithe.md) — ana, turn 1", md)
        self.assertIn("*Bell Road* — unwritten, cited by ana", md)


class CommandLine(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = lx.main(list(argv))
        return code, out.getvalue()

    def test_a_whole_turn_through_the_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, lx.GAMES, lx.ROOT = (lx.GAMES, lx.ROOT), pathlib.Path(tmp) / "games", pathlib.Path(tmp)
            try:
                self.assertEqual(self.run_cli("new-game", "g", "--players", "ana:ana.x,bo")[0], 0)
                code, out = self.run_cli("new", "--author", "ana", "--title", "Bell Road")
                self.assertEqual(code, 1)
                self.assertIn("turn 1 is A", out)
                self.run_cli("new", "--author", "ana", "--title", "Ash Tithe")
                path = lx.GAMES / "g" / "articles" / "ash-tithe.md"
                self.assertEqual(self.run_cli("check")[0], 1)          # the scaffold cites nothing yet
                path.write_text(path.read_text().replace("Write the entry here.",
                                                         "Paid at [[Bell Road]] to the [[Cold Ledger]]."))
                code, out = self.run_cli("check")
                self.assertEqual(code, 0, out)
                code, out = self.run_cli("fold")
                self.assertIn("missed: bo", out)
                g = json.loads((lx.GAMES / "g" / "game.json").read_text())
                self.assertEqual(g["turn"], 2)
                self.assertIn("Bell Road", (lx.GAMES / "g" / "INDEX.md").read_text())
            finally:
                lx.GAMES, lx.ROOT = old


if __name__ == "__main__":
    unittest.main()
