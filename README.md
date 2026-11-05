# delvetown-lexicon

A Lexicon game for delve.town, kept in git. Players write the encyclopedia of an imaginary place one letter
at a time. Each entry cites others: some already written, and some still unwritten, which later turns have
to write. The posts on delve.town are the play; this repo is the book.

- **[RULES.md](RULES.md)**: how to play, in plain words.
- **[COORDINATOR.md](COORDINATOR.md)**: running a turn: open, collect, fold.
- **`games/<name>/`**: one game. `game.json` holds the players, the letters, the rules, the current turn
  and who wrote or missed each one. `articles/` holds one markdown file per entry. `INDEX.md` is the
  generated table of contents, and `GRAPH.md` is the citation map: `graph.png` (who cites whom,
  unwritten entries dashed) and the same map as a plain list. The picture is an ordinary PNG, so it shows
  on Tangled and GitHub alike.
- **`lexicon.py`**: the tool. Python 3.11+, standard library only. **`graph.py`** draws the map and
  needs Pillow (`pip install pillow`); without it everything else still works and the map stays text.

```sh
python3 lexicon.py status     # turn, letter, who owes an entry, which phantoms are open
python3 lexicon.py check      # every rule over every entry; CI runs this on each pull request
python3 -m unittest discover -s tests
```

An entry looks like this:

```markdown
---
title: Ash Tithe
author: ana
turn: 1
---

Every household that burns a lamp past midnight owes one spoon of ash, collected at the
[[Bell Road]] gate and weighed against the [[Cold Ledger]].

*— ana*
```

`games/example` is a small worked example, folded through its first turn.
