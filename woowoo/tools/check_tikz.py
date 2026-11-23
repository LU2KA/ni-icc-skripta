#!/usr/bin/env python3
"""Zkompiluje každý !tikz: samostatně (preambule: tools/tikz/macros.tex + styles.tex + local-NN.tex) a všechnu matematiku.

Použití:
  python3 tools/check_tikz.py [soubor.woo ...]        obrázky TikZ (bez argumentů všechny src/*.woo)
  python3 tools/check_tikz.py --math [soubor.woo ...] řádková i vysazená matematika (hledá nedefinovaná makra)
Výstupy kompilace jdou do .build/ (lze smazat).
"""
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / ".build"
TIKZ_DIR = ROOT / "tools" / "tikz"
LIBS = ["arrows.meta", "positioning", "automata", "calc", "fit", "backgrounds", "shapes.geometric", "shapes.misc",
        "shapes.multipart", "decorations.pathreplacing", "decorations.markings", "decorations.pathmorphing",
        "patterns", "matrix", "quotes", "trees"]


def _read(name):
    f = TIKZ_DIR / name
    return f.read_text(encoding="utf-8") if f.exists() else ""


# barvy a matematická makra skript (tools/tikz/macros.tex) – stejná makra zná i MathJax (mathjax-config.js)
MACROS = _read("macros.tex")


def local_macros(stem):
    """Makra a styly jedné kapitoly: tools/tikz/local-NN.tex (NN = číslo na začátku jména .woo souboru)."""
    m = re.match(r"(\d+)", stem)
    return _read(f"local-{m.group(1)}.tex") if m else ""


PREAMBLE = r"""\documentclass[11pt]{standalone}
\usepackage{polyglossia}
\setdefaultlanguage{czech}
\usepackage{fontspec}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{mathtools}
\usepackage{xcolor}
\usepackage{tikz}
\usepackage{ifthen}
\usepackage{forest}
\usepackage{pgfplots}
\usepackage{fontawesome5}
\usetikzlibrary{@@LIBS@@}
\pgfplotsset{compat=1.18}
""" + MACROS + _read("styles.tex") + r"""
@@LOCAL@@
\begin{document}
@@BODY@@
\end{document}
"""


def tikz_source(stem, meta, body):
    """Celý zdroják jednoho obrázku. Tělo začínající \begin{forest} se do tikzpicture nebalí."""
    code = "\n".join(body).strip()
    if not code.startswith("\\begin{forest}"):
        code = "\\begin{tikzpicture}[%s]\n%s\n\\end{tikzpicture}" % (meta.get("options", ""), code)
    return (PREAMBLE.replace("@@LIBS@@", ",".join(LIBS)).replace("@@LOCAL@@", local_macros(stem))
            .replace("@@BODY@@", code))


def extract(path, names):
    """Yield (env, meta, body_lines, line_no) for the given fragile/math environments."""
    lines = path.read_text(encoding="utf-8").split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r"^( *)[.!](" + "|".join(names) + r"):\s*$", lines[i])
        if not m:
            i += 1
            continue
        ind = len(m.group(1))
        meta = {}
        j = i + 1
        while j < len(lines) and lines[j].strip():
            mm = re.match(r"^ *([a-z_]+):\s*(.*)$", lines[j])
            if mm:
                v = mm.group(2).strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                    v = v[1:-1].replace("''", "'")
                meta[mm.group(1)] = v
            j += 1
        body = []
        k = j
        while k < len(lines):
            if lines[k].strip() == "":
                body.append("")
                k += 1
                continue
            if len(lines[k]) - len(lines[k].lstrip(" ")) <= ind:
                break
            body.append(lines[k][ind + 2:])
            k += 1
        while body and body[-1] == "":
            body.pop()
        while body and body[0] == "":
            body.pop(0)
        yield m.group(2), meta, body, i + 1
        i = k


def run_lualatex(texfile):
    try:
        r = subprocess.run(["lualatex", "-halt-on-error", "-interaction", "nonstopmode", texfile.name],
                           cwd=texfile.parent, capture_output=True, text=True, timeout=180, errors="replace")
        return r.returncode
    except subprocess.TimeoutExpired:
        return -1


def log_error(log):
    if not log.exists():
        return "žádný log"
    out = []
    lines = log.read_text(errors="replace").split("\n")
    for n, l in enumerate(lines):
        if l.startswith("!"):
            out.append(" | ".join(x.strip() for x in lines[n:n + 6] if x.strip())[:300])
            break
    return out[0] if out else "neznámá chyba"


def pdf_size(pdf):
    try:
        data = pdf.read_bytes()
        m = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", data)
        if m:
            return float(m.group(3)) - float(m.group(1)), float(m.group(4)) - float(m.group(2))
    except OSError:
        pass
    return None


def check_tikz(files):
    d = BUILD / "tikz"
    d.mkdir(parents=True, exist_ok=True)
    jobs = []
    for f in files:
        for env, meta, body, ln in extract(f, ["tikz"]):
            fn = meta.get("filename") or f"{f.stem}-L{ln}"
            src = tikz_source(f.stem, meta, body)
            tex = d / (fn + ".tex")
            pdf = d / (fn + ".pdf")
            if tex.exists() and tex.read_text(encoding="utf-8") == src and pdf.exists():
                jobs.append((f.name, ln, fn, tex, None, meta))
                continue
            tex.write_text(src, encoding="utf-8")
            if pdf.exists():
                pdf.unlink()
            jobs.append((f.name, ln, fn, tex, True, meta))
    todo = [j for j in jobs if j[4]]
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(lambda j: run_lualatex(j[3]), todo))
    bad = wide = 0
    for fname, ln, fn, tex, _, meta in jobs:
        pdf = tex.with_suffix(".pdf")
        if not pdf.exists():
            bad += 1
            print(f"{fname}:{ln}: [E] tikz '{fn}' se nezkompiloval: {log_error(tex.with_suffix('.log'))}")
            continue
        size = pdf_size(pdf)
        if size:
            w_cm = size[0] / 72.27 * 2.54
            h_cm = size[1] / 72.27 * 2.54
            if w_cm > 17.0 and 'width' not in meta.get('include_options', ''):
                wide += 1
                print(f"{fname}:{ln}: [W] tikz '{fn}' je široký {w_cm:.1f} cm (sazba má ~16,4 cm): přidej include_options: 'width=\\linewidth'")
            if h_cm > 22:
                print(f"{fname}:{ln}: [W] tikz '{fn}' je vysoký {h_cm:.1f} cm")
    print(f"tikz: {len(jobs)} obrázků, chyb {bad}, příliš širokých {wide} (PDF v {d})")
    return bad


MATH_DOC = r"""\documentclass[12pt]{article}
\usepackage{polyglossia}
\setdefaultlanguage{czech}
\usepackage{fontspec}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{mathtools}
\usepackage{mathrsfs}
\usepackage{xcolor}
""" + MACROS + r"""
\begin{document}
\errorcontextlines=0
@@BODY@@
\end{document}
"""


def check_math(files):
    d = BUILD / "math"
    d.mkdir(parents=True, exist_ok=True)
    bad = total = 0
    for f in files:
        items = []  # (line, latex)
        text_lines = f.read_text(encoding="utf-8").split("\n")
        fragile_spans = set()
        for env, meta, body, ln in extract(f, ["tikz", "pseudocode", "codeblock", "raw", "equation", "align", "gather"]):
            for k in range(ln, ln + len(body) + len(meta) + 3):
                fragile_spans.add(k)
            content = "\n".join(b for b in body if b.strip())
            if env == "equation":
                items.append((ln, "\\[" + content + "\\]"))
            elif env == "align":
                items.append((ln, "\\begin{align*}" + content + "\\end{align*}"))
            elif env == "gather":
                items.append((ln, "\\begin{gather*}" + content + "\\end{gather*}"))
        for n, l in enumerate(text_lines, 1):
            if n in fragile_spans:
                continue
            for m in re.finditer(r"\$([^$]+)\$", l.replace("\\$", "  ")):
                items.append((n, "$" + m.group(1) + "$"))
        if not items:
            continue
        total += len(items)
        body = "\n\n".join(f"%% L{ln}\n\\typeout{{WOOLINE {ln}}}{tex}" for ln, tex in items)
        tex = d / (f.stem + ".tex")
        tex.write_text(MATH_DOC.replace("@@BODY@@", body), encoding="utf-8")
        subprocess.run(["lualatex", "-interaction", "nonstopmode", tex.name], cwd=d, capture_output=True,
                       text=True, timeout=300, errors="replace")
        log = tex.with_suffix(".log").read_text(errors="replace").split("\n")
        cur = "?"
        seen = set()
        for n, l in enumerate(log):
            mm = re.match(r"WOOLINE (\d+)", l)
            if mm:
                cur = mm.group(1)
            elif l.startswith("!"):
                detail = l
                if "Undefined control sequence" in l:
                    for l2 in log[n + 1:n + 4]:
                        mm2 = re.search(r"(\\[A-Za-z]+)\s*$", l2)
                        if l2.startswith("l.") and mm2:
                            detail += " " + mm2.group(1)
                            break
                key = (cur, detail)
                if key not in seen:
                    seen.add(key)
                    bad += 1
                    print(f"{f.name}:{cur}: [E] matematika: {detail[:160]}")
    print(f"matematika: {total} výrazů, chyb {bad}")
    return bad


PSEUDO_DOC = r"""\documentclass[12pt]{article}
\usepackage{polyglossia}
\setdefaultlanguage{czech}
\usepackage{fontspec}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{xcolor}
\usepackage{algorithm}
\usepackage{algorithmic}
\newcommand\algorithmicprocedure{\textbf{procedure}}
\newcommand{\algorithmicendprocedure}{\algorithmicend\ \algorithmicprocedure}
\makeatletter
\newcommand\PROCEDURE[3][default]{\ALC@it\algorithmicprocedure\ \textsc{#2}(#3)\ALC@com{#1}\begin{ALC@prc}}
\newcommand\ENDPROCEDURE{\end{ALC@prc}\ifthenelse{\boolean{ALC@noend}}{}{\ALC@it\algorithmicendprocedure}}
\newenvironment{ALC@prc}{\begin{ALC@g}}{\end{ALC@g}}
\makeatother
""" + MACROS + r"""
\begin{document}
@@BODY@@
\end{document}
"""


def check_pseudo(files):
    """Zkompiluje každý !pseudocode: v prostředí algorithmic (jako šablona fit-pdf)."""
    d = BUILD / "pseudo"
    d.mkdir(parents=True, exist_ok=True)
    bad = total = 0
    for f in files:
        for env, meta, body, ln in extract(f, ["pseudocode"]):
            total += 1
            num = meta.get("linenumber", "1")
            if not re.match(r"^\d+$", num):
                bad += 1
                print(f"{f.name}:{ln}: [E] !pseudocode: linenumber má být číslo (šablona ho vloží do \\begin{{algorithmic}}[...]), ne '{num}'")
                num = "1"
            tex = d / f"{f.stem}-L{ln}.tex"
            tex.write_text(PSEUDO_DOC.replace("@@BODY@@", "\\begin{algorithmic}[" + num + "]\n" + "\n".join(b for b in body if b.strip()) + "\n\\end{algorithmic}"), encoding="utf-8")
            pdf = tex.with_suffix(".pdf")
            if pdf.exists():
                pdf.unlink()
            run_lualatex(tex)
            if not pdf.exists():
                bad += 1
                print(f"{f.name}:{ln}: [E] !pseudocode: se nezkompiloval: {log_error(tex.with_suffix('.log'))}")
    print(f"pseudokód: {total} bloků, chyb {bad}")
    return bad


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = [Path(a) for a in args] if args else sorted((ROOT / "src").glob("*.woo"))
    bad = (check_math(files) + check_pseudo(files)) if "--math" in sys.argv else check_tikz(files)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
