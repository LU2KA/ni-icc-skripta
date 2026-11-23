#!/usr/bin/env python3
"""Strukturální kontrola WooWoo souborů (dialekt FIT Math) podle PRAVIDLA.md.

Nenahrazuje skutečný parser (wuff / woo); hlídá chyby, které při převodu z LaTeXu vznikají nejčastěji.
Použití:  python3 tools/check_woo.py [soubor.woo ...]     (bez argumentů: všechny src/*.woo)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = {"Chapter", "Section", "Subsection"}
WOBJECTS = {"Algorithm", "Concept", "Corollary", "Definition", "Example", "Exercise", "Figure", "Lemma",
            "Observation", "Proposition", "Procedure", "Question", "Remark", "Proof", "Solution", "Table",
            "Theorem", "Video", "Warning"}
FRAGILE = {"tikz", "pseudocode", "codeblock", "dot", "raw"}
MATH_ENVS = {"equation", "align", "gather"}
ENVS = {"enumerate", "itemize", "item", "description", "ditem", "caption", "cell", "centered", "image", "quote",
        "table", "row", "tabular", "paragraph"} | MATH_ENVS
COMMON = {"skip", "only"}
META = {
    "part": {"label", "short_title", "pdf_string", "plain_title", "index"},
    "wobject": {"title", "english", "label", "index", "nonumber", "star", "solution", "show", "options",
                "glue", "vertical", "columns"},
    "tikz": {"filename", "options", "include_options", "alt", "invert"},
    "table": {"columns", "arraystretch", "noheader", "hlines"},
    "row": {"head"},
    "item": {"bullet"},
    "ditem": {"bullet"},
    "enumerate": {"type"},
    "image": {"alt", "invert", "options", "extension"},
    "pseudocode": {"linenumber"},
    "codeblock": {"language"},
    "equation": {"label"}, "align": {"label"}, "gather": {"label"},
    "quote": {"author", "link"},
}
LABEL_RE = re.compile(r"^[a-z0-9-]+$")
HEAD_PART = re.compile(r"^\.(Chapter|Section|Subsection)\s+(.+)$")
HEAD_ANY = re.compile(r"^( *)([.!])([A-Za-z][A-Za-z_]*):\s*$")
META_LINE = re.compile(r"^( *)([A-Za-z_][A-Za-z_0-9]*):(?:\s+(.*))?$")
# příkazy, které MathJax nezná (makra skript z tools/tikz/macros.tex zná, viz mathjax-config.js)
UNDEF_MACROS = re.compile(r"\\(ref|cref|Cref|pageref|uv|redukce|redukceor|mbox|ensuremath|hyperlink|hyperref|hypertarget|tmtape|tmsym|textsc|faIcon|footnote|label)(?![A-Za-z])")
ALGPSEUDO = re.compile(r"\\(State|If|ElsIf|Else|EndIf|For|ForAll|EndFor|While|EndWhile|Return|Require|Ensure|Comment|Function|EndFunction|Call)(?![A-Za-z])")
FONT_PRELUDE = r"\renewcommand{\normalsize}{\fontsize{10}{12}\selectfont}"


class Checker:
    def __init__(self):
        self.problems = []          # (file, line, severity, message)
        self.labels = {}            # label -> (file, line, kind)
        self.refs = []              # (file, line, label, kind)
        self.tikz_names = {}
        self.stats = {}

    def add(self, f, n, sev, msg):
        self.problems.append((f, n, sev, msg))

    # ------------------------------------------------------------------
    def check_file(self, path):
        name = path.name
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        st = self.stats.setdefault(name, {"parts": 0, "wobjects": 0, "tikz": 0, "tables": 0, "lines": len(lines)})
        if "\t" in text:
            self.add(name, 1, "E", "soubor obsahuje tabulátor")
        self._check_block_breaks(name, lines)

        # stack of open headers: (indent, kind, name, line)
        stack = []
        i = 0
        blank_run = 2  # start of file counts as separated
        fragile_indent = None      # indent of the open fragile/math env header
        fragile_name = None
        tikz_body = []
        tikz_line = 0
        table_ctx = []             # stack of dicts for .table: {indent, cols, line}
        row_ctx = None             # {indent, cells, line, in_cell}

        def close_tikz():
            nonlocal tikz_body
            if fragile_name == "tikz":
                body = [b for b in tikz_body if b.strip()]
                if not body:
                    self.add(name, tikz_line, "E", "!tikz: bez těla")
                else:
                    joined = "\n".join(body)
                    forest = body[0].strip().startswith("\\begin{forest}")
                    if "\\begin{tikzpicture}" in joined or "\\end{tikzpicture}" in joined:
                        self.add(name, tikz_line, "E", "!tikz: tělo obsahuje \\begin/\\end{tikzpicture} (dodá je překlad; volby patří do meta options)")
                    if re.search(r"\\(ref|pageref|eqref|cref|Cref)\{", joined):
                        self.add(name, tikz_line, "E", "!tikz: \\ref uvnitř obrázku se nevyhodnotí (obrázek se kompiluje samostatně)")
                    if joined.count("\\begin{scope}") != joined.count("\\end{scope}"):
                        self.add(name, tikz_line, "E", "!tikz: nesouhlasí počet \\begin{scope} a \\end{scope}")
                    if forest and not body[-1].strip().endswith("\\end{forest}"):
                        self.add(name, tikz_line, "E", "!tikz: tělo začínající \\begin{forest} musí končit \\end{forest}")
            tikz_body = []

        n = len(lines)
        while i < n:
            raw = lines[i]
            ln = i + 1
            if raw.strip() == "":
                blank_run += 1
                if fragile_indent is not None and fragile_name == "tikz":
                    tikz_body.append("")
                i += 1
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            stripped = raw.strip()

            # ---- inside fragile / math body? -------------------------------------
            if fragile_indent is not None:
                if indent > fragile_indent:
                    if fragile_name == "tikz":
                        if tikz_body and tikz_body[-1] == "" and any(b.strip() for b in tikz_body):
                            self.add(name, ln, "E", "!tikz: prázdný řádek uvnitř těla")
                        tikz_body.append(raw)
                    elif fragile_name == "pseudocode":
                        m = ALGPSEUDO.search(raw)
                        if m:
                            self.add(name, ln, "E", f"!pseudocode: příkaz \\{m.group(1)} je z algpseudocode, šablona chce velká písmena")
                    elif fragile_name in MATH_ENVS:
                        m = UNDEF_MACROS.search(raw)
                        if m:
                            self.add(name, ln, "E", f"nedefinované makro \\{m.group(1)} v matematice")
                        if "\\begin{" + fragile_name in raw or "\\[" in raw or "$$" in raw:
                            self.add(name, ln, "E", f".{fragile_name}: tělo má být jen obsah rovnice")
                    blank_run = 0
                    i += 1
                    continue
                close_tikz()
                fragile_indent = None
                fragile_name = None

            # ---- pop finished contexts ------------------------------------------
            while stack and indent <= stack[-1][0]:
                stack.pop()
            while table_ctx and indent <= table_ctx[-1]["indent"]:
                table_ctx.pop()
            if row_ctx is not None and indent <= row_ctx["indent"]:
                self._close_row(name, row_ctx, table_ctx_snapshot=row_ctx["table"])
                row_ctx = None

            if indent % 2:
                self.add(name, ln, "E", f"liché odsazení ({indent} mezer)")

            # ---- .include ---------------------------------------------------------
            if stripped.startswith(".include "):
                target = path.parent / stripped.split(None, 1)[1]
                if not target.exists():
                    self.add(name, ln, "E", f".include: soubor {target.name} neexistuje")
                blank_run = 0
                i += 1
                continue

            # ---- document part ---------------------------------------------------
            mp = HEAD_PART.match(raw)
            if mp:
                st["parts"] += 1
                if blank_run < 2:
                    self.add(name, ln, "E", "před částí dokumentu musí být dva prázdné řádky")
                meta, j = self._read_meta(name, lines, i + 1, 2, "part")
                if "label" not in meta:
                    self.add(name, ln, "E", f".{mp.group(1)} bez label")
                else:
                    self._def_label(name, ln, meta["label"], mp.group(1))
                self._check_text(name, ln, mp.group(2))
                # two blank lines after the meta block
                k = j
                while k < n and lines[k].strip() == "":
                    k += 1
                if k < n and k - j < 2:
                    self.add(name, j + 1, "E", "za hlavičkou části dokumentu musí být dva prázdné řádky")
                stack.clear()
                blank_run = 0
                i = j
                continue

            if re.match(r"^\.(Chapter|Section|Subsection)\b", stripped):
                self.add(name, ln, "E", "část dokumentu musí být na úrovni 0 a mít nadpis na témže řádku")

            # ---- object / environment header ------------------------------------
            mh = HEAD_ANY.match(raw)
            if mh:
                sigil, ename = mh.group(2), mh.group(3)
                is_w = ename[0].isupper()
                if is_w:
                    st["wobjects"] += 1
                    if ename not in WOBJECTS:
                        self.add(name, ln, "E", f"neznámý objekt .{ename}:")
                    if indent != 0:
                        self.add(name, ln, "E", f"objekt .{ename}: není na nejvyšší úrovni (objekty se nevnořují)")
                    if sigil != ".":
                        self.add(name, ln, "E", f"objekt {sigil}{ename}: má začínat tečkou")
                    if blank_run < 2:
                        self.add(name, ln, "E", f"před objektem .{ename}: musí být dva prázdné řádky")
                    kind = "wobject"
                else:
                    if ename not in ENVS and ename not in FRAGILE:
                        self.add(name, ln, "E", f"neznámé prostředí {sigil}{ename}:")
                    if ename in FRAGILE and sigil != "!":
                        self.add(name, ln, "E", f"prostředí {ename} je křehké, piš !{ename}:")
                    if ename not in FRAGILE and sigil == "!":
                        self.add(name, ln, "E", f"prostředí {ename} není křehké, piš .{ename}:")
                    if blank_run < 1:
                        self.add(name, ln, "E", f"před prostředím {sigil}{ename}: musí být prázdný řádek")
                    expected = (stack[-1][0] + 2) if stack else 0
                    if indent != expected:
                        self.add(name, ln, "E", f"prostředí {sigil}{ename}: má odsazení {indent}, čekám {expected}")
                    kind = ename
                meta, j = self._read_meta(name, lines, i + 1, indent + 2, kind if not is_w else "wobject")
                if j < n and lines[j].strip() != "":
                    self.add(name, j + 1, "E", "za hlavičkou / meta-blokem musí být prázdný řádek")
                if "label" in meta:
                    self._def_label(name, ln, meta["label"], ename)
                for key in ("title", "bullet", "solution"):
                    if key in meta and meta[key]:
                        self._check_text(name, ln, meta[key])
                if is_w and ename in ("Figure", "Table"):
                    pass
                if ename == "tikz":
                    st["tikz"] += 1
                    fn = meta.get("filename")
                    if not fn:
                        self.add(name, ln, "E", "!tikz: bez filename")
                    else:
                        if not re.match(r"^[A-Za-z0-9_-]+$", fn):
                            self.add(name, ln, "E", f"!tikz: filename '{fn}' obsahuje nepovolené znaky")
                        if fn in self.tikz_names:
                            self.add(name, ln, "E", f"!tikz: filename '{fn}' už použit v {self.tikz_names[fn]}")
                        self.tikz_names[fn] = f"{name}:{ln}"
                    tikz_line = ln
                if ename == "table":
                    st["tables"] += 1
                    cols = meta.get("columns")
                    if not cols:
                        self.add(name, ln, "E", ".table: bez columns")
                    table_ctx.append({"indent": indent, "cols": self._count_cols(cols or ""), "line": ln})
                if ename == "row":
                    if not table_ctx:
                        self.add(name, ln, "E", ".row: mimo .table:")
                    row_ctx = {"indent": indent, "cells": 0, "line": ln, "prev_blank": True,
                               "table": table_ctx[-1] if table_ctx else None}
                if ename == "ditem" and "bullet" not in meta:
                    self.add(name, ln, "E", ".ditem: bez bullet")
                if ename in FRAGILE or ename in MATH_ENVS:
                    fragile_indent = indent
                    fragile_name = ename
                else:
                    stack.append((indent, kind, ename, ln))
                blank_run = 0
                i = j
                continue

            if re.match(r"^[.!][A-Za-z]+:", stripped) and not re.match(r"^\.(reference|eqref|cite|emphasize|notion|code|quoted|small|underline|footnote|todo):\S", stripped):
                self.add(name, ln, "E", "řádek vypadá jako hlavička prostředí, ale není platný (za dvojtečkou nesmí nic být)")

            # ---- plain text line -------------------------------------------------
            expected = (stack[-1][0] + 2) if stack else 0
            if indent > expected:
                self.add(name, ln, "E", f"text odsazený o {indent}, čekám {expected} (odsazený blok je implicitní rovnice)")
            elif indent < expected:
                self.add(name, ln, "E", f"text odsazený o {indent}, čekám {expected}")
            if stripped.startswith("* "):
                self.add(name, ln, "E", "řádek začíná '* '")
            if stripped[0] in ".!" and not re.match(r"^\.(reference|eqref|cite|emphasize|notion|code|quoted|small|underline|footnote|todo):\S", stripped):
                self.add(name, ln, "E", "řádek textu začíná znakem '.' nebo '!'")
            if row_ctx is not None and indent > row_ctx["indent"]:
                if blank_run >= 1 or row_ctx["cells"] == 0:
                    row_ctx["cells"] += 1
                else:
                    self.add(name, ln, "E", ".row: buňka má víc řádků (každá buňka je jeden řádek)")
                if blank_run >= 2:
                    self.add(name, ln, "E", ".row: dva prázdné řádky uvnitř řádku tabulky")
            self._check_text(name, ln, stripped)
            blank_run = 0
            i += 1

        if fragile_indent is not None:
            close_tikz()
        if row_ctx is not None:
            self._close_row(name, row_ctx, row_ctx["table"])
        if not text.endswith("\n"):
            self.add(name, n, "W", "soubor nekončí novým řádkem")

    # ------------------------------------------------------------------
    def _check_block_breaks(self, name, lines):
        """Dva prázdné řádky (= nový blok) smí být jen na nejvyšší úrovni a přímo v těle objektu.

        Uvnitř vnějšího prostředí (.item:, .itemize:, .row:, ...) je to syntaktická chyba (hlásí ji i wuff);
        odstavce se tam oddělují jedním prázdným řádkem.
        """
        top_is_object = False
        blank = 0
        fragile = None
        for ln, line in enumerate(lines, 1):
            if not line.strip():
                blank += 1
                continue
            indent = len(line) - len(line.lstrip())
            if fragile is not None and indent <= fragile:
                fragile = None
            if fragile is None:
                if blank >= 2 and (indent >= 4 or (indent == 2 and not top_is_object)):
                    self.add(name, ln, "E", "dva prázdné řádky uvnitř vnějšího prostředí (nový blok tu být nesmí; "
                                            "odstavce odděl jedním prázdným řádkem)")
                if indent == 0:
                    top_is_object = bool(re.match(r"^\.[A-Z][A-Za-z]*:\s*$", line))
                if re.match(r"^\s*!(tikz|pseudocode|codeblock|raw):\s*$", line):
                    fragile = indent
            blank = 0

    def _close_row(self, name, row, table_ctx_snapshot):
        t = table_ctx_snapshot
        if t and t["cols"] and row["cells"] != t["cols"]:
            self.add(name, row["line"], "E", f".row: {row['cells']} buněk, tabulka (ř. {t['line']}) má {t['cols']} sloupců")

    @staticmethod
    def _count_cols(spec):
        s = re.sub(r"@\{[^{}]*\}", "", spec)
        s = re.sub(r"[><]\{(?:[^{}]|\{[^{}]*\})*\}", "", s)
        s = re.sub(r"([pmb])\{[^{}]*\}", r"\1", s)
        return len(re.findall(r"[lcrpmbX]", s))

    def _read_meta(self, name, lines, start, indent, kind):
        meta = {}
        j = start
        allowed = META.get(kind, set()) | COMMON
        while j < len(lines):
            raw = lines[j]
            if raw.strip() == "":
                break
            m = META_LINE.match(raw)
            if not m or len(m.group(1)) != indent:
                self.add(name, j + 1, "E", "řádek hned za hlavičkou není platný řádek meta-bloku (chybí prázdný řádek?)")
                break
            key, val = m.group(2), (m.group(3) or "").strip()
            if key not in allowed:
                self.add(name, j + 1, "E", f"meta klíč '{key}' není pro '{kind}' povolen")
            val = self._yaml_scalar(name, j + 1, key, val)
            meta[key] = val
            j += 1
        return meta, j

    def _yaml_scalar(self, name, ln, key, val):
        if val == "":
            self.add(name, ln, "E", f"meta '{key}' bez hodnoty")
            return val
        if val[0] == "'":
            if len(val) < 2 or val[-1] != "'" or val[1:-1].replace("''", "").count("'"):
                self.add(name, ln, "E", f"meta '{key}': špatně uzavřené nebo nezdvojené apostrofy")
            return val[1:-1].replace("''", "'")
        if val[0] == '"':
            if len(val) < 2 or val[-1] != '"':
                self.add(name, ln, "E", f"meta '{key}': neuzavřené uvozovky")
            return val[1:-1]
        if key in ("title", "bullet", "solution", "columns", "include_options", "options"):
            self.add(name, ln, "E", f"meta '{key}' piš v jednoduchých uvozovkách")
        elif re.search(r": |#| \[|^[\[{*&!%@`|>]", val):
            self.add(name, ln, "E", f"meta '{key}': hodnota potřebuje uvozovky")
        return val

    def _def_label(self, name, ln, label, kind):
        if not LABEL_RE.match(label):
            self.add(name, ln, "E", f"label '{label}' obsahuje nepovolené znaky (jen a-z, 0-9, -)")
        if label in self.labels:
            f, l, _ = self.labels[label]
            self.add(name, ln, "E", f"label '{label}' už definován v {f}:{l}")
        else:
            self.labels[label] = (name, ln, kind)

    def _check_text(self, name, ln, s):
        # math segments
        s_esc = s.replace("\\$", "\x00")
        if s_esc.count("$") % 2:
            self.add(name, ln, "E", "lichý počet znaků $ na řádku")
        math = re.findall(r"\$([^$]*)\$", s_esc)
        for mth in math:
            m = UNDEF_MACROS.search(mth)
            if m:
                self.add(name, ln, "E", f"nedefinované makro \\{m.group(1)} v matematice")
            if mth.strip() == "":
                self.add(name, ln, "E", "prázdná matematika $$ (vysazenou rovnici piš jako .equation:)")
        text = re.sub(r"\$[^$]*\$", "\u00a4", s_esc)
        for m in re.finditer(r"\\(--|---|~|[A-Za-z]+|.)", text):
            tok = m.group(0)
            if tok in ("\\--", "\\---", "\\~"):
                continue
            self.add(name, ln, "E", f"LaTeX v textu: {tok}")
            break
        if re.search(r"[{}]", text) and re.search(r"\\[A-Za-z]", text) is None and re.search(r"\{[^{}]*\}", text):
            self.add(name, ln, "W", "složené závorky v textu (zbytek LaTeXu?)")
        q = text.count('"')
        closers = len(re.findall(r'"(?:\.[a-z]+|#[A-Za-z0-9_-]+|@[A-Za-z0-9_]+)', text))
        if q % 2 or closers * 2 != q:
            self.add(name, ln, "E", f'znak " mimo vnitřní prostředí ({q} uvozovek, {closers} uzávěrů)')
        for m in re.finditer(r'"\.([a-z]+)', text):
            if m.group(1) not in ("emphasize", "notion", "code", "quoted", "small", "underline", "footnote", "todo", "reference", "eqref", "cite", "math"):
                self.add(name, ln, "E", f"neznámé vnitřní prostředí .{m.group(1)}")
        for m in re.finditer(r"(?<![\"\w])\.(reference|eqref):([A-Za-z0-9_:.-]*)", text):
            lab = m.group(2).rstrip(".:-")
            if not lab:
                self.add(name, ln, "E", f".{m.group(1)}: bez štítku")
            else:
                self.refs.append((name, ln, lab, m.group(1)))
        for m in re.finditer(r'"#([A-Za-z0-9_-]+)', text):
            self.refs.append((name, ln, m.group(1).rstrip("-"), "hash"))

    # ------------------------------------------------------------------
    def finish(self):
        for f, ln, lab, kind in self.refs:
            if lab not in self.labels:
                self.add(f, ln, "E" if self.complete else "R", f"odkaz na neexistující label '{lab}'")
            else:
                tkind = self.labels[lab][2]
                if kind == "hash" and tkind in PARTS and not lab.startswith("red-"):     # kotvy redukcí smí být i na pododdíle
                    self.add(f, ln, "E", f"\"…\"#{lab} míří na {tkind}; na části dokumentu odkazuj přes .reference:{lab}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    quiet_refs = "--no-refs" in sys.argv
    files = [Path(a) for a in args] if args else sorted((ROOT / "src").glob("*.woo"))
    c = Checker()
    c.complete = not args
    # labels from all files are needed for cross-file references
    all_files = sorted((ROOT / "src").glob("*.woo"))
    selected = {f.resolve() for f in files}
    for f in all_files:
        c.check_file(f)
    for f in files:
        if f.resolve() not in {a.resolve() for a in all_files}:
            c.check_file(f)
    c.finish()
    names = {f.name for f in files}
    shown = [p for p in c.problems if p[0] in names and not (quiet_refs and "neexistující label" in p[3])]
    shown.sort(key=lambda p: (p[0], p[1]))
    for f, ln, sev, msg in shown:
        print(f"{f}:{ln}: [{sev}] {msg}")
    errs = sum(1 for p in shown if p[2] == "E")
    unresolved = sum(1 for p in shown if p[2] == "R")
    print("-" * 60)
    for nme in sorted(names):
        s = c.stats.get(nme)
        if s:
            print(f"{nme}: {s['lines']} řádků, částí {s['parts']}, objektů {s['wobjects']}, tikz {s['tikz']}, tabulek {s['tables']}")
    print(f"chyb: {errs}, varování: {sum(1 for p in shown if p[2] == 'W')}, odkazů do zatím neexistujících souborů: {unresolved}")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
