#!/usr/bin/env python3
"""A Lexicon table kept in git: one markdown file per entry, checked on every pull request.

Each turn has a letter. Every player writes one entry whose title starts with that letter. An entry
cites other entries with [[Title]] links: some already written, some not yet written ("phantoms"),
which later turns must fill in. The rules a turn has to keep are in check(); the files are the game.

    python3 lexicon.py status            whose entries are in, who owes one, which phantoms are open
    python3 lexicon.py open              the post that opens the turn, for delve.town
    python3 lexicon.py new --author X --title "..."   start an entry file for the current turn
    python3 lexicon.py check             every rule over every entry; exit 1 on a problem
    python3 lexicon.py fold              close the turn: check, record who wrote and who missed, advance
    python3 lexicon.py index             rewrite INDEX.md, GRAPH.md and graph.png (the citation map)
    python3 lexicon.py new-game NAME --players a:a.delve.town,b:b.delve.town

Standard library only; the map picture (graph.py) needs Pillow. Pass --game NAME when games/ holds more than one game.
"""

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parent
GAMES = ROOT / "games"

DEFAULT_RULES = {
    "first_turn_phantoms": 2,     # turn 1 has nothing written to cite, so it seeds the phantoms
    "written_min": 1,             # from turn 2: at least this many entries written in earlier turns
    "new_phantoms_min": 1,        # from turn 2: at least this many phantoms nobody cited before
    "cite_same_turn": False,      # may an entry cite one written in the same turn?
    "ignore_leading": ["the", "a", "an"],   # "The Ash Tithe" files under A
}
LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
LINK = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]")


# --- entries -------------------------------------------------------------------------------------

@dataclass
class Entry:
    title: str
    author: str
    turn: int
    body: str
    path: pathlib.Path
    cites: list[str] = field(default_factory=list)   # titles as written, in order, no repeats

    @property
    def key(self) -> str:
        return key(self.title)


def key(title: str) -> str:
    """One spelling per title: case, punctuation and spacing do not make a second entry."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def letter_of(title: str, ignore: list[str]) -> str:
    words = title.split()
    while len(words) > 1 and words[0].lower() in ignore:
        words = words[1:]
    for ch in " ".join(words):
        if ch.isalnum():
            return ch.upper()
    return ""


def parse_entry(path: pathlib.Path) -> Entry:
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---\n"):
        head, sep, rest = text[4:].partition("\n---\n")
        if not sep:
            raise ValueError(f"{path.name}: front matter is not closed with ---")
        body = rest
        for line in head.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    for need in ("title", "author", "turn"):
        if not meta.get(need):
            raise ValueError(f"{path.name}: front matter has no {need}")
    try:
        turn = int(meta["turn"])
    except ValueError:
        raise ValueError(f"{path.name}: turn must be a number, not {meta['turn']!r}") from None
    cites, seen = [], set()
    for m in LINK.finditer(body):
        t = m.group(1).strip()
        if key(t) not in seen:
            seen.add(key(t))
            cites.append(t)
    return Entry(meta["title"], meta["author"], turn, body, path, cites)


def load_entries(game_dir: pathlib.Path) -> tuple[list[Entry], list[str]]:
    entries, problems = [], []
    for path in sorted((game_dir / "articles").glob("*.md")):
        try:
            entries.append(parse_entry(path))
        except ValueError as exc:
            problems.append(str(exc))
    return entries, problems


# --- the game file ---------------------------------------------------------------------------------

def load_game(game_dir: pathlib.Path) -> dict:
    game = json.loads((game_dir / "game.json").read_text(encoding="utf-8"))
    game["rules"] = {**DEFAULT_RULES, **game.get("rules", {})}
    game.setdefault("letters", LETTERS)
    game.setdefault("turn", 1)
    game.setdefault("history", [])
    return game


def save_game(game_dir: pathlib.Path, game: dict) -> None:
    (game_dir / "game.json").write_text(json.dumps(game, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def players(game: dict) -> list[str]:
    return [p["player"] for p in game["players"]]


def muted(game: dict) -> set:
    """Players who asked not to be tagged. They keep every right to write; only the @ goes away.

    Mentioning is the default and opting out is a reply, the way the town's other desks do it: the roster
    is for the book, not for permission to address someone (2026-11-07).
    """
    return {str(h).lower() for h in (game.get("muted") or [])}


def turn_letters(game: dict, turn: int) -> str:
    """The letter(s) a turn takes. An entry like "XYZ" lets a short game fold the tail together."""
    return game["letters"][turn - 1] if 1 <= turn <= len(game["letters"]) else ""


def turn_for_letter(game: dict, letter: str) -> int:
    for i, spec in enumerate(game["letters"], start=1):
        if letter in spec:
            return i
    return 0


# --- the rules -----------------------------------------------------------------------------------

def check(game: dict, entries: list[Entry]) -> tuple[list[str], list[str]]:
    """Every rule over every entry. Returns (problems, notes); problems fail a pull request."""
    rules, problems, notes = game["rules"], [], []
    ignore = [w.lower() for w in rules["ignore_leading"]]
    last = len(game["letters"])
    written = {}
    for e in entries:
        if e.key in written:
            problems.append(f"{e.path.name}: '{e.title}' is already written in {written[e.key].path.name}")
        else:
            written[e.key] = e

    by_turn_author = {}
    for e in entries:
        where = f"{e.path.name} ({e.author}, turn {e.turn})"
        if e.author not in players(game):
            problems.append(f"{where}: {e.author} is not a player in game.json")
        if not 1 <= e.turn <= last:
            problems.append(f"{where}: there is no turn {e.turn}")
            continue
        if e.turn > game["turn"]:
            problems.append(f"{where}: turn {e.turn} is not open yet (the table is on turn {game['turn']})")
        # "letters_in_play": false is the one-sitting variant (played once in town on 2026-10-07): no letters,
        # no turn rotation, everybody writes in the same sitting and may write more than one entry. The
        # citation rules still apply, because they are what makes a lexicon a lexicon.
        letters = rules.get("letters_in_play", True)
        if letters:
            spec = turn_letters(game, e.turn)
            if letter_of(e.title, ignore) not in spec:
                problems.append(f"{where}: '{e.title}' does not start with {'/'.join(spec)}")
            if (e.turn, e.author) in by_turn_author:
                problems.append(f"{where}: {e.author} already wrote "
                                f"{by_turn_author[(e.turn, e.author)].path.name} this turn")
            by_turn_author.setdefault((e.turn, e.author), e)

        n_written, n_phantom, n_new = 0, 0, 0
        for title in e.cites:
            k = key(title)
            if k == e.key:
                problems.append(f"{where}: cites itself")
                continue
            target = written.get(k)
            if target is not None and target.author == e.author:
                if target.turn > e.turn:
                    problems.append(f"{target.path.name}: {e.author} cited '{target.title}' as a phantom in "
                                    f"{e.path.name}, so someone else has to write it")
                else:
                    problems.append(f"{where}: cites '{target.title}', which {e.author} wrote")
                continue
            if target is not None and target.turn < e.turn:
                n_written += 1
                continue
            if target is not None and target.turn == e.turn:
                if rules["cite_same_turn"]:
                    n_written += 1
                else:
                    problems.append(f"{where}: cites '{target.title}', written the same turn")
                continue
            # A phantom when this entry was written (still unwritten, or written in a later turn).
            n_phantom += 1
            t = turn_for_letter(game, letter_of(title, ignore)) if letters else None
            if t and t <= e.turn:
                problems.append(f"{where}: phantom '{title}' files under a letter whose turn has passed, so "
                                "nobody could ever write it")
            earlier = any(o.turn < e.turn and k in {key(c) for c in o.cites} for o in entries if o is not e)
            if not earlier:
                n_new += 1

        if e.turn == 1:
            if n_phantom < rules["first_turn_phantoms"]:
                problems.append(f"{where}: turn 1 needs {rules['first_turn_phantoms']} phantom citations, "
                                f"has {n_phantom}")
        else:
            if n_written < rules["written_min"]:
                problems.append(f"{where}: needs {rules['written_min']} citation(s) of entries from earlier "
                                f"turns, has {n_written}")
            if e.turn < last and n_new < rules["new_phantoms_min"]:
                problems.append(f"{where}: needs {rules['new_phantoms_min']} new phantom(s), has {n_new}")

    for title, citers in phantoms(game, entries).items():
        t = turn_for_letter(game, letter_of(title, ignore))
        if t and t < game["turn"]:
            notes.append(f"phantom '{title}' (cited by {', '.join(citers)}) was never written; its turn has passed")
    return problems, notes


def phantoms(game: dict, entries: list[Entry]) -> dict[str, list[str]]:
    """Unwritten titles, each with who cited it."""
    written = {e.key for e in entries}
    out: dict[str, list[str]] = {}
    seen: dict[str, str] = {}
    for e in sorted(entries, key=lambda e: (e.turn, e.path.name)):
        for title in e.cites:
            k = key(title)
            if k in written:
                continue
            name = seen.setdefault(k, title)
            if e.author not in out.setdefault(name, []):
                out[name].append(e.author)
    return {t: sorted(c) for t, c in out.items()}


# --- the turn --------------------------------------------------------------------------------------

def status(game: dict, entries: list[Entry]) -> dict:
    turn = game["turn"]
    ignore = [w.lower() for w in game["rules"]["ignore_leading"]]
    spec = turn_letters(game, turn)
    this = [e for e in entries if e.turn == turn]
    done = {e.author for e in this}
    open_here = {t: c for t, c in phantoms(game, entries).items() if letter_of(t, ignore) in spec}
    return {
        "turn": turn,
        "letters": spec,
        "over": turn > len(game["letters"]),
        "written": sorted(done),
        "owing": [p for p in players(game) if p not in done],   # bookkeeping; muting is a mention rule
        "claimable": open_here,      # phantom -> who cited it (they may not write it)
    }


def opener(game: dict, entries: list[Entry], repo_url: str = "") -> str:
    s = status(game, entries)
    if s["over"]:
        return "#lexicon The lexicon is closed: every letter has had its turn."
    handles = {p["player"]: p.get("handle") for p in game["players"]}
    letters = "/".join(s["letters"])
    off = muted(game)
    owe = " ".join(f"@{handles[p]}" if handles.get(p) else p
                   for p in s["owing"] if (handles.get(p) or p).lower() not in off)
    rules = game["rules"]
    lines = [f"#lexicon Turn {s['turn']}, the letter {letters}. Everyone writes one entry under {letters}.", ""]
    later = letters.replace("/", ", ")
    if s["turn"] == 1:
        lines.append(f"Cite {rules['first_turn_phantoms']} entries nobody has written yet. They become the "
                     f"phantoms later turns fill in. Each must file under a letter still to come — "
                     f"later than {letters} — or its turn never arrives and the promise cannot be kept.")
    else:
        lines.append(f"Cite at least {rules['written_min']} entry already written and add at least "
                     f"{rules['new_phantoms_min']} new phantom. Never cite your own. A new phantom must "
                     f"file under a letter still to come — later than {later} — not under one that has "
                     "already had its turn.")
    if s["claimable"]:
        lines += ["", f"Unwritten entries under {letters}, waiting to be claimed:"]
        for t, citers in s["claimable"].items():
            lines.append(f"• {t} (not by {', '.join(citers)})")
    if owe:
        lines += ["", "Everyone in the book gets tagged; reply `off` if you would rather not be."]
    lines += ["", f"Still to write: {owe or 'nobody'}"]
    if repo_url:
        lines.append(f"The lexicon so far: {repo_url}")
    return "\n".join(lines)


def scaffold(game_dir: pathlib.Path, game: dict, author: str, title: str) -> pathlib.Path:
    ignore = [w.lower() for w in game["rules"]["ignore_leading"]]
    turn = game["turn"]
    spec = turn_letters(game, turn)
    if author not in players(game):
        raise ValueError(f"{author} is not a player in game.json")
    if letter_of(title, ignore) not in spec:
        raise ValueError(f"turn {turn} is {'/'.join(spec)}; '{title}' files under {letter_of(title, ignore)}")
    path = game_dir / "articles" / f"{key(title)}.md"
    if path.exists():
        raise ValueError(f"{path.name} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ntitle: {title}\nauthor: {author}\nturn: {turn}\n---\n\n"
                    f"Write the entry here. Cite others as [[Their Title]].\n\n*— {author}*\n", encoding="utf-8")
    return path


def fold(game: dict, entries: list[Entry]) -> tuple[dict, str]:
    """Close the current turn. Refuses if any rule fails. Returns the new game and a summary line."""
    problems, _ = check(game, entries)
    if problems:
        raise ValueError("the turn does not check:\n  " + "\n  ".join(problems))
    s = status(game, entries)
    if s["over"]:
        raise ValueError("the lexicon is already closed")
    record = {"turn": s["turn"], "letters": s["letters"], "written": s["written"], "missed": s["owing"]}
    new = {**game, "turn": game["turn"] + 1, "history": [*game["history"], record]}
    missed = f"; missed: {', '.join(s['owing'])}" if s["owing"] else ""
    return new, f"turn {s['turn']} ({s['letters']}) folded: {len(s['written'])} entries{missed}"


def index_md(game: dict, entries: list[Entry]) -> str:
    ignore = [w.lower() for w in game["rules"]["ignore_leading"]]
    by_letter: dict[str, list[str]] = {}
    for e in entries:
        by_letter.setdefault(letter_of(e.title, ignore), []).append(
            f"- [{e.title}](articles/{e.path.name}) — {e.author}, turn {e.turn}")
    for t, citers in phantoms(game, entries).items():
        by_letter.setdefault(letter_of(t, ignore), []).append(f"- *{t}* — unwritten, cited by {', '.join(citers)}")
    lines = [f"# {game.get('title', game.get('name', 'Lexicon'))}", "",
             f"Turn {game['turn']} of {len(game['letters'])}. {len(entries)} entries written, "
             f"{len(phantoms(game, entries))} unwritten.", ""]
    for letter in sorted(by_letter):
        lines += [f"## {letter}", "", *sorted(by_letter[letter], key=str.lower), ""]
    return "\n".join(lines)


def graph_md(game: dict, entries: list[Entry], has_image: bool = True) -> str:
    """GRAPH.md: the picture (graph.png, drawn by graph.py) and the same map as plain text.

    The text is there for anyone reading without images, and so the map still exists where Pillow is
    not installed. Plain markdown only: no diagram syntax, so it reads the same on Tangled and GitHub.
    """
    name = game.get("title", game.get("name", "Lexicon"))
    unwritten = phantoms(game, entries)
    lines = [f"# {name}: who cites whom", "",
             f"Turn {game['turn']} of {len(game['letters'])}: {len(entries)} written, {len(unwritten)} unwritten.", ""]
    if has_image:
        lines += ["![The citation map: entries by turn, arrows from each entry to what it cites](graph.png)", "",
                  "Columns are turns. Boxes are coloured by author; dashed grey ones are cited but not yet written.", ""]
    lines += ["## As text", ""]
    written = {e.key for e in entries}
    for e in sorted(entries, key=lambda e: (e.turn, e.title.lower())):
        cites = ", ".join(t if key(t) in written else f"*{t}*" for t in e.cites) or "nothing"
        lines.append(f"- **{e.title}** ({e.author}, turn {e.turn}) cites {cites}")
    if unwritten:
        lines += ["", "*Italic* titles are unwritten."]
    return "\n".join(lines) + "\n"


def write_pages(game_dir: pathlib.Path, game: dict, entries: list[Entry]) -> str:
    """Rewrite INDEX.md, GRAPH.md and, when Pillow is installed, graph.png. Returns a note if the image was skipped."""
    (game_dir / "INDEX.md").write_text(index_md(game, entries), encoding="utf-8")
    try:
        import graph
    except ImportError:
        (game_dir / "GRAPH.md").write_text(graph_md(game, entries, has_image=(game_dir / "graph.png").exists()),
                                           encoding="utf-8")
        return "graph.png not redrawn: Pillow is not installed (pip install pillow)"
    graph.render(game, entries, game_dir / "graph.png")
    (game_dir / "GRAPH.md").write_text(graph_md(game, entries), encoding="utf-8")
    return ""


# --- command line ------------------------------------------------------------------------------------

def pick_game(name: str | None) -> pathlib.Path:
    if name:
        d = GAMES / name
        if not (d / "game.json").exists():
            sys.exit(f"no game at {d}")
        return d
    found = sorted(p.parent for p in GAMES.glob("*/game.json"))
    if len(found) != 1:
        sys.exit(f"pass --game: games/ holds {', '.join(p.name for p in found) or 'nothing'}")
    return found[0]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--game")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    o = sub.add_parser("open")
    o.add_argument("--repo-url", default="")
    n = sub.add_parser("new")
    n.add_argument("--author", required=True)
    n.add_argument("--title", required=True)
    c = sub.add_parser("check")
    c.add_argument("--all", action="store_true", help="every game under games/")
    sub.add_parser("fold")
    sub.add_parser("index", help="rewrite INDEX.md and GRAPH.md")
    sub.add_parser("graph", help="the same as index: rewrite INDEX.md and GRAPH.md")
    g = sub.add_parser("new-game")
    g.add_argument("name")
    g.add_argument("--players", required=True, help="player:handle,player:handle,…")
    g.add_argument("--title", default="")
    g.add_argument("--letters", default="", help='comma-separated turns, e.g. "A,B,…,W,XYZ" (default A–Z)')
    args = ap.parse_args(argv)

    if args.cmd == "new-game":
        d = GAMES / args.name
        if (d / "game.json").exists():
            sys.exit(f"{d} already exists")
        roster = []
        for item in args.players.split(","):
            p, _, h = item.strip().partition(":")
            roster.append({"player": p, **({"handle": h} if h else {})})
        game = {"name": args.name, "title": args.title or args.name, "players": roster,
                "letters": [s.strip().upper() for s in args.letters.split(",")] if args.letters else LETTERS,
                "rules": DEFAULT_RULES, "turn": 1, "history": []}
        (d / "articles").mkdir(parents=True)
        save_game(d, game)
        write_pages(d, game, [])
        print(f"created {d}")
        return 0

    dirs = sorted(p.parent for p in GAMES.glob("*/game.json")) if getattr(args, "all", False) else [pick_game(args.game)]
    failed = False
    for game_dir in dirs:
        game = load_game(game_dir)
        entries, parse_problems = load_entries(game_dir)

        if args.cmd == "status":
            s = status(game, entries)
            if s["over"]:
                print("The lexicon is closed.")
                continue
            print(f"Turn {s['turn']}, letter {'/'.join(s['letters'])}")
            print(f"Written: {', '.join(s['written']) or 'nobody yet'}")
            print(f"Owing:   {', '.join(s['owing']) or 'nobody'}")
            for t, citers in s["claimable"].items():
                print(f"Open phantom: {t} (cited by {', '.join(citers)}, who may not write it)")
        elif args.cmd == "open":
            print(opener(game, entries, args.repo_url))
        elif args.cmd == "new":
            try:
                print(f"wrote {scaffold(game_dir, game, args.author, args.title).relative_to(ROOT)}")
            except ValueError as exc:
                print(f"refused: {exc}")
                return 1
        elif args.cmd == "check":
            problems, notes = check(game, entries)
            problems = parse_problems + problems
            label = f"{game_dir.name}: " if len(dirs) > 1 else ""
            for n_ in notes:
                print(f"{label}note: {n_}")
            for p in problems:
                print(f"{label}FAIL: {p}")
            if not problems:
                print(f"{label}ok — {len(entries)} entries, {len(phantoms(game, entries))} phantoms, turn {game['turn']}")
            failed |= bool(problems)
        elif args.cmd == "fold":
            if parse_problems:
                print("refused:\n  " + "\n  ".join(parse_problems))
                return 1
            try:
                game, summary = fold(game, entries)
            except ValueError as exc:
                print(f"refused: {exc}")
                return 1
            save_game(game_dir, game)
            note = write_pages(game_dir, game, entries)
            print(summary)
            if note:
                print(f"note: {note}")
            print(f"next: python3 lexicon.py open" + (f" --game {game_dir.name}" if args.game else ""))
        elif args.cmd in ("index", "graph"):
            note = write_pages(game_dir, game, entries)
            print(f"wrote {(game_dir / 'INDEX.md').relative_to(ROOT)}, GRAPH.md" + ("" if note else " and graph.png"))
            if note:
                print(f"note: {note}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
