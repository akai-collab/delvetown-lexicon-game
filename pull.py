"""Read a turn's replies off the town and say what belongs in the book.

The Quiet Year taught the same lesson this tool is built around: the tagged roots are only a signpost,
and the play happens in the untagged replies. So pull reads the thread under the turn's opener, takes
replies, and separates entries from chatter by shape — an entry has a title of its own and at least one
[[link]]; a sentence does not.

Nothing is written unless you say --write, and nothing is written that this tool is not sure about. Every
post it leaves out is printed with the reason, one line, so a person can look at the ones that were close.

    pull.py --game candles --post at://…/3mz…            # triage only
    pull.py --game candles --post at://…/3mz… --write     # entries into articles/, joins onto the roster

Reading uses the town's logged-out thread view, so it needs no session and no key.
"""
import argparse
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

import lexicon as lx

APPVIEW = "https://api.delve.town"
HANDLE_SUFFIX = ".delve.town"


def fetch_thread(uri: str, depth: int = 8, breadth: int = 50) -> list[dict]:
    q = urllib.parse.urlencode({"anchor": uri, "above": "false", "below": str(depth),
                                "branchingFactor": str(breadth), "sort": "old"})
    with urllib.request.urlopen(f"{APPVIEW}/xrpc/town.delve.unspecced.getPostThreadV2?{q}", timeout=30) as fh:
        body = json.load(fh)
    out = []
    for item in body.get("thread") or []:
        post = (item.get("value") or {}).get("post") or {}
        if not post or (item.get("depth") or 0) <= 0:
            continue
        rec = post.get("record") or {}
        out.append({"uri": post.get("uri"), "handle": (post.get("author") or {}).get("handle", ""),
                    "text": (rec.get("text") or "").strip(), "at": rec.get("createdAt", "")})
    return out


def title_of(text: str):
    """The entry's own name, or None when the post does not carry one.

    Same reading as the import script: a bold header, or a caps run before a dash or colon. A post that
    opens with a sentence has no title, and a post without a title is not an entry, however good it is.
    """
    m = re.search(r"\*\*([^*\n]{3,80})\*\*", text)
    if m:
        return m.group(1).strip().rstrip(".:").strip()
    m = re.search(r"(?:^|[.!?]\s+)([A-Z][A-Z0-9' ,&\-]{3,80}?)\s*[—:]", text)
    if m:
        return m.group(1).strip()
    return None


def cites(text: str) -> list[str]:
    seen = []
    for m in re.finditer(r"\[\[([^\]\n]{1,80})\]\]", text):
        t = m.group(1).strip()
        if t and t not in seen:
            seen.append(t)
    return seen


JOIN_WORDS = r"\bjoin\b|\btaking a seat\b|\bcount me in\b|\bi'?m in\b|\bsign me up\b"


def is_join(text: str) -> bool:
    """A join is a reply that says lexicon and asks for a place — in the words people actually use.

    penny joined the town's game on 2026-11-05 with "taking a seat", which a strict reading of "join" would
    have dropped; the cost of that is a player who thinks they are in and whose handle never gets tagged.
    So the test is a short list of phrasings rather than one word, and pull still prints every join it finds
    before --write does anything with it.
    """
    return bool(re.search(JOIN_WORDS, text, re.I)) and "lexicon" in text.lower()


def handle_to_player(handle: str) -> str:
    return handle[:-len(HANDLE_SUFFIX)] if handle.endswith(HANDLE_SUFFIX) else handle.split(".")[0]


def classify(replies, roster, turn, letters, ignore):
    """Sort replies into takes, joins, dupes and skips. Pure: no files, no network, so it can be tested.

    The rules are the game's, not the tool's: an entry has a title of its own, cites at least one thing,
    and files under the turn's letter. Everything else is printed with a reason and left alone.
    """
    takes, joins, skips, dupes = [], [], [], []
    by_author = {}
    for r in replies:
        player = roster.get(r["handle"])
        title = title_of(r["text"])
        refs = cites(r["text"])
        if player is None:
            if is_join(r["text"]):
                joins.append(r)
            elif title and refs:
                skips.append((r, "an entry, but this account is not on the roster — ask it to join"))
            else:
                skips.append((r, "not on the roster, not a join"))
            continue
        if not title:
            skips.append((r, "no title line — chatter, however good"))
            continue
        if not refs:
            skips.append((r, "'%s' cites nothing — an entry needs a [[link]] at least" % title))
            continue
        if lx.letter_of(title, ignore) not in letters:
            skips.append((r, "'%s' files under %s; turn %d is %s"
                          % (title, lx.letter_of(title, ignore), turn, letters)))
            continue
        by_author.setdefault(player, []).append((r, title, refs))

    for player, got in by_author.items():
        if len(got) > 1:
            dupes.append((player, got))
            continue
        takes.append((got[0][0], got[0][1], got[0][2], player))
    return takes, joins, skips, dupes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="triage a turn's replies into entries, joins and chatter")
    ap.add_argument("--game", required=True)
    ap.add_argument("--post", required=True, help="the turn's opener: an at-uri or the bare rkey")
    ap.add_argument("--did", default="", help="the opener's DID, if you would rather pass a bare rkey")
    ap.add_argument("--depth", type=int, default=8)
    ap.add_argument("--write", action="store_true", help="write the takes; the rest is still only printed")
    args = ap.parse_args(argv)

    game_dir = lx.pick_game(args.game)
    game = lx.load_game(game_dir)
    turn = game["turn"]
    letters = lx.turn_letters(game, turn)
    roster = {p["handle"]: p["player"] for p in game["players"] if p.get("handle")}
    ignore = (game.get("rules") or {}).get("ignore_leading") or []

    uri = args.post
    if not uri.startswith("at://"):
        if not args.did:
            print("the appview needs the whole at:// uri. Give one, or a bare rkey with --did <the opener's did>.")
            return 1
        uri = "at://%s/town.delve.feed.post/%s" % (args.did, uri)

    replies = fetch_thread(uri, args.depth)
    if not replies:
        print("no replies under that post yet")
        return 0

    takes, joins, skips, dupes = classify(replies, roster, turn, letters, ignore)

    for r, title, refs, player in takes:
        print("take: %-34s %-10s turn %d  cites %s" % (title[:34], player, turn, ", ".join(refs[:3])))
    for r in joins:
        print("join: %-34s (%s)" % (r["handle"], r["text"].replace("\n", " ")[:60]))
    for player, got in dupes:
        print("dupe: %s wrote %d entries this turn (%s) — pick one; none were taken"
              % (player, len(got), ", ".join("'%s'" % t for _, t, _ in got)))
    for r, why in skips:
        print("skip: %-34s %s" % (r["handle"], why))

    print("\n%d take, %d join, %d dupe, %d skip%s"
          % (len(takes), len(joins), len(dupes), len(skips), "" if args.write else "  (dry run)"))

    if args.write:
        for r, title, refs, player in takes:
            path = game_dir / "articles" / (lx.key(title) + ".md")
            path.write_text("---\ntitle: %s\nauthor: %s\nturn: %d\n---\n\n%s\n" % (title, player, turn, r["text"]),
                            encoding="utf-8")
            print("wrote %s" % path.relative_to(lx.ROOT))
        for r in joins:
            player = handle_to_player(r["handle"])
            if any(p["player"] == player for p in game["players"]):
                continue
            game["players"].append({"player": player, "handle": r["handle"]})
            print("joined %s (%s)" % (player, r["handle"]))
        lx.save_game(game_dir, game)

    return 0


if __name__ == "__main__":
    sys.exit(main())
