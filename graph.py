"""The citation map as a PNG, drawn with Pillow, so it shows on any forge (Tangled, GitHub) as a plain image.

Columns are turns, left to right: each entry sits in the column of the turn it was written, each phantom
in the column of the turn whose letter it files under. Written entries are boxes coloured by author;
phantoms are grey and dashed. An arrow runs from an entry to each entry it cites, coloured like the
citing author's box, so a reader can follow one scholar's references across the year.

Within a column, entries are ordered to sit near what they cite (a few barycentre sweeps), which keeps
crossings down without a layout engine. The drawing is a pure function of the files, and the font is
Pillow's own, so two machines with the same Pillow make the same image.
"""

import pathlib

from PIL import Image, ImageDraw, ImageFont

import lexicon as lx

PALETTE = ["#f4d9a6", "#c9e4c5", "#c7d8f0", "#efc9d6", "#e2d4f0", "#f0e0c0", "#cfe8e8", "#e8d0c0"]
INK = ["#9a6b1f", "#3d7a37", "#36609e", "#a3486a", "#6e4f9c", "#8a6a2a", "#2f7f7f", "#8a5a3a"]
PAPER, TEXT, MUTED, PHANTOM_FILL, PHANTOM_LINE = "#fbf8f1", "#222222", "#777777", "#eeeeee", "#9a9a9a"

BOX_W, PAD, ROW_GAP, COL_GAP, MARGIN, HEADER = 190, 8, 22, 110, 30, 46
SCALE = 2   # drawn at twice the size, so text stays sharp when a forge shrinks the image


def _font(size: int):
    try:
        return ImageFont.load_default(size=size * SCALE)
    except TypeError:  # Pillow older than 10.1 has one bitmap size only
        return ImageFont.load_default()


def _wrap(draw, text: str, font, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + ([line] if line else [])


def layout(game: dict, entries: list[lx.Entry]) -> dict:
    """Where each node goes, before any pixels: {key: {col, row, ...}}, plus the edges. Pure, so it is tested."""
    ignore = [w.lower() for w in game["rules"]["ignore_leading"]]
    last = len(game["letters"])
    nodes: dict[str, dict] = {}
    for e in entries:
        nodes[e.key] = {"title": e.title, "author": e.author, "turn": e.turn, "written": True}
    for title, citers in lx.phantoms(game, entries).items():
        turn = lx.turn_for_letter(game, lx.letter_of(title, ignore)) or last + 1
        nodes[lx.key(title)] = {"title": title, "author": None, "turn": turn, "written": False, "citers": citers}
    edges = [(e.key, lx.key(t), e.author) for e in sorted(entries, key=lambda e: (e.turn, e.key))
             for t in e.cites if lx.key(t) != e.key and lx.key(t) in nodes]

    turns = sorted({n["turn"] for n in nodes.values()})
    col_of = {t: i for i, t in enumerate(turns)}

    # An arrow that crosses columns gets a waypoint in each column it passes through, with its own slot in
    # that column's order, so it travels through a gap and never behind a box it does not touch.
    paths = []
    for i, (a, b, author) in enumerate(edges):
        ca, cb = col_of[nodes[a]["turn"]], col_of[nodes[b]["turn"]]
        step = 1 if cb > ca else -1
        chain = [a]
        for c in range(ca + step, cb, step):
            w = f"~{i}~{c}"
            nodes[w] = {"title": "", "author": author, "turn": turns[c], "written": False, "waypoint": True}
            chain.append(w)
        paths.append((chain + [b], author))

    columns = {t: sorted((k for k, n in nodes.items() if n["turn"] == t), key=lambda k: nodes[k]["title"].lower())
               for t in turns}
    near: dict[str, list[str]] = {k: [] for k in nodes}
    for chain, _ in paths:
        for a, b in zip(chain, chain[1:]):
            near[a].append(b)
            near[b].append(a)
    for _ in range(4):  # pull each node towards the average row of what it touches
        row = {k: i for t in turns for i, k in enumerate(columns[t])}
        for t in turns:
            def centre(k):
                ns = [row[n] for n in near[k]]
                return (sum(ns) / len(ns) if ns else row[k], nodes[k]["title"].lower())
            columns[t] = sorted(columns[t], key=centre)
    for ci, t in enumerate(turns):
        for ri, k in enumerate(columns[t]):
            nodes[k]["col"], nodes[k]["row"] = ci, ri
    return {"nodes": nodes, "edges": edges, "paths": paths, "columns": [columns[t] for t in turns], "turns": turns}


def _dashed_rect(draw, box, colour, width, dash=7 * SCALE, gap=5 * SCALE):
    x0, y0, x1, y1 = box
    for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        length = max(abs(bx - ax), abs(by - ay))
        pos = 0
        while pos < length:
            end = min(pos + dash, length)
            f0, f1 = pos / length, end / length
            draw.line((ax + (bx - ax) * f0, ay + (by - ay) * f0, ax + (bx - ax) * f1, ay + (by - ay) * f1),
                      fill=colour, width=width)
            pos += dash + gap


def _curve(draw, p0, p3, colour, width, arrow=True):
    """A horizontal S-curve from p0 to p3, ending in an arrowhead."""
    (x0, y0), (x3, y3) = p0, p3
    bend = max(abs(x3 - x0) * 0.45, 30 * SCALE)
    sign = 1 if x3 >= x0 else -1
    p1, p2 = (x0 + sign * bend, y0), (x3 - sign * bend, y3)
    pts = []
    for i in range(41):
        t = i / 40
        u = 1 - t
        pts.append((u ** 3 * x0 + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * x3,
                    u ** 3 * y0 + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * y3))
    draw.line(pts, fill=colour, width=width, joint="curve")
    if not arrow:
        return
    head = 9 * SCALE
    draw.polygon([(x3, y3), (x3 - sign * head, y3 - head * 0.55), (x3 - sign * head, y3 + head * 0.55)], fill=colour)


def render(game: dict, entries: list[lx.Entry], path: pathlib.Path) -> pathlib.Path:
    plan = layout(game, entries)
    nodes, authors = plan["nodes"], lx.players(game)
    title_font, small_font, head_font = _font(14), _font(11), _font(18)
    scratch = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    s = SCALE

    # Box sizes from the wrapped text.
    for n in nodes.values():
        if n.get("waypoint"):
            n["h"] = 4 * s
            continue
        n["lines"] = _wrap(scratch, n["title"], title_font, (BOX_W - 2 * PAD) * s)
        n["sub"] = f"{n['author']}, turn {n['turn']}" if n["written"] else "unwritten"
        n["h"] = (2 * PAD + 18 * len(n["lines"]) + 15) * s

    col_heights = [sum(nodes[k]["h"] for k in col) + ROW_GAP * s * max(len(col) - 1, 0) for col in plan["columns"]]
    tallest = max(col_heights, default=0)
    width = (2 * MARGIN + len(plan["columns"]) * BOX_W + max(len(plan["columns"]) - 1, 0) * COL_GAP) * s
    legend_h = 40 * s
    height = max((2 * MARGIN + HEADER) * s + tallest + legend_h, 200 * s)

    for ci, col in enumerate(plan["columns"]):
        x = (MARGIN + ci * (BOX_W + COL_GAP)) * s
        y = (MARGIN + HEADER) * s + (tallest - col_heights[ci]) / 2
        for k in col:
            n = nodes[k]
            n["box"] = (x, y, x + BOX_W * s, y + n["h"])
            y += n["h"] + ROW_GAP * s

    img = Image.new("RGB", (int(width), int(height)), PAPER)
    draw = ImageDraw.Draw(img)

    # Column headers: the turn's letters.
    for ci, t in enumerate(plan["turns"]):
        spec = lx.turn_letters(game, t) or "after the last letter"
        label = "/".join(spec) if len(spec) <= 3 else spec
        cx = (MARGIN + ci * (BOX_W + COL_GAP) + BOX_W / 2) * s
        draw.text((cx, MARGIN * s), label, font=head_font, fill=MUTED, anchor="mt")

    # Arrows first, so boxes sit on top of them. Each follows its chain of waypoints: a curve between
    # columns, a straight run across each column it passes through.
    for chain, author in plan["paths"]:
        ink = INK[authors.index(author) % len(INK)] if author in authors else MUTED
        first, last_ = nodes[chain[0]]["box"], nodes[chain[-1]]["box"]
        forward = last_[0] > first[2]
        if not forward and not last_[2] < first[0]:   # same column (cite_same_turn): loop out to the right
            _curve(draw, (first[2], (first[1] + first[3]) / 2), (last_[2] + 2 * s, (last_[1] + last_[3]) / 2),
                   ink, 2 * s)
            continue
        def mid(box):
            return (box[1] + box[3]) / 2
        out_x = first[2] if forward else first[0]
        point = (out_x, mid(first))
        for w in chain[1:-1]:
            box = nodes[w]["box"]
            enter, leave = (box[0], box[2]) if forward else (box[2], box[0])
            _curve(draw, point, (enter, mid(box)), ink, 2 * s, arrow=False)
            draw.line((enter, mid(box), leave, mid(box)), fill=ink, width=2 * s)
            point = (leave, mid(box))
        end_x = last_[0] - 2 * s if forward else last_[2] + 2 * s
        _curve(draw, point, (end_x, mid(last_)), ink, 2 * s)

    for n in nodes.values():
        if n.get("waypoint"):
            continue
        x0, y0, x1, y1 = n["box"]
        if n["written"]:
            i = authors.index(n["author"]) if n["author"] in authors else 0
            draw.rounded_rectangle(n["box"], radius=4 * s, fill=PALETTE[i % len(PALETTE)], outline="#555555",
                                   width=s)
            colour = TEXT
        else:
            draw.rounded_rectangle(n["box"], radius=14 * s, fill=PHANTOM_FILL)
            _dashed_rect(draw, (x0 + 3 * s, y0, x1 - 3 * s, y1), PHANTOM_LINE, 2 * s)
            colour = MUTED
        ty = y0 + PAD * s
        for line in n["lines"]:
            draw.text(((x0 + x1) / 2, ty), line, font=title_font, fill=colour, anchor="mt")
            ty += 18 * s
        draw.text(((x0 + x1) / 2, ty + 1 * s), n["sub"], font=small_font, fill=MUTED, anchor="mt")

    # Legend along the bottom: who is which colour.
    lx_, ly = MARGIN * s, height - (MARGIN + 18) * s
    for i, a in enumerate(authors):
        if not any(e.author == a for e in entries):
            continue
        draw.rounded_rectangle((lx_, ly, lx_ + 16 * s, ly + 16 * s), radius=3 * s, fill=PALETTE[i % len(PALETTE)],
                               outline="#555555", width=s)
        draw.text((lx_ + 22 * s, ly + 8 * s), a, font=small_font, fill=TEXT, anchor="lm")
        lx_ += 22 * s + draw.textlength(a, font=small_font) + 18 * s
    if lx.phantoms(game, entries):
        _dashed_rect(draw, (lx_, ly, lx_ + 16 * s, ly + 16 * s), PHANTOM_LINE, s, dash=4 * s, gap=3 * s)
        draw.text((lx_ + 22 * s, ly + 8 * s), "unwritten", font=small_font, fill=MUTED, anchor="lm")

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)
    return path
