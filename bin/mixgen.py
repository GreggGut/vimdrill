"""Randomized practice rounds for `vimdrill --mix`.

Each generator builds one small edit drill for its lesson from random content. The reference
solution comes from Ed, a tiny model of the editor that emits keys and applies the same edit,
so the target is whatever that solution produces. `tools/verify_drills.py --mix N` replays
generated rounds in real nvim to keep the model honest.

A generator returns a drill spec like the ones in src/*.drills.json:
  {"instructions", "solution", "start": {"main.txt": ...}, "target": {"main.txt": ...}}
Lessons without a generator fall back to their fixed drill in drills/<id>.
"""
import heapq
import random
import re
from collections import deque

INF = 10 ** 9

NOUNS = ["fox", "dog", "river", "garden", "window", "rocket", "kettle", "planet", "bridge", "lantern",
         "forest", "engine", "pocket", "letter", "harbor", "pencil", "castle", "meadow", "button", "ladder",
         "basket", "candle", "mirror", "tunnel", "violin", "wagon", "island", "turtle", "jacket", "silver"]
VERBS = ["jumps", "waits", "glows", "drifts", "sings", "turns", "falls", "rests", "grows", "spins",
         "hides", "rolls", "shines", "climbs", "listens", "wanders", "sleeps", "breaks", "opens", "travels"]
ADJS = ["quick", "lazy", "quiet", "bright", "heavy", "gentle", "rusty", "golden", "narrow", "sleepy",
        "brave", "silent", "frozen", "hollow", "tiny", "ancient", "clever", "dusty", "wild", "calm"]
SMALL = ["the", "a", "over", "under", "near", "with", "and", "into", "past", "by"]
IDENTS = ["count", "total", "index", "limit", "offset", "width", "height", "speed", "score", "level",
          "retries", "timeout", "buffer", "result", "cursor", "status", "config", "parser", "loader", "cache"]
FUNCS = ["add", "scale", "merge", "clamp", "lerp", "pick", "blend", "apply", "shift", "split"]
OPS = ["+", "-", "*", "/"]


def lit(text):
    """Text typed in insert mode, in <>-notation."""
    return text.replace("<", "<lt>")


# ---------- the editor model ----------

def word_cls(ch):
    return 0 if ch in " \t" else 2 if (ch.isalnum() or ch == "_") else 1


def big_cls(ch):
    return 0 if ch in " \t" else 1


def _w(s, col, cls):
    n, i, c = len(s), col, cls(s[col])
    if c:
        while i < n and cls(s[i]) == c:
            i += 1
    while i < n and cls(s[i]) == 0:
        i += 1
    return i if i < n else None


def _e(s, col, cls):
    n, i = len(s), col + 1
    while i < n and cls(s[i]) == 0:
        i += 1
    if i >= n:
        return None
    c = cls(s[i])
    while i + 1 < n and cls(s[i + 1]) == c:
        i += 1
    return i


def _b(s, col, cls):
    i = col - 1
    while i >= 0 and cls(s[i]) == 0:
        i -= 1
    if i < 0:
        return None
    c = cls(s[i])
    while i > 0 and cls(s[i - 1]) == c:
        i -= 1
    return i


PARTNER = {"(": ")", "[": "]", "{": "}", ")": "(", "]": "[", "}": "{"}


def _pct(s, col):
    i = col
    while i < len(s) and s[i] not in PARTNER:
        i += 1
    if i == len(s):
        return None
    ch, step = s[i], 1 if s[i] in "([{" else -1
    depth, j = 0, i
    while 0 <= j < len(s):
        if s[j] == ch:
            depth += 1
        elif s[j] == PARTNER[ch]:
            depth -= 1
            if depth == 0:
                return j
        j += step
    return None


def hmove(s, col, m):
    """Column after motion m on line s, or None if it would leave the line."""
    n = len(s)
    if n == 0:
        return None
    return {
        "l": lambda: col + 1 if col + 1 < n else None,
        "h": lambda: col - 1 if col > 0 else None,
        "0": lambda: 0,
        "^": lambda: n - len(s.lstrip(" \t")) if s.strip() else n - 1,
        "$": lambda: n - 1,
        "w": lambda: _w(s, col, word_cls),
        "W": lambda: _w(s, col, big_cls),
        "e": lambda: _e(s, col, word_cls),
        "E": lambda: _e(s, col, big_cls),
        "b": lambda: _b(s, col, word_cls),
        "B": lambda: _b(s, col, big_cls),
        "%": lambda: _pct(s, col),
    }[m]()


def hpath(s, start, target, motions):
    """Fewest keys from column start to column target, as a list of motions (BFS)."""
    if start == target:
        return []
    prev = {start: None}
    q = deque([start])
    while q:
        c = q.popleft()
        for m in motions:
            nc = hmove(s, c, m)
            if nc is None or nc in prev:
                continue
            prev[nc] = (c, m)
            if nc == target:
                path = []
                while prev[nc]:
                    nc, m = prev[nc]
                    path.append(m)
                return path[::-1]
            q.append(nc)
    raise ValueError(f"column {target} unreachable in {s!r}")


class Ed:
    """Buffer + cursor that records the keys of every motion and edit it performs."""

    def __init__(self, lines, motions="hlwbeWBE0^$%", screen=None):
        self.lines = list(lines)
        self.row = self.col = self.want = 0
        self.keys = []
        self.motions = list(motions)
        self.screen = screen  # window height: plan with H/M/L, Ctrl-d/u, zt/zz/zb (scrolloff=0)
        self.top = 0  # first visible row; None once a far jump leaves the view unknown
        self.ins = None  # (row, col) where insert mode was last left: nvim's '^ mark, used by gi
        self.practice = {}  # key -> why the round needs it; vimdrill fails a round where it goes unused

    @property
    def solution(self):
        return "".join(self.keys)

    def _col_for(self, row, want):
        n = len(self.lines[row])
        return max(0, min(want, n - 1)) if n else 0

    def _para(self, row, step):
        n, i = len(self.lines), row + step
        while self.lines[row] == "" and 0 <= i < n and self.lines[i] == "":
            i += step
        while 0 <= i < n and self.lines[i] != "":
            i += step
        return i if 0 <= i < n else None

    def _vertical(self, r):
        """Candidate ways to reach row r: (keys, want afterwards)."""
        d, cands = r - self.row, []
        if d == 0:
            return [([], self.want)]
        cands.append((["j" if d > 0 else "k"] * abs(d), self.want))
        cands.append(([f":{r + 1}<CR>"], self.want))
        if r == len(self.lines) - 1:
            cands.append((["G"], self.want))
        if r == 0:
            cands.append((["gg"], self.want))
        if self.lines[r] == "":
            step, i, keys = (1 if d > 0 else -1), self.row, []
            while i is not None and len(keys) < 8:
                i = self._para(i, step)
                keys.append("}" if step > 0 else "{")
                if i == r:
                    cands.append((keys, 0))
                    break
        return cands

    def _screen_moves(self, top, row, r):
        """One-command moves as (key, top, row), matching nvim at a fixed height with scrolloff=0.
        Moves whose scrolling is hard to predict (:N off screen) leave top as None."""
        h, n = self.screen, len(self.lines)
        half, last_top = h // 2, n - h
        on = lambda x: top is not None and top <= x < top + h
        if top is not None:
            if top + half <= last_top:
                yield "<C-d>", top + half, row + half
            if top - half >= 0:
                yield "<C-u>", top - half, row - half
            yield from (("H", top, top), ("M", top, top + (h - 1) // 2), ("L", top, top + h - 1))
            for key, t in (("zt", row), ("zz", max(0, row - (h - 1) // 2)), ("zb", max(0, row - h + 1))):
                if t <= last_top and t != top:
                    yield key, t, row
        for key, d in (("j", 1), ("k", -1)):
            if 0 <= row + d < n:
                yield key, None if top is None else min(max(top, row + d - h + 1), row + d), row + d
        yield "gg", 0, 0
        yield "G", top if on(n - 1) else last_top, n - 1
        yield f":{r + 1}<CR>", top if on(r) else None, r

    def _screen_path(self, r):
        """Fewest keys to row r through the viewport model (Dijkstra over (top, row))."""
        cost = lambda k: len(k) - 3 if k.startswith(":") else 1 if k.startswith("<") else len(k)
        start, tie = (self.top, self.row), 0
        best, heap = {start: 0}, [(0, 0, start, [])]
        while heap:
            c, _, (top, row), keys = heapq.heappop(heap)
            if row == r:
                return keys, top
            if c > best[(top, row)]:
                continue
            for key, t, nr in self._screen_moves(top, row, r):
                nc = c + cost(key)
                if nc < best.get((t, nr), INF):
                    best[(t, nr)], tie = nc, tie + 1
                    heapq.heappush(heap, (nc, tie, (t, nr), keys + [key]))
        raise ValueError(f"row {r} unreachable")

    def goto(self, r, c=None):
        """Move to row r (and column c, if given) the cheapest way, counting keys like vimdrill does."""
        if self.screen:
            vkeys, self.top = self._screen_path(r)
            col = self._col_for(r, self.want)
            hkeys = [] if c is None else hpath(self.lines[r], col, c, self.motions)
            self.keys += vkeys + hkeys
            self.row, self.col = r, (col if c is None else c)
            self.want = INF if hkeys[-1:] == ["$"] else (self.want if not hkeys else self.col)
            return self
        best = None
        for vkeys, want in self._vertical(r):
            col = self._col_for(r, want)
            hkeys = [] if c is None else hpath(self.lines[r], col, c, self.motions)
            cost = sum(len(k) if not k.startswith(":") else len(k) - 3 for k in vkeys) + len(hkeys)
            if best is None or cost < best[0]:
                best = (cost, vkeys, hkeys, want, col)
        _, vkeys, hkeys, want, col = best
        self.keys += vkeys + hkeys
        self.row, self.col = r, (col if c is None else c)
        self.want = INF if hkeys[-1:] == ["$"] else (want if not hkeys else self.col)
        return self

    def _set(self, line, col):
        self.lines[self.row] = line
        self.col = self.want = col

    # edits (cursor rules match nvim with nostartofline + autoindent)
    def x(self):
        s = self.lines[self.row]
        s = s[:self.col] + s[self.col + 1:]
        self.keys.append("x")
        self._set(s, max(0, min(self.col, len(s) - 1)))

    def r(self, ch):
        s = self.lines[self.row]
        self.keys.append("r" + ("<Space>" if ch == " " else lit(ch)))
        self._set(s[:self.col] + ch + s[self.col + 1:], self.col)

    def tilde(self, n=1):
        s, c = self.lines[self.row], self.col
        self.keys.append(("" if n == 1 else str(n)) + "~")
        self._set(s[:c] + s[c:c + n].swapcase() + s[c + n:], min(c + n, len(s) - 1))

    def line_op(self, keys, fn):
        self.keys.append(keys)
        self._set(fn(self.lines[self.row]), 0)

    def J(self):
        cur, nxt = self.lines[self.row], self.lines[self.row + 1].lstrip(" \t")
        assert nxt and not cur.endswith(" ") and not nxt.startswith(")")
        self.keys.append("J")
        del self.lines[self.row + 1]
        # nvim moves a '^ on the joined line onto this one; forgetting it is simpler, and a later gi asserts
        if self.ins and self.ins[0] > self.row:
            self.ins = None if self.ins[0] == self.row + 1 else (self.ins[0] - 1, self.ins[1])
        self.top = None if self.screen else self.top
        self._set(cur + " " + nxt, len(cur))

    # inserts: '^ is where the cursor was when <Esc> was pressed, one past the typed text
    def A(self, text):
        self.keys.append("A" + lit(text) + "<Esc>")
        s = self.lines[self.row] + text
        self.ins = (self.row, len(s))
        self._set(s, len(s) - 1)

    def I(self, text):
        s = self.lines[self.row]
        fnb = len(s) - len(s.lstrip(" \t"))
        self.keys.append("I" + lit(text) + "<Esc>")
        self.ins = (self.row, fnb + len(text))
        self._set(s[:fnb] + text + s[fnb:], fnb + len(text) - 1)

    def i(self, text):
        s, c = self.lines[self.row], self.col
        self.keys.append("i" + lit(text) + "<Esc>")
        self.ins = (self.row, c + len(text))
        self._set(s[:c] + text + s[c:], c + len(text) - 1)

    def gi(self, text):
        """Resume inserting at '^, wherever the cursor is now."""
        assert self.ins, "gi before any insert"
        (r, c), s = self.ins, self.lines[self.ins[0]]
        self.keys.append("gi" + lit(text) + "<Esc>")
        self.practice.setdefault("gi", "This round is there to practice gi.")
        self.row, self.ins = r, (r, c + len(text))
        self.top = None if self.screen else self.top
        self._set(s[:c] + text + s[c:], c + len(text) - 1)

    def o(self, text, above=False):
        s = self.lines[self.row]
        new = s[:len(s) - len(s.lstrip(" \t"))] + text
        self.keys.append(("O" if above else "o") + lit(text) + "<Esc>")
        if not above:
            self.row += 1
        self.lines.insert(self.row, new)
        self.ins = (self.row, len(new))
        self.top = None if self.screen else self.top
        self.col = self.want = len(new) - 1


# ---------- random content ----------

def prose(rng, lo=5, hi=8):
    words = []
    for _ in range(rng.randint(lo, hi)):
        words.append(rng.choice(rng.choice([NOUNS, VERBS, ADJS, SMALL, SMALL])))
    return " ".join(words)


def sentence(rng, lo=5, hi=8):
    s = prose(rng, lo, hi)
    return s[0].upper() + s[1:] + "."


def code_line(rng):
    a, b, c, d = rng.sample(IDENTS, 4)
    return rng.choice([
        f"{a}.{b}({c}, {d}) returns {rng.choice(NOUNS)}",
        f"    {a}_{b} = {c}({d})",
        f"Use {a}.{b}({c}) to {rng.choice(VERBS)[:-1]} the {rng.choice(NOUNS)}.",
        f"if ({a} > {rng.randint(2, 99)}) {b} = {c}.{d};",
    ])


def unique_lines(rng, make, n):
    out = []
    while len(out) < n:
        s = make(rng)
        if s not in out:
            out.append(s)
    return out


# ---------- blocks: a few lines plus one instruction, reused across lessons ----------
# A block is (start_lines, instruction, apply) where apply(ed, row) edits the block that starts
# at row in ed and returns how many lines the block has afterwards.

def blk_doubled(rng, line=None, count=None):
    """1.1: remove doubled letters with word motions + x."""
    target = line or rng.choice([sentence, code_line])(rng)
    spots = [m for m in re.finditer(r"[A-Za-z]{3,}", target)]
    picks = sorted(rng.sample(spots, min(len(spots), count or rng.randint(1, 2))), key=lambda m: m.start())
    start, shown, cols, shift = target, [], [], 0
    for m in picks:
        at_end = rng.random() < 0.7
        pos = (m.end() - 1 if at_end else m.start()) + shift
        start = start[:pos] + start[pos] + start[pos:]
        shown.append((m.group() + m.group()[-1]) if at_end else (m.group()[0] + m.group()))
        cols.append(pos)
        shift += 1

    def apply(ed, row):
        for k, col in enumerate(cols):
            ed.goto(row, col - k)
            ed.x()
        return 1
    return [start], "Remove the doubled letters in " + ", ".join(shown) + " (w/b/e/W/B/E, 0/^/$, then x).", apply


def blk_statements(rng):
    """1.2: A; on statements, I// to comment one out."""
    names = rng.sample(IDENTS, rng.randint(2, 3))
    lines = [f"{rng.choice(['const', 'let'])} {n} = {rng.randint(1, 500)}" for n in names]
    out = rng.randrange(len(lines)) if rng.random() < 0.5 else None
    instr = "End the const/let lines with ; (A)."
    if out is not None:
        instr = f"Comment out the {names[out]} line with a leading // (I); end the other const/let lines with ; (A)."

    def apply(ed, row):
        for k in range(len(lines)):
            ed.goto(row + k)
            ed.I("// ") if k == out else ed.A(";")
        return len(lines)
    return lines, instr, apply


def blk_function(rng):
    """1.2: indent the body (I) and end it with ; (A)."""
    f, (p, q), op = rng.choice(FUNCS), rng.sample(["x", "y", "a", "b", "n", "m"], 2), rng.choice(OPS)
    lines = [f"function {f}({p}, {q}) {{", f"return {p} {op} {q}", "}"]

    def apply(ed, row):
        ed.goto(row + 1)
        ed.I("    ")
        ed.A(";")
        return 3
    return lines, f"Indent the return line in {f}() by 4 spaces (I) and end it with ; (A).", apply


def blk_indented(rng):
    """1.2: I on an indented line inserts after the indent (0i would land in front of it)."""
    f, (a, b, c) = rng.choice(FUNCS), rng.sample(IDENTS, 3)
    pad = " " * rng.choice([2, 4, 8])
    body = [f"{pad}const {a} = {b}({c})", f"{pad}{rng.choice(['log', 'debug', 'trace'])}({a})", f"{pad}return {a}"]
    out = rng.randrange(2)
    lines = [f"function {f}({c}) {{"] + body + ["}"]

    def apply(ed, row):
        for k in range(len(body)):
            ed.goto(row + 1 + k)
            ed.I("// ") if k == out else ed.A(";")
        return len(lines)
    instr = (f'In {f}(), comment out "{body[out].strip()}" with // after its indent (I, not 0i), '
             f"and end the other two body lines with ; (A).")
    return lines, instr, apply


def blk_resume(rng, avoid=()):
    """1.2: typing gets interrupted by a fix elsewhere; gi resumes exactly where typing stopped.
    In a file-only drill doing the fix first is shorter, so the order is prescribed and vimdrill
    checks that gi was pressed (Ed.practice). Names in `avoid` (the other blocks' words) are not
    reused, so instructions like "comment out the X line" stay unambiguous."""
    name, f, g = rng.sample([w for w in FUNCS if w not in avoid], 3)
    a, b, c, d, e = rng.sample([w for w in IDENTS if w not in avoid], 5)
    stray, k = rng.choice("QXZ"), rng.randrange(2)
    # already ended with ; so "end the const/let lines with ;" elsewhere in the round doesn't apply here
    lets = [f"  let {d} = {rng.randint(2, 99)};", f"  let {e} = {rng.randint(2, 99)};"]
    lets[k] = "  " + stray + lets[k].lstrip()
    call = f"  return {f}({a}, {b}) {rng.choice(OPS)} {g}({c})"
    lines = [f"function {name}({a}, {b}, {c}) {{", *lets, call, "}"]
    spot = call.index(f"{f}({a}, {b}") + len(f"{f}({a}, {b}")

    def apply(ed, row):
        ed.goto(row + 3, spot)
        ed.i(f", {d}")
        ed.goto(row + 1 + k, 2)
        ed.x()
        ed.gi(f", {e}")
        ed.practice["gi"] = (
            "This round trains the interruption: type the first part, Esc, fix the stray character elsewhere, "
            "then gi puts you back in insert mode exactly where you stopped. You got back to the typing spot "
            "without gi: either you moved there yourself, or you did the fix first and typed everything in one go. "
            "Same file, but it skips what the round is for. Retry: after the fix, press gi instead of moving.")
        return len(lines)
    instr = (f'In {name}(), give {f}() two more arguments, {d} and {e}, with an interruption (practice gi): '
             f'type ", {d}" after {b}; then, as if you just spotted it, Esc and delete the stray {stray} on the '
             f'"let {(d, e)[k]}" line (x); then press gi and type ", {e}". gi drops you back into insert mode where you stopped typing.')
    return lines, instr, apply


def blk_bracket(rng):
    """1.3: % to the matching bracket, then delete the stray character after it."""
    f, a, b, c, d = rng.choice(FUNCS), *rng.sample(IDENTS, 4)
    stray = rng.choice("!?#")
    head = f"Check {f}("
    inner = rng.choice([f"{a}, [{b}, {c}], {{{d}: {rng.randint(1, 9)}}}", f"{a}({b}), [{c}], {d}",
                        f"[{a}, {b}], ({c} + {d})"])
    tail = rng.choice([" before the " + rng.choice(NOUNS) + ".", " and " + rng.choice(VERBS) + " on."])
    line = head + inner + ")" + stray + tail

    def apply(ed, row):
        ed.goto(row, len(head) + len(inner) + 1)
        ed.x()
        return 1
    return [line], f"Delete the stray {stray} right after the ) that closes {f}( - put the cursor on ( and press %.", apply


def blk_fix_caps(rng):
    """1.4: ~ on single letters."""
    words = prose(rng, 5, 7).split()
    k = rng.randrange(2, len(words))
    words[k] = words[k].capitalize()
    target = " ".join([words[0].capitalize()] + [w.lower() for w in words[1:]])
    start = " ".join(words)
    col = len(" ".join(words[:k])) + 1

    def apply(ed, row):
        ed.goto(row, 0)
        ed.tilde()
        ed.goto(row, col)
        ed.tilde()
        return 1
    return [start], f'Capitalize "{words[0]}" and lowercase "{words[k]}" (~).', apply


def blk_shout(rng):
    """1.4: count + ~ to lowercase a phrase."""
    a, b = prose(rng, 2, 3), prose(rng, 2, 3)
    phrase = f"{rng.choice(ADJS)} {rng.choice(NOUNS)}"
    start = f"{a} {phrase.upper()} {b}"

    def apply(ed, row):
        ed.goto(row, len(a) + 1)
        ed.tilde(len(phrase))
        return 1
    return [start], f'Lowercase "{phrase.upper()}" (a count works: {len(phrase)}~).', apply


def blk_line_case(rng):
    """1.4: g~~ / gUU / guu."""
    target = " ".join(w.capitalize() for w in prose(rng, 4, 6).split())
    kind = rng.choice(["toggle", "upper", "lower"])
    if kind == "toggle":
        start, keys, fn, instr = target.swapcase(), "g~~", str.swapcase, "Fix the caps-lock line in one go (g~~)."
    elif kind == "upper":
        start, keys, fn = target, "gUU", str.upper
        instr = f'Make the "{target.split()[0]} ..." line all caps (gUU).'
    else:
        start, keys, fn = target.upper(), "guu", str.lower
        instr = f'Make the "{start.split()[0]} ..." line all lowercase (guu).'

    def apply(ed, row):
        ed.goto(row)
        ed.line_op(keys, fn)
        return 1
    return [start], instr, apply


def blk_join(rng):
    """1.4: J."""
    a, b = prose(rng, 3, 4), prose(rng, 3, 4) + "."

    def apply(ed, row):
        ed.goto(row)
        ed.J()
        return 1
    return [a, "  " + b], f'Join the line ending in "{a.split()[-1]}" with the next one (J).', apply


def blk_commas(rng):
    """1.4: r to replace characters."""
    words = prose(rng, 5, 7).split()
    cuts = sorted(rng.sample(range(1, len(words)), rng.randint(2, 3)))
    start = ""
    for k, w in enumerate(words):
        start += ("," if k in cuts else " " if k else "") + w
    cols = [m.start() for m in re.finditer(",", start)]

    def apply(ed, row):
        for col in cols:
            ed.goto(row, col)
            ed.r(" ")
        return 1
    return [start], f'Replace the commas on the "{words[0]} ..." line with spaces (r).', apply


def compose(blocks, gap=False, header=None, footer=None, intro=""):
    """Stack blocks into one file and play their solutions top to bottom."""
    lines, instr = [], []
    for k, (blines, text, _) in enumerate(blocks):
        lines += blines + ([""] if gap and k < len(blocks) - 1 else [])
        instr.append(text)
    ed = Ed(lines)
    if header:
        instr.insert(0, f'Add a first line: {header} (O).')
    if footer:
        instr.append(f"Add a last line: {footer} (o).")
    row = 0
    for blines, _, apply in blocks:
        row += apply(ed, row) + (1 if gap else 0)
    if footer:
        ed.goto(len(ed.lines) - 1)
        ed.o(footer)
    if header:
        ed.goto(0)
        ed.o(header, above=True)
    text = (intro + "\n" if intro else "") + "\n".join(f"{k}. {t}" for k, t in enumerate(instr, 1))
    return drill(text, ed, lines)


def drill(instructions, ed, start_lines):
    spec = {"instructions": instructions, "solution": ed.solution,
            "start": {"main.txt": "\n".join(start_lines)}, "target": {"main.txt": "\n".join(ed.lines)}}
    if ed.practice:
        spec["practice"] = dict(ed.practice)
    return spec


# ---------- generators ----------

def gen_1_1(rng):
    lines = unique_lines(rng, lambda r: r.choice([sentence, code_line, code_line])(r), rng.randint(4, 5))
    blocks = [blk_doubled(rng, line, 1 if k % 2 else rng.randint(1, 2)) for k, line in enumerate(lines)]
    words = [w for _, text, _ in blocks for w in re.findall(r"in (.*) \(", text)[0].split(", ")]
    d = compose(blocks)
    d["instructions"] = ("Remove the doubled letters: " + ", ".join(words) + ".\n"
                         "Use w/b/e/W/B/E and 0/^/$ to get there, then x. Avoid holding ← / →.")
    return d


def with_resume(rng, makers):
    """Build the blocks, the gi block last so it can avoid every name the others use; order is kept."""
    built = {k: m(rng) for k, m in enumerate(makers) if m is not blk_resume}
    words = set(re.findall(r"\w+", "\n".join(l for b in built.values() for l in b[0])))
    return [built[k] if k in built else blk_resume(rng, words) for k in range(len(makers))]


def gen_1_2(rng):
    blocks = with_resume(rng, [blk_statements, blk_function, blk_indented, blk_resume])
    rng.shuffle(blocks)
    f = re.search(r"function (\w+)", "\n".join(l for b in blocks for l in b[0])).group(1)
    header = f"// {prose(rng, 2, 3)}" if rng.random() < 0.7 else None
    footer = f"export {{ {f} }};" if rng.random() < 0.7 or not header else None
    return compose(blocks, header=header, footer=footer,
                   intro="Use O, o, A, I and gi. Don't move with $ or 0 before inserting.")


SCREEN_ROWS = 14
CHORES = ["fix", "paint", "clean", "check", "move", "sort", "polish", "label", "pack", "oil"]


def gen_1_3_screen(rng):
    """1.3: a long list in a fixed-height window - page with Ctrl-d/u, land with H/M/L."""
    h, n = SCREEN_ROWS, rng.randint(56, 64)
    lines = unique_lines(rng, lambda r: f"- {r.choice(CHORES)} the {r.choice(ADJS)} {r.choice(NOUNS)}", n)
    half, off = h // 2, {"H": 0, "M": (h - 1) // 2, "L": h - 1}
    while True:  # a tour down the file and back up, each stop a page or two away
        top, rows = 0, [off["M"]]
        for pages, land in ((rng.randint(2, 3), rng.choice("HL")), (rng.randint(1, 2), "M"),
                            (-rng.randint(1, 2), rng.choice("HL"))):
            top += pages * half
            rows.append(top + off[land])
        if rng.random() < 0.5:
            rows.append(n - 1)
        if len(set(rows)) == len(rows):
            break
    ed = Ed(lines, screen=h)
    for r in rows:
        ed.goto(r)
        ed.A(" DONE")
    text = (f"The window is fixed at {h} rows; the file has {n} lines. Page with Ctrl-d / Ctrl-u, land with H / M / L\n"
            "(zt / zz / zb re-frame the screen first). :N works too but costs more keys.\n"
            "Append \" DONE\" to these lines, in this order (A):\n"
            + "\n".join(f'{k}. line {r + 1}: "{lines[r][2:]}"' for k, r in enumerate(rows, 1)))
    return {**drill(text, ed, lines), "screen": h, "diff": False}


def gen_1_3(rng):
    if rng.random() < 0.5:
        return gen_1_3_screen(rng)
    paras =[unique_lines(rng, lambda r: sentence(r, 4, 7), rng.randint(2, 4)) for _ in range(rng.randint(4, 5))]
    bracket = None
    if rng.random() < 0.6:
        bracket = blk_bracket(rng)
        p = rng.randrange(len(paras))
        paras[p].insert(rng.randint(0, len(paras[p])), bracket[0][0])
    lines = [l for k, p in enumerate(paras) for l in (p + ([""] if k < len(paras) - 1 else []))]
    candidates = [k for k in range(1, len(lines) - 1) if lines[k] and not lines[k].startswith("Check ")]
    stray_row, stray = rng.choice(candidates), rng.choice("XQZ")
    lines[stray_row] = stray + lines[stray_row]
    marker = rng.choice(["---", "***", "~~~", "* * *"])
    end = rng.choice([" (end)", " THE END", " [done]", " -- fin"])
    title = "# " + " ".join(w.capitalize() for w in prose(rng, 2, 3).split())

    ed = Ed(lines)
    steps = [(f'Line {stray_row + 1} starts with a stray {stray}: jump there with :{stray_row + 1} and delete it.',
              lambda: (ed.goto(stray_row, 0), ed.x()))]
    if bracket:
        row = lines.index(bracket[0][0])
        steps.append((bracket[1], lambda: bracket[2](ed, row)))
    blanks = [k for k, l in enumerate(lines) if l == ""]
    steps.append((f"Put {marker} on each blank line. Hop between them with }} and {{.",
                  lambda: [(ed.goto(k), ed.i(marker)) for k in blanks]))
    steps.append((f'Jump to the last line (G) and append "{end}".', lambda: (ed.goto(len(ed.lines) - 1), ed.A(end))))
    rng.shuffle(steps)
    steps.append((f'Jump to the first line (gg) and add "{title}" above it.',
                  lambda: (ed.goto(0), ed.o(title, above=True))))
    for _, run in steps:
        run()
    text = "\n".join(f"{k}. {t}" for k, (t, _) in enumerate(steps, 1)) + "\nDo the steps in order (line numbers are for the file as it starts)."
    return drill(text, ed, lines)


def gen_1_4(rng):
    makers = [blk_fix_caps, blk_shout, blk_line_case, blk_join, blk_commas]
    picks = rng.sample(makers, 4) + ([rng.choice([blk_line_case, blk_shout])] if rng.random() < 0.5 else [])
    rng.shuffle(picks)
    return compose([m(rng) for m in picks], intro="Fix every line without entering insert mode.")


def gen_1_5(rng):
    makers = [blk_doubled, blk_statements, blk_function, blk_indented, blk_resume, blk_bracket, blk_fix_caps,
              blk_shout, blk_line_case, blk_join, blk_commas]
    blocks = with_resume(rng, rng.sample(makers, 5))
    header = "# " + " ".join(w.capitalize() for w in prose(rng, 2, 3).split()) if rng.random() < 0.5 else None
    return compose(blocks, gap=True, header=header, intro="Week 1 review: make the left side match the right.")


GENERATORS = {"1.1": gen_1_1, "1.2": gen_1_2, "1.3": gen_1_3, "1.4": gen_1_4, "1.5": gen_1_5}


def pick_rounds(rng, unlocked, current, misses, n=4):
    """Today's lesson first, then a weighted spread of everything unlocked, no lesson twice in a row.
    Lessons with open quiz misses and today's lesson come up more often."""
    missed = {qid.rsplit("-", 1)[0] for qid in misses}
    rounds = [current]
    while len(rounds) < n:
        cands = [l for l in unlocked if l != rounds[-1]] or unlocked
        weights = [1 + 2 * (l in missed) + 2 * (l == current) for l in cands]
        rounds.append(rng.choices(cands, weights)[0])
    return rounds
