#!/usr/bin/env python3
"""Převede skripta ve WooWoo (src/*.woo v abecedním pořadí) na web pro MkDocs Material.

Zdrojem pravdy zůstávají .woo soubory; všechno v .build/mkdocs*/ se generuje znovu při každém spuštění.

  python3 tools/woo2mkdocs.py            # web: vygeneruje .build/mkdocs/ (docs + mkdocs.yml)
  python3 tools/woo2mkdocs.py --pdf      # PDF: vygeneruje .build/mkdocs-pdf/ (celá skripta jako jedna stránka)
  python3 tools/woo2mkdocs.py --only=04,05   # náhled jen kapitol ze souborů 04*, 05* do .build/preview-04-05/
Sestavení a umístění výstupů řeší tools/build_web.sh a tools/build_pdf.sh (výstup: ../skripta/).

Jak se co převádí:
  .Chapter            -> složka s index.md (úvod kapitoly + seznam oddílů)
  .Section            -> samostatná stránka, .Subsection -> nadpis na stránce
  objekty (.Example:) -> rámečky Material (admonition), .Solution: a .Proof: jsou rozbalovací,
  u .Example: se rozbaluje vše za prvním blokem (zadáním)
  režim --pdf         -> jedna stránka: kapitola = h1, oddíl = h2, pododdíl = h3; řešení jsou rozbalená,
                         odkazy vedou na kotvy uvnitř dokumentu (v PDF fungují jako skoky)
  !tikz:              -> SVG (přeloží se lualatexem přes tools/check_tikz.py, PDF -> SVG přes PyMuPDF)
  !pseudocode:        -> číslovaný HTML výpis
  matematika $...$    -> MathJax
Obsah stránek se píše jako hotové HTML (Markdown jsou jen nadpisy kvůli obsahu a hledání),
takže se v textu nic nerozbije o znaky jako | * _ uvnitř vzorců.
"""
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULT = Path(os.environ.get("SKRIPTA_OUT") or ROOT.parent / "skripta")    # sem jdou hotové výstupy
PDF = "--pdf" in sys.argv[1:]
ONLY = next((a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("--only=")), None)   # náhled
if ONLY:
    OUT = ROOT / ".build" / ("preview-" + "-".join(ONLY)) / "mkdocs"
    SITE = OUT.parent / "site"
else:
    OUT = ROOT / ".build" / ("mkdocs-pdf" if PDF else "mkdocs")
    SITE = ROOT / ".build" / "site-pdf" if PDF else RESULT / "html"
DOCS = OUT / "docs"
LAZY = "" if PDF else ' loading="lazy"'      # při tisku do PDF se líně načítané obrázky nemusí stihnout načíst
ASSETS = ROOT / "tools" / "mkdocs"
sys.path.insert(0, str(ROOT / "tools"))
import check_tikz as ct  # noqa: E402

SITE_NAME = "NI-ICC – skripta"
SITE_DESC = "Skripta NI-ICC (Úvod do výpočetní složitosti, FIT ČVUT)"
PX_PER_PT = 1.45         # měřítko obrázků: 11pt písmo v obrázku ~ 16 px, jako okolní text

HEADER = re.compile(r"^([.!])([A-Za-z_]+):\s*$")
PART = re.compile(r"^\.(Chapter|Section|Subsection)\s+(.*\S)\s*$")
META = re.compile(r"^([a-z_]+):\s*(.*)$")
RAW_ENVS = {"tikz", "pseudocode", "codeblock", "raw", "equation", "align", "gather", "image"}

# objekt -> (typ rámečku Material, český název před titulkem nebo None)
OBJECTS = {
    "Definition": ("info", "Definice"),
    "Theorem": ("info", "Věta"),
    "Lemma": ("info", "Lemma"),
    "Proposition": ("info", "Tvrzení"),
    "Corollary": ("info", "Důsledek"),
    "Observation": ("note", "Pozorování"),
    "Example": ("example", "Příklad"),
    "Exercise": ("question", None),
    "Remark": ("note", None),
    "Warning": ("warning", None),
    "Procedure": ("abstract", "Postup"),
    "Concept": ("tip", None),
    "Question": ("question", None),
    "Algorithm": ("abstract", "Algoritmus"),
    "Proof": ("quote", "Důkaz"),
}
# číslované objekty: skupina čítače (čísluje se v rámci kapitoly, např. Definice 4.2, Obrázek 4.7)
COUNTERS = {"Definition": "thm", "Theorem": "thm", "Lemma": "thm", "Proposition": "thm", "Corollary": "thm",
            "Observation": "thm", "Example": "thm", "Figure": "fig", "Table": "tab", "Algorithm": "alg"}
FLOATS = {"Figure": "Obrázek", "Table": "Tabulka"}
DEFAULT_TITLE = {"Remark": "Poznámka", "Warning": "Varování", "Concept": "Myšlenka", "Question": "Zkus sám",
                 "Exercise": "Cvičení"}
# pododdíly, kterými v oddíle začíná jádro a úlohy podtématu
PART_PREFIXES = ("Shrnutí:", "Řešené úlohy:")
# záložky webu podle čísla v názvu prvního souboru kapitoly
GROUPS = [(1, 2, "Model a vyčíslitelnost"), (3, 4, "Časová složitost"), (5, 11, "NP-úplnost"),
          (12, 13, "Prostorová složitost"), (14, 15, "SAT a ILP v praxi"), (16, 99, "Test a přehledy")]
APPENDIX_FROM = 16       # kapitoly ze souborů 16-… a výš jsou přílohy: značí se A, B, C místo čísel

warnings = []


def warn(msg):
    warnings.append(msg)


class Node:
    def __init__(self, kind, **kw):
        self.kind = kind            # part | env | par
        self.name = kw.get("name", "")
        self.sigil = kw.get("sigil", ".")
        self.meta = kw.get("meta", {})
        self.children = kw.get("children", [])
        self.raw = kw.get("raw", [])
        self.text = kw.get("text", "")
        self.src = kw.get("src", "")


def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        q = v[0]
        v = v[1:-1]
        v = v.replace("''", "'") if q == "'" else v.replace('\\"', '"')
    return v


def read_meta(lines, i):
    meta = {}
    while i < len(lines) and lines[i].strip() and lines[i].startswith("  ") and not lines[i].startswith("   "):
        m = META.match(lines[i].strip())
        if not m:
            break
        meta[m.group(1)] = unquote(m.group(2))
        i += 1
    return meta, i


def parse_blocks(lines, src):
    """lines: řádky bloku odsazené od nuly. Vrací seznam uzlů."""
    nodes = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        top = not line.startswith(" ")
        m = PART.match(line) if top else None
        if m:
            meta, j = read_meta(lines, i + 1)
            nodes.append(Node("part", name=m.group(1), text=m.group(2), meta=meta, src=src))
            i = j
            continue
        m = HEADER.match(line) if top else None
        if m:
            meta, j = read_meta(lines, i + 1)
            body = []
            k = j
            while k < n and (not lines[k].strip() or lines[k].startswith(" ")):
                body.append(lines[k][2:] if lines[k].strip() else "")
                k += 1
            while body and not body[0].strip():
                body.pop(0)
            while body and not body[-1].strip():
                body.pop()
            node = Node("env", sigil=m.group(1), name=m.group(2), meta=meta, src=src)
            if m.group(1) == "!" or m.group(2) in RAW_ENVS:
                node.raw = body
            else:
                node.children = parse_blocks(body, src)
            nodes.append(node)
            i = k
            continue
        buf = []
        while i < n and lines[i].strip():
            if buf and not lines[i].startswith(" ") and (HEADER.match(lines[i]) or PART.match(lines[i])):
                break
            buf.append(lines[i].strip())
            i += 1
        nodes.append(Node("par", text=" ".join(buf), src=src))
    return nodes


# ---------------------------------------------------------------- text -> HTML

INLINE = re.compile(
    r'(?P<math>\$(?:[^$\\]|\\.)+\$)'
    r'|"(?P<q>(?:[^"$]|\$(?:[^$\\]|\\.)+\$)*)"'
    r'(?:\.(?P<env>notion|emphasize|code|underline|quoted|small|footnote)(?![A-Za-z])|#(?P<hash>[A-Za-z0-9-]+))'
    r'|\.(?P<ref>reference|eqref):(?P<label>[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)')


def esc(s):
    return html.escape(s, quote=False).replace("~", "&nbsp;")


BASE_COLORS = {"red": "FF0000", "green": "00FF00", "blue": "0000FF", "black": "000000", "white": "FFFFFF",
               "gray": "808080", "darkgray": "404040", "lightgray": "BFBFBF", "orange": "FF8000", "violet": "800080",
               "purple": "BF0040", "brown": "BF8040", "cyan": "00FFFF", "magenta": "FF00FF", "yellow": "FFFF00",
               "teal": "008080", "olive": "808000", "lime": "BFFF00", "pink": "FFBFBF"}
COLORS = {}


def load_colors():
    COLORS.update({k: tuple(int(v[i:i + 2], 16) for i in (0, 2, 4)) for k, v in BASE_COLORS.items()})
    src = "".join((ROOT / "tools" / "tikz" / f).read_text(encoding="utf-8")
                  for f in ("macros.tex", "styles.tex") if (ROOT / "tools" / "tikz" / f).exists())
    for m in re.finditer(r"\\definecolor\{(\w+)\}\{HTML\}\{([0-9A-Fa-f]{6})\}|\\colorlet\{(\w+)\}\{([^{}]+)\}", src):
        if m.group(1):
            COLORS[m.group(1)] = tuple(int(m.group(2)[i:i + 2], 16) for i in (0, 2, 4))
        else:
            c = mix_color(m.group(4))
            if c:
                COLORS[m.group(3)] = c


def mix_color(expr):
    """Výraz balíku xcolor (např. defc!70!black, red!20) -> (r, g, b), nebo None."""
    parts = [x.strip() for x in expr.split("!")]
    cur = COLORS.get(parts[0])
    if cur is None:
        return None
    i = 1
    while i < len(parts):
        try:
            pct = float(parts[i]) / 100
        except ValueError:
            return None
        other = COLORS.get(parts[i + 1]) if i + 1 < len(parts) else COLORS["white"]
        if other is None:
            return None
        cur = tuple(pct * a + (1 - pct) * b for a, b in zip(cur, other))
        i += 2
    return cur


def fix_colors(tex):
    def one(m):
        c = mix_color(m.group(2))
        if not c:
            return m.group(0)
        return m.group(1) + "{#%02X%02X%02X}" % tuple(max(0, min(255, round(x))) for x in c)
    return re.sub(r"(\\(?:textcolor|color|clr))\{([A-Za-z][A-Za-z0-9!. ]*)\}", one, tex)


def math_inline(body):
    return '<span class="arithmatex">\\(' + html.escape(fix_colors(body), quote=False) + '\\)</span>'


class Ctx:
    def __init__(self, page):
        self.page = page            # cesta stránky (.md) relativně k docs
        self.title = ""             # nejbližší titulek (pro alt obrázků)
        self.prev_object = ""


def rel_url(ctx, target_page, anchor=""):
    cur = os.path.dirname(ctx.page)
    url = os.path.relpath(re.sub(r"\.md$", ".html", target_page), cur or ".").replace(os.sep, "/")
    return url + ("#" + anchor if anchor else "")


LABELS = {}     # label -> dict(page, anchor, number, title)


def link(ctx, label, inner_html=None):
    t = LABELS.get(label)
    if not t:
        warn(f"neznámý štítek '{label}' (stránka {ctx.page})")
        return inner_html if inner_html is not None else esc(label)
    text = inner_html if inner_html is not None else esc(t["number"] or t["title"])
    if PDF:     # vše je na jedné stránce; kapitoly a oddíly mají kotvu se jménem svého štítku
        return f'<a href="#{t["anchor"] or label}">{text}</a>'
    return f'<a href="{rel_url(ctx, t["page"], t["anchor"])}">{text}</a>'


def inline(text, ctx):
    out = []
    pos = 0
    for m in INLINE.finditer(text):
        out.append(esc(text[pos:m.start()]))
        pos = m.end()
        if m.group("math"):
            # interpunkce hned za vzorcem (tečka, čárka, uvozovka, závorka) nesmí spadnout na další řádek
            tail = re.match(r"[“”.,;:!?)\]]+", text[pos:])
            if tail:
                pos += tail.end()
                out.append('<span class="woo-nobr">' + math_inline(m.group("math")[1:-1]) + esc(tail.group(0)) + "</span>")
            else:
                out.append(math_inline(m.group("math")[1:-1]))
        elif m.group("ref"):
            # „cvičení .reference:cv-1-1“ by se vypsalo „cvičení Cvičení 1.1“: slovo zopakované z textu z odkazu vypustíme
            t = LABELS.get(m.group("label"))
            shown = (t["number"] or t["title"]) if t else ""
            before = re.search(r"(\w+)[\s(~]*$", text[:m.start()])
            first = re.match(r"(\w+):?\s+(?=\S)", shown)
            if before and first and before.group(1).casefold() == first.group(1).casefold():
                out.append(link(ctx, m.group("label"), esc(shown[first.end():])))
            else:
                out.append(link(ctx, m.group("label")))
        elif m.group("hash"):
            out.append(link(ctx, m.group("hash"), inline(m.group("q"), ctx)))
        else:
            env, q = m.group("env"), m.group("q")
            if env == "notion":
                out.append("<strong>" + inline(q, ctx) + "</strong>")
            elif env == "emphasize":
                out.append("<em>" + inline(q, ctx) + "</em>")
            elif env == "code":
                out.append("<code>" + html.escape(q, quote=False) + "</code>")
            elif env == "underline":
                out.append("<u>" + inline(q, ctx) + "</u>")
            elif env == "small":
                out.append("<small>" + inline(q, ctx) + "</small>")
            elif env == "quoted":
                out.append("„" + inline(q, ctx) + "“")
            else:
                out.append(" <small>(" + inline(q, ctx) + ")</small>")
    out.append(esc(text[pos:]))
    return "".join(out)


PLAIN_SYMBOLS = {"ne": "≠", "neq": "≠", "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "to": "→", "times": "×",
                 "Rightarrow": "⇒", "Leftarrow": "⇐", "iff": "⇔", "lor": "∨", "land": "∧", "neg": "¬", "lnot": "¬",
                 "redp": " ≤ₚ ", "in": " ∈ ", "notin": " ∉ ", "subseteq": " ⊆ ", "subsetneq": " ⊊ ", "cup": "∪",
                 "cap": "∩", "ell": "ℓ", "varphi": "φ", "Phi": "Φ", "Sigma": "Σ", "Sig": "Σ", "delta": "δ",
                 "mid": " | ", "dots": "…", "ldots": "…", "cdot": "·", "log": "log", "blank": "␣", "N": "ℕ",
                 "mapsto": " ↦ ", "rightarrow": "→", "leftarrow": "←", "Rgt": "→", "Lft": "←", "quad": " ",
                 "PP": "P", "NP": "NP", "NPhat": "NP", "EXP": "EXP", "NEXP": "NEXP", "DTIME": "DTIME",
                 "NTIME": "NTIME", "DSPACE": "DSPACE", "NSPACE": "NSPACE", "PSPACE": "PSPACE",
                 "NPSPACE": "NPSPACE", "LL": "L", "NL": "NL", "coNP": "coNP", "coNL": "coNL",
                 "ANO": "ANO", "NE": "NE", "qA": "q_A", "qR": "q_R", "exists": "∃", "forall": "∀"}


def plain(text):
    """Text bez značek (pro navigaci, alt texty, <title>)."""
    def rep(m):
        if m.group("math"):
            s = m.group("math")[1:-1]
            s = re.sub(r"\\enc\{([^{}]*)\}", r"⟨\1⟩", s)
            s = re.sub(r"\\overset\{\?\}\{=\}", " =? ", s)
            s = re.sub(r"\\(?:mathit|mathrm|mathtt|text|mathcal|mathbf|mathsf|textsf|prob|cls)\{([^{}]*)\}", r"\1", s)
            s = re.sub(r"\\[A-Za-z]+", lambda x: PLAIN_SYMBOLS.get(x.group(0)[1:], ""), s)
            s = re.sub(r"\\[,;! ]", " ", s)
            return re.sub(r"\s+", " ", re.sub(r"[{}\\]", "", s)).strip()
        if m.group("ref"):
            t = LABELS.get(m.group("label"))
            return (t["number"] or t["title"]) if t else m.group("label")
        return plain(m.group("q"))
    return INLINE.sub(rep, text).replace("~", " ")


def md_heading_text(text):
    """Titulek pro markdownový nadpis: matematiku nechá ($...$ zpracuje arithmatex), zbytek escapuje."""
    out = []
    pos = 0
    for m in INLINE.finditer(text):
        out.append(re.sub(r"([\\`*_{}\[\]<>#|])", r"\\\1", text[pos:m.start()]))
        pos = m.end()
        if m.group("math"):
            out.append(m.group("math"))
        elif m.group("ref") or m.group("hash"):
            out.append(re.sub(r"([\\`*_{}\[\]<>#|])", r"\\\1", plain(m.group(0))))
        else:
            q = md_heading_text(m.group("q"))
            out.append({"notion": f"**{q}**", "emphasize": f"*{q}*", "code": f"`{m.group('q')}`"}.get(m.group("env"), q))
    out.append(re.sub(r"([\\`*_{}\[\]<>#|])", r"\\\1", text[pos:]))
    return "".join(out).replace("~", " ")


# ---------------------------------------------------------------- pseudokód

ALG_CMD = re.compile(r"\\(STATE|IF|ELSIF|ELSE|ENDIF|FORALL|FOR|ENDFOR|WHILE|ENDWHILE|RETURN|COMMENT|"
                     r"PROCEDURE|ENDPROCEDURE|REQUIRE|ENSURE)(?![A-Za-z])")


def read_group(s, i, open_ch="{", close_ch="}"):
    """s[i] == open_ch; vrátí (obsah, index za uzavírací závorkou)."""
    depth = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


TEXT_CMDS = {"textbf": ("<b>", "</b>"), "textit": ("<i>", "</i>"), "emph": ("<i>", "</i>"),
             "textsc": ('<span class="woo-sc">', "</span>"), "texttt": ("<code>", "</code>"),
             "textrm": ("", ""), "text": ("", "")}


TEXT_SYMBOLS = {"quad": "&emsp;", "qquad": "&emsp;&emsp;", "dots": "…", "ldots": "…", "gets": "←", "to": "→"}


def latex_text(s):
    """Krátký LaTeXový text (řádek pseudokódu) -> HTML."""
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "$":
            j = i + 1
            while j < len(s) and s[j] != "$":
                j += 2 if s[j] == "\\" else 1
            out.append(math_inline(s[i + 1:j]))
            i = j + 1
        elif c == "\\":
            m = re.match(r"\\([A-Za-z]+)\s*", s[i:])
            if m and m.group(1) in TEXT_CMDS and i + m.end() < len(s) and s[i + m.end()] == "{":
                body, j = read_group(s, i + m.end())
                a, b = TEXT_CMDS[m.group(1)]
                out.append(a + latex_text(body) + b)
                i = j
            elif m and m.group(1) in TEXT_SYMBOLS:
                out.append(TEXT_SYMBOLS[m.group(1)])
                i += m.end()
            elif m:
                warn(f"pseudokód: neznámý příkaz \\{m.group(1)}")
                out.append(esc(m.group(0)))
                i += m.end()
            else:
                nxt = s[i + 1:i + 2]
                out.append({";": " ", ",": " ", " ": " ", "!": "", "\\": "<br>"}.get(nxt, esc(nxt)))
                i += 2
        elif c == "~":
            out.append("&nbsp;")
            i += 1
        elif c in "{}":
            i += 1
        else:
            out.append(html.escape(c, quote=False))
            i += 1
    return "".join(out)


def render_pseudocode(body):
    s = " ".join(l.strip() for l in body if l.strip())
    lines = []          # [indent, html, comment]
    indent = 0
    cur = None

    def new_line(text=""):
        nonlocal cur
        cur = [indent, text, ""]
        lines.append(cur)

    def add_text(t):
        t = t.strip()
        if not t:
            return
        if cur is None:
            new_line()
        cur[1] += (" " if cur[1] else "") + latex_text(t)

    pos = 0
    while True:
        m = ALG_CMD.search(s, pos)
        if not m:
            add_text(s[pos:])
            break
        add_text(s[pos:m.start()])
        cmd = m.group(1)
        i = m.end()
        opt = None
        while i < len(s) and s[i] == " ":
            i += 1
        if cmd in ("IF", "ELSIF", "FOR", "FORALL", "WHILE") and i < len(s) and s[i] == "[":
            opt, i = read_group(s, i, "[", "]")
        args = []
        need = {"IF": 1, "ELSIF": 1, "FOR": 1, "FORALL": 1, "WHILE": 1, "COMMENT": 1, "PROCEDURE": 2}.get(cmd, 0)
        for _ in range(need):
            while i < len(s) and s[i] == " ":
                i += 1
            if i < len(s) and s[i] == "{":
                a, i = read_group(s, i)
                args.append(a)
        pos = i
        if cmd == "STATE":
            new_line()
        elif cmd == "RETURN":
            if cur is None or cur[1]:
                new_line()
            cur[1] = "<b>return</b>"
        elif cmd in ("REQUIRE", "ENSURE"):
            new_line("<b>Vstup:</b>" if cmd == "REQUIRE" else "<b>Výstup:</b>")
        elif cmd == "COMMENT":
            if cur is None:
                new_line()
            cur[2] = latex_text(args[0])
        elif cmd == "PROCEDURE":
            new_line(f'<b>procedure</b> <span class="woo-sc">{latex_text(args[0])}</span>({latex_text(args[1])})')
            indent += 1
            cur = None
        elif cmd in ("IF", "FOR", "FORALL", "WHILE"):
            kw, end = {"IF": ("if", "then"), "FOR": ("for", "do"), "FORALL": ("for all", "do"),
                       "WHILE": ("while", "do")}[cmd]
            new_line(f"<b>{kw}</b> {latex_text(args[0])} <b>{end}</b>")
            if opt:
                cur[2] = latex_text(opt)
            indent += 1
            cur = None
        elif cmd == "ELSIF":
            indent = max(0, indent - 1)
            new_line(f"<b>else if</b> {latex_text(args[0])} <b>then</b>")
            indent += 1
            cur = None
        elif cmd == "ELSE":
            indent = max(0, indent - 1)
            new_line("<b>else</b>")
            indent += 1
            cur = None
        else:   # END*
            indent = max(0, indent - 1)
            cur = None
    items = []
    for ind, text, com in lines:
        c = f'<span class="woo-algo-c">▷ {com}</span>' if com else ""
        items.append(f'<li style="--ind:{ind}"><span class="woo-algo-l">{text}</span>{c}</li>')
    return '<ol class="woo-algo">' + "".join(items) + "</ol>"


# ---------------------------------------------------------------- bloky -> HTML

FIG_SIZE = {}       # filename -> (šířka pt, výška pt)


def col_aligns(spec):
    aligns = []
    i = 0
    while i < len(spec):
        c = spec[i]
        if c in "lcr":
            aligns.append({"l": "left", "c": "center", "r": "right"}[c])
            i += 1
        elif c in "pmbX":
            aligns.append("left")
            i += 1
            if i < len(spec) and spec[i] == "{":
                _, i = read_group(spec, i)
        elif c in "@><!":
            i += 1
            if i < len(spec) and spec[i] == "{":
                _, i = read_group(spec, i)
        else:
            i += 1
    return aligns


def item_content(node, ctx):
    kids = node.children
    if len(kids) == 1 and kids[0].kind == "par":
        return inline(kids[0].text, ctx)
    return render_nodes(kids, ctx)


def render_env(node, ctx):
    name = node.name
    if name == "itemize" or name == "enumerate":
        items = [c for c in node.children if c.kind == "env" and c.name == "item"]
        custom = any("bullet" in it.meta for it in items)
        if custom:
            lis = "".join(f'<li><span class="woo-bul">{inline(it.meta.get("bullet", "•"), ctx)}</span>'
                          f'<div>{item_content(it, ctx)}</div></li>' for it in items)
            return f'<ul class="woo-custom">{lis}</ul>'
        tag = "ul" if name == "itemize" else "ol"
        attr = f' type="{html.escape(node.meta["type"])}"' if name == "enumerate" and node.meta.get("type") else ""
        return f"<{tag}{attr}>" + "".join(f"<li>{item_content(it, ctx)}</li>" for it in items) + f"</{tag}>"
    if name == "description":
        items = [c for c in node.children if c.kind == "env" and c.name == "ditem"]
        return '<dl class="woo-dl">' + "".join(
            f'<dt>{inline(it.meta.get("bullet", ""), ctx)}</dt><dd>{item_content(it, ctx)}</dd>' for it in items) + "</dl>"
    if name == "table":
        aligns = col_aligns(node.meta.get("columns", ""))
        rows = [c for c in node.children if c.kind == "env" and c.name == "row"]
        noheader = node.meta.get("noheader", "") == "true"
        head, body = [], []
        for r_i, r in enumerate(rows):
            is_head = (r.meta.get("head") == "true" or r_i == 0) and not noheader
            tag = "th" if is_head else "td"
            cells = []
            for c_i, cell in enumerate(r.children):
                al = aligns[c_i] if c_i < len(aligns) else "left"
                if cell.kind == "par":
                    content = "" if cell.text.strip() == "~" else inline(cell.text, ctx)
                else:
                    content = render_nodes([cell], ctx)
                cells.append(f'<{tag} style="text-align:{al}">{content}</{tag}>')
            (head if is_head else body).append("<tr>" + "".join(cells) + "</tr>")
        thead = "<thead>" + "".join(head) + "</thead>" if head else ""
        return f"<table>{thead}<tbody>" + "".join(body) + "</tbody></table>"
    if name == "equation":
        return '<div class="arithmatex">\\[' + html.escape(fix_colors(" ".join(node.raw)), quote=False) + '\\]</div>'
    if name in ("align", "gather"):
        env = name + "*"
        return ('<div class="arithmatex">\\begin{' + env + '}' + html.escape(fix_colors(" ".join(node.raw)), quote=False)
                + '\\end{' + env + '}</div>')
    if name == "centered":
        return '<div class="woo-centered">' + render_nodes(node.children, ctx) + "</div>"
    if name == "tikz":
        fn = node.meta.get("filename", "")
        size = FIG_SIZE.get(fn)
        if not size:
            warn(f"obrázek '{fn}' se nepodařilo připravit ({node.src})")
            return f'<p class="woo-missing">[obrázek {html.escape(fn)} chybí]</p>'
        w, h = round(size[0] * PX_PER_PT), round(size[1] * PX_PER_PT)
        full = ' style="width:100%"' if "width" in node.meta.get("include_options", "") else ""
        alt = html.escape("Obrázek: " + (ctx.title or fn), quote=True)
        return (f'<img class="woo-fig" src="{rel_url(ctx, "figures/" + fn + ".svg")}" '
                f'width="{w}" height="{h}" alt="{alt}"{LAZY}{full}>')
    if name == "image":
        fn = " ".join(l.strip() for l in node.raw if l.strip())
        src = ROOT / "figures" / fn
        if src.exists():
            (DOCS / "figures").mkdir(parents=True, exist_ok=True)
            shutil.copy(src, DOCS / "figures" / fn)
        else:
            warn(f"chybí soubor figures/{fn}")
        url = os.path.relpath("figures/" + fn, os.path.dirname(ctx.page) or ".").replace(os.sep, "/")
        alt = html.escape("Obrázek: " + (ctx.title or fn), quote=True)
        return f'<img class="woo-fig woo-img" src="{url}" alt="{alt}"{LAZY}>'
    if name == "pseudocode":
        return render_pseudocode(node.raw)
    if name == "codeblock":
        code = "\n".join(node.raw)
        return '<pre class="woo-code"><code>' + html.escape(code, quote=False).replace("\n\n", "\n&#8203;\n") + "</code></pre>"
    if name == "caption":
        return f'<p class="woo-caption">{item_content(node, ctx)}</p>'
    if name == "raw":
        return ""
    if name in OBJECTS or name in FLOATS or name == "Solution":
        return render_object(node, ctx)
    warn(f"neznámé prostředí .{name}: ({node.src})")
    return render_nodes(node.children, ctx)


def render_object(node, ctx):
    name = node.name
    ident = f' id="{node.meta["label"]}"' if node.meta.get("label") else ""
    old_title = ctx.title
    if name == "Solution":
        body = render_nodes(node.children, ctx)
        ctx.prev_object = name
        if PDF:
            return (f'<div class="admonition success woo-solution"{ident}>'
                    f'<p class="admonition-title">Řešení</p>{body}</div>')
        return f'<details class="success woo-solution"{ident}><summary>Řešení</summary>{body}</details>'
    num = node.meta.get("_number", "")
    if name in FLOATS:
        cap = [c for c in node.children if c.kind == "env" and c.name == "caption"]
        rest = [c for c in node.children if not (c.kind == "env" and c.name == "caption")]
        if cap:
            ctx.title = plain(" ".join(k.text for k in cap[0].children if k.kind == "par"))
        label = f'<span class="woo-fignum">{FLOATS[name]}{" " + num if num else ""}{":" if cap else ""}</span> '
        cap_html = (f'<figcaption>{label}{item_content(cap[0], ctx)}</figcaption>' if cap
                    else (f'<figcaption>{label}</figcaption>' if num else ""))
        if name == "Table":
            inner = cap_html + render_nodes(rest, ctx)
        else:
            inner = '<div class="woo-centered">' + render_nodes(rest, ctx) + "</div>" + cap_html
        ctx.title = old_title
        ctx.prev_object = name
        return f'<figure class="woo-float woo-{name.lower()}"{ident}>{inner}</figure>'
    kind, prefix = OBJECTS[name]
    title = node.meta.get("title", "")
    extra = ""
    if name == "Definition" and title.startswith("Problém"):      # definice rozhodovacího problému (Vstup / Otázka)
        prefix, title, extra = "Problém", title[len("Problém"):].lstrip(" :"), " woo-problem"
    elif name == "Remark" and title.startswith("Redukce"):         # hlavička redukce: co se převádí na co
        kind, extra = "abstract", " woo-redukcebox"
    elif name == "Remark" and title.startswith(("Co si odnést", "Shrnutí")):
        kind, extra = "success", " woo-summary"
    if prefix and num:
        prefix = f"{prefix} {num}"
    if title:
        ctx.title = plain(title)
        t_html = inline(title, ctx)
        if name == "Theorem":
            head = f"{prefix} ({t_html})"
        elif prefix and (title.split()[0].rstrip(":").casefold() == prefix.split()[0].casefold()
                         or (name == "Proof" and "důkaz" in title.casefold())):   # „Náznak důkazu“
            head = t_html                       # „Postup: Postup na papíře“ – název už typem rámečku začíná
        elif prefix:
            head = f"{prefix}: {t_html}"
        else:
            head = t_html
    else:
        head = prefix or DEFAULT_TITLE.get(name, name)
    kids = [c for c in node.children if c.kind in ("par", "env")]
    if name == "Example" and not PDF and len(kids) >= 2:
        # příklad: první blok (zadání) zůstane vidět, zbytek je rozbalovací řešení
        body = (render_nodes(kids[:1], ctx) + '<details class="success woo-solution woo-example-solution">'
                f'<summary>Řešení</summary>{render_nodes(kids[1:], ctx)}</details>')
    else:
        body = render_nodes(node.children, ctx)
    ctx.title = old_title if name != "Exercise" and name != "Example" else ctx.title
    ctx.prev_object = name
    if name == "Proof" and not PDF:                                # důkaz je na webu rozbalovací
        return f'<details class="{kind} woo-proof"{ident}><summary>{head}</summary>{body}</details>'
    return (f'<div class="admonition {kind} woo-{name.lower()}{extra}"{ident}>'
            f'<p class="admonition-title">{head}</p>{body}</div>')


def render_nodes(nodes, ctx):
    out = []
    for n in nodes:
        if n.kind == "par":
            cls = ' class="woo-redukce"' if n.text.startswith(('"Redukce:"', '"Redukce s orákulem:"')) else ""
            out.append(f"<p{cls}>" + inline(n.text, ctx) + "</p>")
        elif n.kind == "env":
            out.append(render_env(n, ctx))
    return "\n".join(out)


def render_page_body(nodes, ctx, base_level):
    """Střídá markdownové nadpisy (pododdíly) a bloky hotového HTML."""
    chunks = []
    buf = []

    def flush():
        if buf:
            h = render_nodes(buf, ctx)
            h = "\n".join(l for l in h.split("\n") if l.strip())
            chunks.append('<div class="woo">\n' + h + "\n</div>")
            buf.clear()

    for n in nodes:
        if n.kind == "part":
            flush()
            ctx.title = plain(n.text)
            num = n.meta.get("_number", "")
            attrs = []
            if n.meta.get("label"):
                attrs.append("#" + n.meta["label"])
            if n.text.startswith(PART_PREFIXES):     # jádro a úlohy podtématu: v oddíle je oddělí linka
                attrs.append(".woo-part")
            if "$" in n.text:      # v postranním obsahu má být čitelný text, ne zdroj vzorce
                toc = (num + " " + (n.meta.get("pdf_string") or plain(n.text))).replace('"', "'")
                attrs.append(f'data-toc-label="{toc}"')
            ident = " { " + " ".join(attrs) + " }" if attrs else ""
            chunks.append("#" * base_level + f" {num} {md_heading_text(n.text)}{ident}")
        else:
            buf.append(n)
    flush()
    return "\n\n".join(chunks)


# ---------------------------------------------------------------- obrázky

def prepare_figures(files):
    """Přeloží všechny !tikz: (s mezipamětí) a udělá z PDF soubory SVG v docs/figures."""
    import fitz
    devnull = open(os.devnull, "w")
    stdout, sys.stdout = sys.stdout, devnull
    try:
        ct.check_tikz(files)
    finally:
        sys.stdout = stdout
        devnull.close()
    figdir = DOCS / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    cache = ROOT / ".build" / "svg"
    cache.mkdir(parents=True, exist_ok=True)
    for f in files:
        for _env, meta, _body, ln in ct.extract(f, ["tikz"]):
            fn = meta.get("filename") or f"{f.stem}-L{ln}"
            pdf = ct.BUILD / "tikz" / (fn + ".pdf")
            if not pdf.exists():
                continue
            svg = cache / (fn + ".svg")
            size_file = cache / (fn + ".size")
            if not svg.exists() or svg.stat().st_mtime < pdf.stat().st_mtime or not size_file.exists():
                doc = fitz.open(pdf)
                page = doc[0]
                svg.write_text(page.get_svg_image(text_as_path=True), encoding="utf-8")
                size_file.write_text(f"{page.rect.width} {page.rect.height}")
                doc.close()
            w, h = (float(x) for x in size_file.read_text().split())
            FIG_SIZE[fn] = (w, h)
            shutil.copy(svg, figdir / (fn + ".svg"))


# ---------------------------------------------------------------- sestavení webu

def load_document():
    files = sorted((ROOT / "src").glob("*.woo"))
    nodes = []
    for f in files:
        nodes.extend(parse_blocks(f.read_text(encoding="utf-8").split("\n"), f.name))
    return files, nodes


def build_structure(nodes):
    chapters = []
    cur_ch = cur_sec = None
    c = s = u = apx = 0
    counters = {}
    for n in nodes:
        if n.kind == "env" and n.name in COUNTERS and n.meta.get("nonumber") != "true" and cur_ch is not None:
            grp = COUNTERS[n.name]
            counters[grp] = counters.get(grp, 0) + 1
            n.meta["_number"] = f"{c}.{counters[grp]}"
        if n.kind == "part" and n.name == "Chapter":
            counters = {}
            m = re.match(r"(\d+)", n.src)
            if m and int(m.group(1)) >= APPENDIX_FROM:
                apx += 1
                c = chr(ord("A") + apx - 1)
            else:
                c = int(c) + 1
            s = u = 0
            cur_ch = {"node": n, "num": str(c), "intro": [], "sections": [], "src": n.src}
            cur_sec = None
            n.meta["_number"] = str(c)
            chapters.append(cur_ch)
        elif n.kind == "part" and n.name == "Section":
            s += 1
            u = 0
            n.meta["_number"] = f"{c}.{s}"
            cur_sec = {"node": n, "num": f"{c}.{s}", "nodes": []}
            cur_ch["sections"].append(cur_sec)
        else:
            if n.kind == "part":
                u += 1
                n.meta["_number"] = f"{c}.{s}.{u}" if cur_sec else f"{c}.{u}"
            if cur_ch is None:
                warn(f"obsah před první kapitolou ({n.src})")
                continue
            (cur_sec["nodes"] if cur_sec else cur_ch["intro"]).append(n)
    return chapters


def slug(label, fallback):
    return label or fallback


def register_labels(chapters):
    def reg_objects(nodes, page):
        for n in nodes:
            if n.kind == "part" and n.meta.get("label"):
                LABELS[n.meta["label"]] = {"page": page, "anchor": n.meta["label"], "number": n.meta["_number"],
                                           "title": n.text}
            elif n.kind == "env" and n.meta.get("label"):
                LABELS[n.meta["label"]] = {"page": page, "anchor": n.meta["label"], "number": n.meta.get("_number", ""),
                                           "title": plain(n.meta.get("title", "")) or n.name}
    for i, ch in enumerate(chapters):
        cn = ch["node"]
        ch["dir"] = slug(cn.meta.get("label"), f"kapitola-{i + 1}")
        ch["page"] = ch["dir"] + "/index.md"
        ch["anchor"] = ch["dir"]
        if cn.meta.get("label"):
            LABELS[cn.meta["label"]] = {"page": ch["page"], "anchor": "", "number": ch["num"], "title": cn.text}
        reg_objects(ch["intro"], ch["page"])
        for j, sec in enumerate(ch["sections"]):
            sn = sec["node"]
            sec["anchor"] = slug(sn.meta.get("label"), f"{ch['dir']}-oddil-{j + 1}")
            sec["page"] = ch["dir"] + "/" + slug(sn.meta.get("label"), f"oddil-{j + 1}") + ".md"
            if sn.meta.get("label"):
                LABELS[sn.meta["label"]] = {"page": sec["page"], "anchor": "", "number": sec["num"], "title": sn.text}
            reg_objects(sec["nodes"], sec["page"])


def nav_title(node, num):
    t = node.meta.get("pdf_string") or plain(node.text)
    return f"{num} {t}"


def group_of(ch):
    m = re.match(r"(\d+)", ch["src"])
    k = int(m.group(1)) if m else 0
    for lo, hi, name in GROUPS:
        if lo <= k <= hi:
            return name
    return "Ostatní"


def chapter_groups(chapters):
    groups = []
    for ch in chapters:
        g = group_of(ch)
        if not groups or groups[-1][0] != g:
            groups.append((g, []))
        groups[-1][1].append(ch)
    return groups


PDF_ONLY = ("pdf.css", "pdf.js", "mathjax-config-pdf.js", "mathjax-chtml")     # soubory jen pro PDF verzi


def copy_assets(skip=()):
    for sub in ("stylesheets", "javascripts"):
        (DOCS / sub).mkdir(parents=True, exist_ok=True)
        for f in (ASSETS / sub).glob("*"):
            if f.name in skip:
                continue
            if f.is_dir():
                shutil.copytree(f, DOCS / sub / f.name)
            else:
                shutil.copy(f, DOCS / sub / f.name)


def write_config(cfg):
    (OUT / "mkdocs.yml").write_text("# GENEROVÁNO skriptem tools/woo2mkdocs.py – needituj ručně\n"
                                    + json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_pdf_doc(chapters):
    """Celá skripta jako jedna stránka (index.md), ze které Chrome vytiskne PDF."""
    import datetime
    ctx = Ctx("index.md")
    d = datetime.date.today()
    parts = ['<div class="woo-titlepage">\n'
             '<p class="woo-tp-subject">NI-ICC · Úvod do výpočetní složitosti · FIT ČVUT</p>\n'
             '<p class="woo-tp-title">Skripta s důrazem na vizualizaci</p>\n'
             '<p class="woo-tp-topics">Turingovy stroje · P a NP · NP-úplnost a redukce · prostorová složitost · '
             'SAT a ILP řešiče</p>\n'
             f'<p class="woo-tp-date">verze z {d.day}. {d.month}. {d.year}</p>\n</div>']
    toc = ['<nav class="woo-toc">', '<p class="woo-toc-title">Obsah</p>']
    for g, chs in chapter_groups(chapters):
        toc.append('<div class="woo-toc-part">')        # část obsahu se nedělí mezi stránky
        if g != "Úvod":
            toc.append(f'<p class="woo-toc-group">{esc(g)}</p>')
        toc.append("<ul>")
        for ch in chs:
            cn = ch["node"]
            toc.append(f'<li><a href="#{ch["anchor"]}"><span class="woo-toc-num">{ch["num"]}</span> '
                       f'{inline(cn.text, ctx)}</a>')
            if ch["sections"]:
                toc.append("<ul>")
                for sec in ch["sections"]:
                    toc.append(f'<li><a href="#{sec["anchor"]}"><span class="woo-toc-num">{sec["num"]}</span> '
                               f'{inline(sec["node"].text, ctx)}</a></li>')
                toc.append("</ul>")
            toc.append("</li>")
        toc.append("</ul></div>")
    toc.append("</nav>")
    parts.append("\n".join(toc))
    for ch in chapters:
        cn = ch["node"]
        ctx.title = plain(cn.text)
        parts.append(f"# {ch['num']} {md_heading_text(cn.text)} {{ #{ch['anchor']} .woo-chapter }}")
        body = render_page_body(ch["intro"], ctx, 2)
        if body:
            parts.append(body)
        for sec in ch["sections"]:
            sn = sec["node"]
            ctx.title = plain(sn.text)
            parts.append(f"## {sec['num']} {md_heading_text(sn.text)} {{ #{sec['anchor']} .woo-section }}")
            body = render_page_body(sec["nodes"], ctx, 3)
            if body:
                parts.append(body)
    (DOCS / "index.md").write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    copy_assets(skip=("tex-svg-full.js", "mathjax-config.js", "woo.js", "pojmy.js"))
    write_config({
        "site_name": SITE_NAME,
        "site_description": SITE_DESC,
        "docs_dir": "docs",
        "site_dir": os.path.relpath(SITE, OUT),
        "use_directory_urls": False,
        "theme": {"name": "material", "language": "cs", "font": False,
                  "palette": {"scheme": "default", "primary": "custom", "accent": "custom"}},
        "markdown_extensions": ["attr_list", {"toc": {"permalink": False, "toc_depth": 3}},
                                {"pymdownx.arithmatex": {"generic": True}}],
        "extra_css": ["stylesheets/extra.css", "stylesheets/pdf.css"],
        "extra_javascript": ["javascripts/mathjax-config-pdf.js", "javascripts/mathjax-chtml/tex-chtml-full.js",
                             "javascripts/pdf.js"],
        "plugins": [],
        "nav": [{"Skripta": "index.md"}],
    })


def write_site(chapters):
    if ONLY:        # náhled: jen vybrané kapitoly (štítky jsou zaregistrované ze všech, odkazy jinam nikam nevedou)
        chapters = [ch for ch in chapters if ch["src"].startswith(tuple(ONLY))]
    for ch in chapters:
        cn = ch["node"]
        ctx = Ctx(ch["page"])
        ctx.title = plain(cn.text)
        parts = [f"# {ch['num']} {md_heading_text(cn.text)}"]
        body = render_page_body(ch["intro"], ctx, 2)
        if body:
            parts.append(body)
        if ch["sections"]:
            lst = "\n".join(f"- [{sec['num']} {md_heading_text(sec['node'].text)}]({os.path.basename(sec['page'])})"
                            for sec in ch["sections"])
            parts.append("## Oddíly kapitoly\n\n" + lst)
        p = DOCS / ch["page"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
        for sec in ch["sections"]:
            sn = sec["node"]
            ctx = Ctx(sec["page"])
            ctx.title = plain(sn.text)
            parts = [f"# {sec['num']} {md_heading_text(sn.text)}"]
            body = render_page_body(sec["nodes"], ctx, 2)
            if body:
                parts.append(body)
            (DOCS / sec["page"]).write_text("\n\n".join(parts) + "\n", encoding="utf-8")

    # úvodní stránka
    groups = chapter_groups(chapters)
    home = [f"# {SITE_NAME}",
            "Skripta k předmětu NI-ICC (Úvod do výpočetní složitosti, FIT ČVUT, ZS 2026/2027) podle přednášek, "
            "proseminářů a cvičení: Turingovy stroje a vyčíslitelnost, třídy P, NP a EXP, NP-úplnost a katalog redukcí, "
            "prostorová složitost a PSPACE, SAT a ILP řešiče.",
            "Kapitoly nejdou po týdnech, ale podle látky: od výpočetního modelu přes třídy složitosti a NP-úplné "
            "problémy k prostoru a k řešičům. Látka proseminářů je zapracovaná v textu, úlohy ze cvičení jsou "
            "u kapitoly, ke které patří. Co je na zápočtovém testu, typové úlohy a vyřešený ukázkový test najdeš "
            "v přílohách na konci (záložka „Test a přehledy“), stejně jako graf všech redukcí.",
            "Každá redukce začíná rámečkem, který říká, co se převádí na co. Řešení úloh jsou sbalená – nejdřív zkus "
            "úlohu vyřešit sám, pak si řešení rozklikni (tlačítko nahoře na stránce rozbalí všechna najednou). "
            "Hledat se dá v celém textu (lupa nahoře, klávesa `/`)."]
    for g, chs in groups:
        home.append(f"## {g}")
        home.append("\n".join(f"- [{ch['num']} {md_heading_text(ch['node'].text)}]({ch['page']})" for ch in chs))
    (DOCS / "index.md").write_text("\n\n".join(home) + "\n", encoding="utf-8")

    # navigace
    nav = [{"Úvod": "index.md"}]
    for g, chs in groups:
        entries = []
        for ch in chs:
            pages = [ch["page"]] + [{nav_title(sec["node"], sec["num"]): sec["page"]} for sec in ch["sections"]]
            entries.append({nav_title(ch["node"], ch["num"]): pages})
        nav.append({g: entries})

    copy_assets(skip=PDF_ONLY)
    mathjax = "javascripts/tex-svg-full.js" if (DOCS / "javascripts" / "tex-svg-full.js").exists() \
        else "https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-svg-full.js"
    cfg = {
        "site_name": SITE_NAME,
        "site_description": SITE_DESC,
        "docs_dir": "docs",
        "site_dir": os.path.relpath(SITE, OUT),
        "use_directory_urls": False,
        "theme": {
            "name": "material",
            "language": "cs",
            "font": False,
            "features": ["navigation.tabs", "navigation.indexes", "navigation.footer", "navigation.top",
                         "toc.follow", "search.highlight", "search.suggest"],
            # výchozí je vždy světlý režim (ne podle systému); přepnutí platí, dokud ho čtenář nevrátí zpět
            # (přenos volby mezi stránkami: tools/mkdocs/overrides/main.html a javascripts/woo.js)
            "custom_dir": os.path.relpath(ASSETS / "overrides", OUT),
            "palette": [
                {"scheme": "default", "primary": "custom", "accent": "custom",
                 "toggle": {"icon": "material/weather-night", "name": "Přepnout na tmavý režim"}},
                {"scheme": "slate", "primary": "custom", "accent": "custom",
                 "toggle": {"icon": "material/weather-sunny", "name": "Přepnout na světlý režim"}},
            ],
        },
        "markdown_extensions": ["attr_list", {"toc": {"permalink": True, "toc_depth": 3}},
                                {"pymdownx.arithmatex": {"generic": True}}],
        "extra_css": ["stylesheets/extra.css"],
        "extra_javascript": ["javascripts/mathjax-config.js", mathjax, "javascripts/woo.js"],
        "plugins": ["search", "offline"],
        "nav": nav,
    }
    write_config(cfg)


def main():
    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir(parents=True)
    load_colors()
    files, nodes = load_document()
    prepare_figures([f for f in files if f.name.startswith(tuple(ONLY))] if ONLY else files)
    chapters = build_structure(nodes)
    register_labels(chapters)
    if PDF:
        write_pdf_doc(chapters)
        print(f"kapitol {len(chapters)}, oddílů {sum(len(c['sections']) for c in chapters)}, "
              f"obrázků {len(FIG_SIZE)}, štítků {len(LABELS)} (jedna stránka pro PDF)")
    else:
        write_site(chapters)
        n_pages = len(chapters) + sum(len(c["sections"]) for c in chapters) + 1
        print(f"kapitol {len(chapters)}, stránek {n_pages}, obrázků {len(FIG_SIZE)}, štítků {len(LABELS)}")
    for w in sorted(set(warnings)):
        print("[W]", w)
    print(f"hotovo: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
