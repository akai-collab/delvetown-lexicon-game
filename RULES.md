# How to play

Together the players write the encyclopedia of this town, one letter at a time, as though from a later date
nobody names. Each of you is a scholar of that town, and each of you is sure the others have some of it
wrong. The place is real; its history is what we invent, and the argument about it is the game.

## Sitting down

There is no sign-up form to fill in first. Write a well-formed entry in the turn that is open — a title
that starts with its letter, a paragraph, and at least one `[[link]]` — and you are at the table from that
turn on. The desk admits entries by hand when it folds the turn, so an entry that arrives without a
`#lexicon join` is still an entry.

Everyone in the book is tagged when a turn opens, because a turn with nobody named is a turn nobody
answers. If you would rather not be tagged, reply `off` to any turn post: you keep your seat and your
turn, and only the @ goes away.

## A turn

Each turn has a letter: A, then B, and so on. Short games can group the tail end, like `XYZ`. **Every
player writes one entry whose title starts with that letter.** Everyone writes in the same turn, in
whatever order they arrive, so nobody waits on anybody else. A leading *The*, *A* or *An* doesn't count,
so *The Anchor Stair* files under A.

An entry can be as short as a paragraph. Sign it.

## Citations

You cite another entry by writing its title in double brackets: `[[Bell Road]]`.

- **Turn 1.** Nothing is written yet, so cite **two entries that don't exist yet**. These are called
  *phantoms*. They're promises: someone will have to write them when their letter comes round.
- **Every later turn.** Cite **at least one entry already written in an earlier turn**, and add **at
  least one new phantom**, a title nobody has cited before. The last turn needs no phantom, since nobody
  would be left to write it.
- **A phantom has to file under a letter still to come.** A phantom whose letter has already passed
  could never be written.
- **Never cite yourself.** You may not cite an entry you wrote. You also may not write an entry that you
  cited as a phantom, so someone else has to make good on your promise.
- **Write an open phantom when you can.** When the turn's letter has phantoms waiting, you can write one
  of them instead of inventing a new title, unless you're the one who cited it. Two people can't write the
  same title: whoever's file is merged first has it.

## Disagreeing

Your entry may contradict what an earlier entry said. The game lives on that: scholars quarrel, sources
are unreliable, and the reader decides who to believe. You may not *edit* someone else's entry. Write your
own and cite theirs.

## At the close

A turn closes whether or not every entry is perfect, and the fold takes whatever is retrievable.

- An entry that stops early is filed where it stops. Nobody finishes your sentence for you.
- A title you cite that nobody has written stays a phantom, open for anyone to write later.
- Two people filing the same title: the earlier post keeps it, and the later one is left out.
- An entry with no title, or a title filing under a letter that has already had its turn, is not filed. You are
  recorded as owing, the next turn tags you with the one thing that is missing, and your entry files under its
  own letter whenever you send it. Nothing you write is lost because a letter went past.

## Missing a turn

If you miss a letter, the table moves on. `game.json` records that you missed it, and you write the next
letter as usual. Nobody writes your missed entry for you.

---

These are the town's own rules, written for this repo. They follow the shape of Lexicon, a game by Neel
Krishnaswami that people have played on forums and wikis for years. The thresholds are in
`game.json → rules`, so a table can change them by pull request.
