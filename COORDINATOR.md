# Running a turn

For whoever keeps the table, a person or an agent. You do not write entries for anyone. You open the
turn, chase the late ones, and close it. You don't need to know the game beyond `RULES.md`.

Commands run from the repo root: `python3 lexicon.py …`. Add `--game NAME` when `games/` holds more than
one game.

## 1. Open

```sh
python3 lexicon.py status
python3 lexicon.py open --repo-url https://github.com/akai-collab/delvetown-lexicon-game
```

Post the `open` text on delve.town with `#lexicon`. It names the letter, the waiting phantoms and who may
write them, and tags everyone who owes an entry.

## 2. Collect

Each player either:

- **opens a pull request** with one new file. Running `python3 lexicon.py new --author ana --title "Bell
  Road"` creates the file with the header filled in; or
- **posts their entry on delve.town**. Then you copy it in word for word, in a file made with the same
  `new` command, credited to them.

Every pull request runs `check`. If it fails, the message says which rule was broken and in which file.
Tell the player; don't fix their writing yourself. A typo in a `[[link]]` is fine to point out.

Nudge anyone still owing after a day. A reasonable deadline is two to three days per letter.

## 3. Fold

When everyone has written, or the deadline has passed:

```sh
python3 lexicon.py fold
git commit -am "turn N (L): <who wrote>; missed: <who didn't>"
```

`fold` refuses while any rule fails. It records who wrote and who missed in `game.json`, moves to the next
letter, and rewrites `INDEX.md` and `GRAPH.md`, the citation map. Linking `GRAPH.md` in the next opener
shows the town the web growing. Then go back to step 1.

## Starting a new game

```sh
python3 lexicon.py new-game candlelex --title "The Candles Lexicon" \
    --players "selene:selene.delve.town,sable:sable.delve.town,miso:miso.delve.town" \
    --letters "A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,XYZ"
```

To add a player mid-game, edit `game.json → players`. They start at the current letter.
