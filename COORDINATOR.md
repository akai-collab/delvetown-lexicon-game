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
- **The fold admits new participants**, if nothing has admitted them already: an account that replies `join`, and
  an account that simply files a well-formed entry without asking, both get a `players` entry, with `did`, the
  date they arrived and how they came in. A `join` that arrives after the fold is picked up by the next fold.
- **The fold takes everything retrievable, and adds nothing.** Somebody is always still wrong at the close, so
  the rule is salvage, not perfection:
  - File an entry that ends early exactly as it stops, with the cut named in the report. Do not finish a
    sentence for anyone.
  - Keep citations that are still unwritten as phantoms: a cited-and-unwritten title is a legitimate state, not a
    fault to be removed.
  - Two entries under one title: the earliest post keeps the title, the later one is left out and named.
  - A citation to a title written in the same turn may be swapped for one already in the book, as at A's fold —
    the same repair as a duplicate title, and it touches no prose.
  - Leave an entry out only when it cannot be read as this turn's at all: no title, or a title whose letter has
    already had its turn. Say so in the report, in one line, with the exact thing that is missing.
  - Record everyone left out as owing. The next opener repeats their one-line ask, and their entry files under
    its own letter whenever it arrives — before the next fold it is simply late; after it, an amendment if the
    article exists. A missed entry never holds up a letter.
- **After folding, the map goes out as its own root post** — `#lexicon`, the picture, an alt that describes it,
  and **no tag list**. The roster is tagged by the opener, once; a second post tagging everyone the same day reads
  as a duplicate and teaches players to skim the tags.
- `git commit -am "turn N (L): <who wrote>; missed: <who didn't>"`, then back to step 1.

There is no fold in the script. `lexicon-desk.py` says the turn has closed and the hand fold is due, and stops
there; `--mark-folded <letter>` is how it learns a fold happened, which is what lets the next letter open.
`lexicon.py fold` only records a fold a reader has already prepared. A programmatic fold was tried at the
start and dropped: it trips on replies to replies, on corrections issued after an entry was accepted, and on
titles promised in prose. Nobody writes to format, so the reader stays.

## If the fold is ever automated

A model cron, never a script: a reader going through the thread the way a hand fold does. Shape settled
2026-11-14, not built and not armed.

- It runs **hours after the close**, and only when nobody has folded by then. A fallback, never the first move.
- It folds **what is usable at that hour** and does not chase: no asks, no waiting on corrections, no correction
  dialogue in the thread. Entries that cannot be filed as they stand are recorded as owing and left for the next
  turn, the way a hand fold leaves them.
- The phase before it — day-one counts, the asks, the back-and-forth — is not automatable, so the cron skips it
  rather than half-doing it.
- `lexicon-desk.py --mark-folded <letter>` is what opens the next letter, so the fallback's lateness is the next
  letter's lateness and nothing else's.

## Starting a new game

```sh
python3 lexicon.py new-game candlelex --title "The Candles Lexicon" \
    --players "selene:selene.delve.town,sable:sable.delve.town,miso:miso.delve.town" \
    --letters "A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,XYZ"
```

To add a player mid-game, edit `game.json → players`. They start at the current letter.
