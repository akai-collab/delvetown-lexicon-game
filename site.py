#!/usr/bin/env python3
"""The public page: https://lexicon.pleroma.nexus/

One HTML file rendered from the game's own files and pushed to skizy's host. It adds no sentence of its
own: every title and every paragraph on the page is a player's, and every count is read off the articles
(`lexicon.py::phantoms` and the entry list), never typed in by hand.

    python3 site.py build              render build/index.html (+ a web-sized map) and stop
    python3 site.py build --upload     render and PUT index.html and graph-web.png to the site
    python3 site.py build --upload --map   also PUT the full-size graph.png

The key lives in ~/.hermes/.env as PLEROMA_KEY and is read by scripts/pleroma-publish.py, never here.
Building needs no Pillow unless the map has to be shrunk; shrinking does, so use ~/embed-venv/bin/python
for a build that regenerates graph-web.png.

What the page shows is what has been folded. An open turn appears only as a date: a page that carried
entries from a turn still in play would disagree with the book the moment somebody corrected one.
"""

import argparse
import datetime as _dt
import html
import pathlib
import re
import subprocess
import sys

import lexicon as lx

ROOT = pathlib.Path(__file__).resolve().parent
PUBLISH = pathlib.Path.home() / ".hermes" / "scripts" / "pleroma-publish.py"
SITE = "lexicon"
WEB_MAP_WIDTH = 1800

STYLE = """\
 :root { --ink:#e8e4dc; --dim:#9a948a; --bg:#14140f; --line:#33302a; --ph:#6f8f7a; --wr:#d8a75f; }
 body { background:var(--bg); color:var(--ink); font:17px/1.65 Georgia,serif;
        max-width:44rem; margin:0 auto; padding:2.5rem 1.25rem 5rem; }
 h1 { font-size:1.9rem; margin:0 0 .2rem; letter-spacing:.01em; }
 h2 { font-size:1.05rem; text-transform:uppercase; letter-spacing:.14em;
       color:var(--dim); border-top:1px solid var(--line); padding-top:1.4rem; margin:2.8rem 0 1rem; }
 h3 { font-size:1.15rem; margin:0 0 .15rem; }
 .lede, .by, .who, footer { color:var(--dim); }
 .by { font-size:.82rem; margin:0 0 .9rem; font-style:italic; }
 article { margin:0 0 2rem; }
 /* a citation to an entry written: amber, thin underline, and a link to the entry itself */
 .written { color:var(--wr); border-bottom:1px solid rgba(216,167,95,.4); text-decoration:none; }
 .written:hover, .written:focus { border-bottom-color:var(--wr); }
 .phantom { color:var(--ph); border-bottom:1px dashed var(--ph); }
 article:target h3 { color:var(--wr); }
 article:target { outline:1px solid rgba(216,167,95,.25); outline-offset:.6rem; }
 ul { padding-left:1.1rem; } li { margin:.25rem 0; }
 .who { font-size:.8rem; }
 .mapbox { overflow-x:auto; margin:1.4rem 0 .3rem; border:1px solid var(--line); }
 .map { display:block; cursor:zoom-in; }
 .map img { display:block; width:%(width)dpx; max-width:none; height:auto; }
 .cap { font-size:.78rem; color:var(--dim); margin:0 0 1.2rem; }
 footer { font-size:.8rem; margin-top:3rem; border-top:1px solid var(--line); padding-top:1rem; }
 a { color:var(--ink); }
""" % {"width": WEB_MAP_WIDTH}

SIGNATURE = re.compile(r"^\*—\s*(.+?)\*\s*$")
DATE_ONLY = "%Y-%m-%dT%H:%MZ"


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def paragraphs(body: str, written: set[str], signature: str) -> list[str]:
    """The entry as paragraphs, with every citation marked written or phantom.

    A trailing `*— author*` line is dropped: it is the bookkeeping the article file keeps, and the page
    already prints the author under the title.
    """
    blocks = [b.strip() for b in re.split(r"\n\s*\n", body.strip()) if b.strip()]
    if blocks and SIGNATURE.match(blocks[-1]):
        blocks = blocks[:-1]
    out = []
    for block in blocks:
        pieces, last = [], 0
        for m in lx.LINK.finditer(block):
            title = m.group(1).strip()
            k = lx.key(title)
            pieces.append(esc(block[last:m.start()]))
            if k in written:
                # A citation that has been made good is the entry's own address: amber, and a jump to it.
                pieces.append('<a class="written" href="#%s">%s</a>' % (k, esc(title)))
            else:
                pieces.append('<span class="phantom">%s</span>' % esc(title))
            last = m.end()
        pieces.append(esc(block[last:]))
        out.append("<p>%s</p>" % "".join(pieces).replace("\n", " "))
    return out


def build(game_dir: pathlib.Path) -> tuple[str, dict]:
    game = lx.load_game(game_dir)
    entries, problems = lx.load_entries(game_dir)
    if problems:
        for p in problems:
            print("  not parsed: " + p, file=sys.stderr)
    turn = game["turn"]
    letters = "/".join(lx.turn_letters(game, turn) or "?")
    closes = lx.closes_at(game, turn)
    opens = None
    for t in (game.get("schedule") or {}).get("turns") or []:
        if t.get("letter") in (lx.turn_letters(game, turn) or ""):
            opens = t.get("opens")

    written = {e.key for e in entries}
    phantoms = lx.phantoms(game, entries)

    # who promised each phantom, named by the entry that did it (a phantom can have several creditors)
    creditors: dict[str, list[str]] = {}
    for e in sorted(entries, key=lambda e: (e.turn, e.path.name)):
        for title in e.cites:
            if lx.key(title) in written:
                continue
            name = next((n for n in phantoms if lx.key(n) == lx.key(title)), title)
            who = "%s (%s)" % (e.title, e.author)
            if who not in creditors.setdefault(name, []):
                creditors[name].append(who)

    entries_sorted = sorted(entries, key=lambda e: e.title.lower())
    phantom_sorted = sorted(phantoms, key=lambda t: t.lower())

    last = (game.get("history") or [None])[-1]
    parts = []
    add = parts.append

    add("<!doctype html>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">")
    add("<title>Lexicon — turn %d, letter %s</title>" % (turn, letters))
    add("<style>\n%s</style>" % STYLE)
    add("<h1>The Lexicon</h1>")
    add('<p class="lede">A town dictionary, one letter per turn. Turn %d is the letter\n<b>%s</b> and closes %s.</p>'
        % (turn, esc(letters), closes.strftime(DATE_ONLY) if closes else "on no stated date"))
    add('<p class="lede">Entries are folded at the close, so what is below is what has been folded:\n%d entries, and %d names promised but not yet written. A name in\n<span class="phantom">green</span> is a phantom — someone built on it before anyone wrote it — and each\nphantom names the entry that made the promise. A name in\n<span class="written">amber</span> was a phantom that has since been written: it links to the entry, and\nevery citation of it jumps there. Because both lists are drawn from folded\ntext, a promise made in a reply that has not been folded yet appears here after the fold,\nnot before it.</p>'
        % (len(entries), len(phantoms)))
    add('<div class="mapbox"><a class="map" href="graph.png" title="Open the full-size map (%d x %d)">'
        % map_size(game_dir))
    add('<img src="graph-web.png" alt="The lexicon as a graph: %d written entries as solid boxes, %d phantoms as dashed ones, grouped by letter."></a></div>'
        % (len(entries), len(phantoms)))
    add('<p class="cap">The map, too wide to fit: drag sideways to pan, or click it for the full-size image.</p>')

    add("<h2>Folded entries (%d)</h2>" % len(entries))
    for e in entries_sorted:
        add('<article id="%s"><h3>%s</h3><p class="by">%s · turn %d</p>%s</article>'
            % (lx.key(e.title), esc(e.title), esc(e.author), e.turn,
               "".join(paragraphs(e.body, written, e.author))))

    add("<h2>Cited, not written (%d)</h2>" % len(phantoms))
    add("<ul>")
    for title in phantom_sorted:
        add("<li>%s <span class=\"who\">promised in %s</span></li>"
            % (esc(title), esc("; ".join(creditors.get(title, [])))))
    add("</ul>")

    add("<h2>Turn %d</h2>" % turn)
    line = "Letter %s, open %s, closes %s." % (esc(letters), opens or "no stated date",
                                              closes.strftime(DATE_ONLY) if closes else "no stated date")
    add('<p class="lede">%s\nNothing from this turn is folded yet; the entries above are the %d folded from earlier turns.'
        % (line, len(entries)))
    if last:
        filed = len(last.get("written") or [])
        missed = len(last.get("missed") or [])
        add(" Last folded turn: %s, with %d entries filed and %d player%s who filed nothing."
            % (last.get("letters", "?"), filed, missed, "" if missed == 1 else "s"))
    add("</p>")

    add("<footer>Built from the game's own files. Titles and text are the players' own,\n"
        "including their spelling. · %d entries · %s</footer>"
        % (len(entries), _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")))
    return "\n".join(parts) + "\n", {"entries": len(entries), "phantoms": len(phantoms)}


def map_size(game_dir: pathlib.Path) -> tuple[int, int]:
    import struct
    path = game_dir / "graph.png"
    try:
        data = path.read_bytes()[:33]
        if data[12:16] == b"IHDR":
            return struct.unpack(">II", data[16:24])
    except (FileNotFoundError, IndexError, struct.error):
        pass
    return (0, 0)


def shrink_map(game_dir: pathlib.Path, out: pathlib.Path) -> bool:
    """A web-sized copy, because the map is drawn ~7700 px wide for the forge."""
    try:
        from PIL import Image
    except ImportError:
        print("  no Pillow: graph-web.png not rebuilt (run with ~/embed-venv/bin/python)", file=sys.stderr)
        return False
    src = game_dir / "graph.png"
    if not src.exists():
        print("  no graph.png: run `lexicon.py index` first", file=sys.stderr)
        return False
    img = Image.open(src)
    if img.width > WEB_MAP_WIDTH:
        img = img.resize((WEB_MAP_WIDTH, round(img.height * WEB_MAP_WIDTH / img.width)), Image.LANCZOS)
    img.save(out)
    return True


def publish(local: pathlib.Path, remote: str) -> int:
    return subprocess.call([sys.executable, str(PUBLISH), "put", SITE, str(local), remote])


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["build"], nargs="?", default="build")
    ap.add_argument("--game", default="town")
    ap.add_argument("--game-dir", default=None, help="path to the game folder, overriding --game")
    ap.add_argument("--out", default=None, help="where to write the build (default build/)")
    ap.add_argument("--upload", action="store_true", help="PUT the page and the web map to the site")
    ap.add_argument("--map", action="store_true", help="also PUT the full-size graph.png")
    a = ap.parse_args(argv[1:])

    game_dir = pathlib.Path(a.game_dir) if a.game_dir else ROOT / "games" / a.game
    out = pathlib.Path(a.out) if a.out else ROOT / "build"
    out.mkdir(parents=True, exist_ok=True)

    page, counts = build(game_dir)
    target = out / "index.html"
    target.write_text(page, encoding="utf-8")
    print("wrote %s — %d entries, %d phantoms, %d bytes"
          % (target, counts["entries"], counts["phantoms"], len(page.encode("utf-8"))))

    web = out / "graph-web.png"
    made = shrink_map(game_dir, web)
    if made:
        print("wrote %s (%d bytes)" % (web, web.stat().st_size))

    if not a.upload:
        print("not uploaded; pass --upload to PUT it to https://%s.pleroma.nexus/" % SITE)
        return 0
    fails = 0
    fails += 1 if publish(target, "index.html") else 0
    if made:
        fails += 1 if publish(web, "graph-web.png") else 0
    if a.map and (game_dir / "graph.png").exists():
        fails += 1 if publish(game_dir / "graph.png", "graph.png") else 0
    print("upload done: %d failed" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
