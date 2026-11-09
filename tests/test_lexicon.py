"""The rules of a Lexicon turn, checked without git or the network: python3 -m unittest discover -s tests"""

import contextlib
import importlib.util
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


class OneSitting(unittest.TestCase):
    """The 7 October variant: no letters, no turn rotation, one author may write several entries."""

    def test_letters_out_of_play_lets_any_initial_through(self):
        g = game(letters=["A"], letters_in_play=False, first_turn_phantoms=0)
        self.assertEqual(problems(g, [entry("Bell Road", "ana", 1, "Cold Ledger")]), [])

    def test_letters_out_of_play_lets_one_author_write_twice_in_a_turn(self):
        g = game(letters=["A"], letters_in_play=False, first_turn_phantoms=0)
        got = problems(g, [entry("Bell Road", "ana", 1, "Cold Ledger"),
                           entry("Cold Ledger", "ana", 1, "Bell Road")])
        self.assertFalse(any("already wrote" in x for x in got), got)

    def test_a_phantom_is_still_caught_when_letters_decide_turns(self):
        g = game(letters=["A"], first_turn_phantoms=0)
        got = problems(g, [entry("Bell Road", "ana", 1, "Cold Ledger")])
        self.assertTrue(any("does not start with A" in x for x in got), got)


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

    def test_the_turn_one_opener_says_a_phantom_must_take_a_later_letter(self):
        text = lx.opener(game(), [entry("Amber Well", "bo", 1, "Bell Road", "Cold Ledger")])
        self.assertIn("later than A", text)
        self.assertIn("its turn never arrives", text)

    def test_a_later_opener_says_a_new_phantom_must_take_a_later_letter(self):
        es = [entry("Ash Tithe", "ana", 1, "Bell Road", "Cold Ledger"), entry("Bell Road", "bo", 2, "Ash Tithe")]
        text = lx.opener(game(3), es)
        self.assertIn("later than C", text)
        self.assertIn("already had its turn", text)

    def test_the_opener_says_when_the_turn_closes_in_utc_and_nothing_else(self):
        g = game()
        g["schedule"] = {"hours_per_turn": 48, "turns": [{"letter": "A", "opens": "2026-11-06T18:00:00Z"}]}
        text = lx.opener(g, [])
        self.assertIn("Closes 2026-11-08T18:00Z.", text)
        self.assertNotIn("CET", text)
        self.assertNotIn("(19:00", text)

    def test_an_opener_without_a_schedule_still_opens(self):
        self.assertNotIn("Closes", lx.opener(game(), []))

    def test_a_muted_player_is_not_tagged_but_still_owes(self):
        g = game()
        g["muted"] = ["ana.delve.town"]           # the fixture only gives ana a handle
        es = [entry("Ash Tithe", "bo", 1, "Bell Road", "Cold Ledger")]
        text = lx.opener(g, es)
        self.assertIn("Still to write: cy", text)
        self.assertNotIn("@ana.delve.town", text)
        self.assertIn("ana", lx.status(g, es)["owing"])

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

    def test_the_graph_text_marks_the_unwritten(self):
        es = [entry("Ash Tithe", "ana", 1, "Bell Road", "Cold Ledger"),
              entry("Bell Road", "cy", 2, "Ash Tithe", "Eel Market")]
        md = lx.graph_md(game(2), es)
        self.assertIn("![The citation map", md)
        self.assertIn("- **Bell Road** (cy, turn 2) cites Ash Tithe, *Eel Market*", md)
        self.assertNotIn("```", md, "no diagram syntax: Tangled shows code blocks as text")
        self.assertNotIn("![", lx.graph_md(game(2), es, has_image=False))


@unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is not installed")
class Picture(unittest.TestCase):
    def setUp(self):
        import graph
        self.graph = graph
        self.es = [entry("Ash Tithe", "ana", 1, "Bell Road", "Cold Ledger"),
                   entry("Amber Well", "bo", 1, "Bell Road", "Dun Gate"),
                   entry("Bell Road", "cy", 2, "Ash Tithe", "Eel Market")]

    def test_columns_are_turns_and_phantoms_sit_under_their_letter(self):
        plan = self.graph.layout(game(2), self.es)
        n = plan["nodes"]
        self.assertEqual(plan["turns"], [1, 2, 3, 4, 5])
        self.assertEqual((n["ash-tithe"]["col"], n["bell-road"]["col"], n["dun-gate"]["col"]), (0, 1, 3))
        self.assertTrue(n["bell-road"]["written"])
        self.assertFalse(n["eel-market"]["written"])
        self.assertIn(("bell-road", "ash-tithe", "cy"), plan["edges"])

    def test_a_long_arrow_gets_a_slot_in_every_column_it_crosses(self):
        plan = self.graph.layout(game(2), self.es)
        chain = next(c for c, a in plan["paths"] if c[0] == "amber-well" and c[-1] == "dun-gate")
        self.assertEqual(len(chain), 4, "A to D passes through B and C")
        n = plan["nodes"]
        self.assertEqual([n[k]["col"] for k in chain], [0, 1, 2, 3])
        self.assertTrue(all(n[k].get("waypoint") for k in chain[1:-1]))

    def test_it_draws_a_png_and_draws_it_the_same_twice(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = self.graph.render(game(2), self.es, pathlib.Path(tmp) / "a.png")
            b = self.graph.render(game(2), self.es, pathlib.Path(tmp) / "b.png")
            self.assertEqual(a.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(a.read_bytes(), b.read_bytes(), "same files, same picture: no churn in git")

    def test_an_empty_game_still_draws(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(self.graph.render(game(), [], pathlib.Path(tmp) / "g.png").exists())

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
                self.assertIn("- **Ash Tithe** (ana, turn 1) cites *Bell Road*", (lx.GAMES / "g" / "GRAPH.md").read_text())
            finally:
                lx.GAMES, lx.ROOT = old


if __name__ == "__main__":
    unittest.main()
