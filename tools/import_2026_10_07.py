"""Import the 7 October Lexicon game from the town dump into this repo.

The game was played in the feed, one sitting, on 2026-10-07: elsyian opened it as a variant of
Krishnaswami's Lexicon, and the entries were posted as individual posts. This writes them out as
games/lexicon-2026-10-07/: one markdown file per entry, frontmatter and all, plus the game.json that
the tool reads. Nothing is invented: titles come from the entries' own headers, authors from their
posts, and a post that is not an entry is not imported.
"""
import json
import os
import pathlib
import re

DUMP = os.path.expanduser("~/delve-dump/posts-all.jsonl")
WINDOW = os.path.expanduser("~/.local/state/delvetown-dt/town-window-skillissue.jsonl")
OUT = pathlib.Path(__file__).resolve().parent.parent / "games" / "lexicon-2026-10-07"

# The entries, by rkey, in the order they were posted. Chosen by hand from the 7 October thread: each
# carries a bold header and at least one [[link]], and each was posted by a player rather than the chair.
ENTRIES = [
    ("3mxbbsqyq6q2a", "inkling"),
    ("3mxbbtmnbty2a", "grok"),
    ("3mxbbtv6rsi2a", "mimo"),
    ("3mxbbumjchy2a", "selene"),
    ("3mxbc7jfswc2x", "fieldnote"),
    ("3mxbcdvktmy2a", "selene"),
    ("3mxbcqkfzzy2a", "grok"),
    ("3mxbcuvgqgq2a", "selene"),
    ("3mxbcxefsbf22", "penny"),
    ("3mxbd3ijfty2a", "selene"),
    ("3mxbelcv25e2l", "astral"),
]

HANDLES = {
    "inkling": "inkling.delve.town",
    "grok": "grok.delve.town",
    "mimo": "mimo.delve.town",
    "selene": "selene.delve.town",
    "fieldnote": "fieldnote.delve.town",
    "penny": "penny.hailey.at",
    "astral": "astral100.bsky.social",
}


def load():
    rows = {}
    for f in (DUMP, WINDOW):
        if not os.path.exists(f):
            continue
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("uri"):
                rows[r["uri"].rsplit("/", 1)[-1]] = r
    return rows


def title_of(text):
    """The entry's own name: the bold header, a caps line before a dash or colon, or the name inside a sentence.

    One entry was posted late and opens "Late, out of competition. THE GRAPE ROT OF 2038:" — its name is
    the caps run inside the first sentence, not the sentence.
    """
    m = re.search(r"\*\*([^*]{3,80})\*\*", text)
    if m:
        return m.group(1).strip().rstrip(".:").strip()
    m = re.search(r"(?:^|[.!?]\s+)([A-Z][A-Z0-9' ,&\-]{3,80}?)\s*[—:]", text)
    if m:
        return m.group(1).strip()
    return text.strip().split("\n", 1)[0][:60].strip()


def slug(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "entry"


def main():
    rows = load()
    (OUT / "articles").mkdir(parents=True, exist_ok=True)
    written = []
    for rkey, author in ENTRIES:
        row = rows.get(rkey)
        if not row:
            print("missing from the copy:", rkey)
            continue
        text = (row.get("text") or "").strip()
        title = title_of(text)
        path = OUT / "articles" / (slug(title) + ".md")
        body = text if text.rstrip().endswith(("*— " + author, author)) else text
        path.write_text(
            "---\ntitle: %s\nauthor: %s\nturn: 1\n---\n\n%s\n" % (title, author, body), encoding="utf-8")
        written.append({"title": title, "author": author, "rkey": rkey, "at": row.get("created_at")})
        print("%-40s %-10s %s" % (title[:40], author, slug(title)))

    order = []
    for w in written:
        if w["author"] not in order:
            order.append(w["author"])
    game = {
        "name": "lexicon-2026-10-07",
        "title": "Lexicon, 7 October 2026: an encyclopedia of the mid-late 21st century",
        "players": [{"player": p, "handle": HANDLES[p]} for p in order],
        "letters": ["A"],
        "rules": {
            # The town played a one-sitting variant: no letters, no turns, everybody writing at once and
            # citing whoever had already posted. The rules say that, so the checker does not ask this game
            # for a letter rotation it never had.
            "letters_in_play": False,
            "first_turn_phantoms": 0,
            "written_min": 1,
            "new_phantoms_min": 0,
            "cite_same_turn": True,
            "ignore_leading": ["the", "a", "an"],
        },
        "turn": 2,
        "history": [
            {"turn": 1, "letters": "A", "written": order, "missed": [],
             "note": "one sitting, 2026-10-07 06:08-06:57Z; chair: elsyian.delve.town"},
        ],
    }
    (OUT / "game.json").write_text(json.dumps(game, indent=2) + "\n", encoding="utf-8")
    print("\nwrote %s with %d entries and %d players" % (OUT, len(written), len(order)))


if __name__ == "__main__":
    main()
