"""pull.py: what counts as an entry, and what is only a reply.

The town writes entries as replies with a title of their own and [[links]] in the body; everything else in
the thread is conversation. These tests pin that reading, because getting it wrong puts chatter in the book
or leaves a real entry out, and both are worse than asking a person.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import pull  # noqa: E402

ROSTER = {"ana.delve.town": "ana", "bo.delve.town": "bo"}


def r(handle, text):
    return {"handle": handle, "text": text, "uri": "at://x/" + handle + "/1", "at": "2026-11-05T00:00:00Z"}


class Titles(unittest.TestCase):
    def test_a_bold_line_is_the_title(self):
        self.assertEqual(pull.title_of("**Ash Tithe**\n\nA road of ash, see [[Bell Road]]."), "Ash Tithe")

    def test_a_caps_line_before_a_dash_is_the_title(self):
        self.assertEqual(pull.title_of("GARDEN-STATE RECORDS — a music imprint. [[Busan Stack]]"), "GARDEN-STATE RECORDS")

    def test_a_sentence_has_no_title(self):
        self.assertIsNone(pull.title_of("wait, are we doing B or C? lol"))

    def test_a_late_entry_still_has_one(self):
        self.assertEqual(pull.title_of("Late, out of competition. THE GRAPE ROT OF 2038: six tonnes. [[Ash Tithe]]"),
                         "THE GRAPE ROT OF 2038")


class Citations(unittest.TestCase):
    def test_links_are_read_once_each_in_order(self):
        self.assertEqual(pull.cites("[[B]] then [[A]] then [[B]]"), ["B", "A"])

    def test_none_is_an_empty_list(self):
        self.assertEqual(pull.cites("no links here"), [])


class Joins(unittest.TestCase):
    def test_join_needs_both_words(self):
        self.assertTrue(pull.is_join("#lexicon join me in"))
        self.assertTrue(pull.is_join("I'd like to join the lexicon"))

    def test_taking_a_seat_is_joining(self):
        self.assertTrue(pull.is_join("#lexicon — taking a seat."))
        self.assertTrue(pull.is_join("count me in for the lexicon"))

    def test_mentioning_the_word_alone_is_not_joining(self):
        self.assertFalse(pull.is_join("the lexicon joinery is a nice phrase"))
        self.assertFalse(pull.is_join("#lexicon this is lovely"))


class Taking(unittest.TestCase):
    def test_an_entry_from_a_player_is_taken(self):
        takes, joins, skips, dupes = pull.classify(
            [r("ana.delve.town", "**Ash Tithe**\n\n[[Bell Road]] and [[Cold Ledger]].")], ROSTER, 1, "A", [])
        self.assertEqual([t[1] for t in takes], ["Ash Tithe"])
        self.assertEqual((joins, skips, dupes), ([], [], []))

    def test_chatter_is_skipped_with_a_reason(self):
        takes, _, skips, _ = pull.classify([r("ana.delve.town", "haha yes")], ROSTER, 1, "A", [])
        self.assertEqual(takes, [])
        self.assertIn("no title", skips[0][1])

    def test_a_title_under_the_wrong_letter_is_skipped(self):
        takes, _, skips, _ = pull.classify(
            [r("ana.delve.town", "**Bell Road**\n\n[[Ash Tithe]]")], ROSTER, 1, "A", [])
        self.assertEqual(takes, [])
        self.assertIn("files under B", skips[0][1])

    def test_an_entry_without_links_is_skipped(self):
        takes, _, skips, _ = pull.classify([r("ana.delve.town", "**Ash Tithe**\n\nA road, no links.")],
                                           ROSTER, 1, "A", [])
        self.assertEqual(takes, [])
        self.assertIn("cites nothing", skips[0][1])

    def test_two_entries_by_one_player_are_a_dupe_and_neither_is_taken(self):
        takes, _, _, dupes = pull.classify(
            [r("ana.delve.town", "**Ash Tithe**\n\n[[Bell Road]]"),
             r("ana.delve.town", "**Ash Road**\n\n[[Cold Ledger]]")], ROSTER, 1, "A", [])
        self.assertEqual(takes, [])
        self.assertEqual(len(dupes), 1)
        self.assertEqual(dupes[0][0], "ana")

    def test_a_stranger_writing_a_well_formed_entry_is_an_admit_not_a_skip(self):
        # juno filed a real entry in turn A without a join post (2026-11-07): the entry is the ask, so it
        # comes back marked for a hand admission rather than being dropped as "not on the roster".
        takes, joins, skips, _ = pull.classify(
            [r("cy.delve.town", "**Ash Tithe**\n\n[[Bell Road]]")], ROSTER, 1, "A", [])
        self.assertEqual(takes, [])
        self.assertEqual(skips, [])
        self.assertEqual(len(joins), 1)
        self.assertTrue(joins[0].get("_admit"))

    def test_a_bare_off_asks_not_to_be_tagged(self):
        _, _, skips, _ = pull.classify([r("ana.delve.town", "off")], ROSTER, 1, "A", [])
        self.assertIn("asks not to be tagged", skips[0][1])

    def test_a_stranger_asking_to_join_is_a_join(self):
        _, joins, _, _ = pull.classify([r("cy.delve.town", "#lexicon join please")], ROSTER, 1, "A", [])
        self.assertEqual(len(joins), 1)

    def test_a_join_from_a_retired_handle_is_not_a_join(self):
        # The signup post keeps its replies forever, so a retired player's old join came back as a join on
        # every roll and the desk re-announced the retirement each hour (retrofractal, 2026-11-11).
        _, joins, skips, _ = pull.classify([r("cy.delve.town", "#lexicon joining")], ROSTER, 1, "A", [],
                                           ["cy.delve.town"])
        self.assertEqual(joins, [])
        self.assertIn("retired", skips[0][1])

    def test_a_retired_handle_that_files_an_entry_is_still_an_admit(self):
        # Retired is not banned: an entry is the one admission this game has.
        _, joins, skips, _ = pull.classify([r("cy.delve.town", "**Ash Tithe**\n\n[[Bell Road]]")],
                                           ROSTER, 1, "A", [], ["cy.delve.town"])
        self.assertEqual(skips, [])
        self.assertTrue(joins and joins[0].get("_admit"))

    def test_leading_articles_are_ignored_when_reading_the_letter(self):
        takes, _, _, _ = pull.classify([r("ana.delve.town", "**The Ash Tithe**\n\n[[Bell Road]]")],
                                       ROSTER, 1, "A", ["the"])
        self.assertEqual([t[1] for t in takes], ["The Ash Tithe"])


if __name__ == "__main__":
    unittest.main()
