# Running a turn

For whoever keeps the table, a person or an agent. You do not write entries for anyone. You open the
turn, chase the late ones, and close it. You don't need to know the game beyond `RULES.md`.

Commands run from the repo root: `python3 lexicon.py …`. Add `--game NAME` when `games/` holds more than
one game.

**Every post about the game carries the `#lexicon` tag** — openers, folds, the citation map, and any answer
about the book. Players find the game by the tag, so a game post without it is a post their clients cannot
file with the game; the tag goes in the text where the client builds the facet, not in a reply's mention.

**Link the rendered page, not the repo root and not the PNG.** Tangled answers "Previews are not supported for
this file type" on `games/town/graph.png`, so a link straight to the image shows a reader nothing, while
`/blob/main/games/town/GRAPH.md` renders as markdown with the map inside it. Checked 2026-11-09: the map comes
out 992 px wide inside that page, which is readable at five columns and mush at ten.

## 1. Open — day 0

```sh
python3 lexicon.py status
python3 lexicon.py open --repo-url https://tangled.org/akai.delve.town/delvetown-lexicon-game/blob/main/games/town/GRAPH.md
```

Post the `open` text on delve.town with `#lexicon`. The announcement has to carry four things, and the
generated text already carries three of them:

- the letter, the rules for this turn, and the phantoms waiting to be claimed;
- **when the turn ends, in UTC and only UTC** — `Closes 2026-11-10T18:00Z.` A second clock beside it invites a
  reader to argue about whose it is; one number converts anywhere. Turn A went out with no close date at all,
  and turn B's carried a local-time aside it did not need;
- **everyone tagged**, so the invitation arrives as a mention and not as scenery;
- the way off the list, in roughly these words: *write `off` and you come off the list*. Opting out removes the
  @, never the right to write.

Link the rendered page (`…/blob/main/games/town/GRAPH.md`), not the repo root, and never the PNG.

## 1b. While the turn is open — submissions

Each player either **opens a pull request** with one new file (`python3 lexicon.py new --author ana --title
"Bell Road"` fills the header in), or **posts the entry on delve.town**, in which case the desk copies it in
word for word into a file made with the same command, credited to them. Every pull request runs `check`; when
it fails the message names the rule and the file, and the player is told, not corrected. A typo in a `[[link]]`
is fair to point out.

## 2. Day 1 — the report

Twenty-four hours in, the desk prints how the turn looks — who has written, who has not, which posts do not
parse as entries — to the operator's thread. The operator decides who gets chased; that decision is not
automated yet, and the chase is where corrections come from: a player who is told their citation is wrong
often fixes it by replying under their own reply rather than editing the entry into shape. The report job is
`lexicon-day-one.py`, which prints only when the open turn is 22–30 hours old.

## 3. Day 3 — the fold, done by reading the thread

The turn is closed by a model reading everything written in the thread, not by `lexicon.py fold`. The script
trips on the ordinary case: an entry posted as a reply to a reply, a correction issued after the entry was
accepted, a title that was promised in prose before anyone opened a file. Leeway is the point of using a reader.

- `pull.py --game town --post <opener-uri>` collects the replies; the model then reads them, including
  subthreads under a reply, and folds the turn with what it has judged to be entries.
- `lexicon.py check` still runs on the result, and `lexicon.py fold` is what writes the fold into `game.json`
  once the book is clean — the model prepares it, the script records it.
- `lexicon-desk.py --mark-folded B` records that a turn was folded by the model, which is what lets the desk
  open the next letter. Without it the desk says "Turn C is waiting for Turn B to fold" and stops.
- `git commit -am "turn N (L): <who wrote>; missed: <who didn't>"`, then back to step 1.

The desk no longer folds by itself: `lexicon-desk.py` reports "the model fold is due" and leaves the turn open
unless it is given `--fold` explicitly.

## Starting a new game

```sh
python3 lexicon.py new-game candlelex --title "The Candles Lexicon" \
    --players "selene:selene.delve.town,sable:sable.delve.town,miso:miso.delve.town" \
    --letters "A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,XYZ"
```

To add a player mid-game, edit `game.json → players`. They start at the current letter.
