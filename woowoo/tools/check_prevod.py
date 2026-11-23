#!/usr/bin/env python3
"""Úplnost převodu kapitoly z LaTeXu (../latex-skripta/kapitoly/NN-*.tex) do src/NN*.woo.

Použití:  python3 tools/check_prevod.py 08        (kapitola 19 = předloha 14-graf-redukci.tex)
Porovná: štítky (mechanické pravidlo z PRAVIDLA.md), počty obrázků a rámečků, nadpisy oddílů, objem textu.
[E] = chybí něco, co v předloze je (štítek, obrázek, cvičení, oddíl); [W] = počty nesedí, zkontroluj ručně.
Návratový kód 0 = bez [E].
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEX_DIR = ROOT.parent / "latex-skripta" / "kapitoly"
TEX_OF = {"19": "14"}                      # příloha D je předloha 14-graf-redukci.tex
BOX_PREFIX = {"definice": "def", "veta": "thm", "lemma": "lem", "dusledek": "cor", "problem": "prob", "priklad": "ex"}
BOX_OBJECT = {"definice": "Definition", "problem": "Definition", "veta": "Theorem", "lemma": "Lemma",
              "dusledek": "Corollary", "priklad": "Example", "intuice": "Concept", "pozor": "Warning",
              "poznamka": "Remark", "shrnuti": "Remark", "cviceni": "Exercise", "reseni": "Solution",
              "dukaz": "Proof", "figure": "Figure"}


def norm(label):
    return re.sub(r"[:._]", "-", label.lower())


def group(s, i):
    """s[i] == '{' -> (obsah, index za '}')"""
    depth, j = 0, i
    while j < len(s):
        if s[j] == "\\":
            j += 2
            continue
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def words(text):
    return len(re.findall(r"[A-Za-zÀ-ž]{3,}", text))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    nn = sys.argv[1]
    tex_files = sorted(TEX_DIR.glob(TEX_OF.get(nn, nn) + "-*.tex"))
    woo_files = sorted((ROOT / "src").glob(nn + "*.woo"))
    if not tex_files or not woo_files:
        print(f"[E] chybí předloha ({len(tex_files)}) nebo soubory src/{nn}*.woo ({len(woo_files)})")
        return 1
    tex = re.sub(r"(?<!\\)%.*", "", tex_files[0].read_text(encoding="utf-8"))
    woo = "\n".join(f.read_text(encoding="utf-8") for f in woo_files)
    errs = 0

    # ---- štítky
    want = {}
    for m in re.finditer(r"\\label\{([^{}]+)\}", tex):
        want[norm(m.group(1))] = "\\label{" + m.group(1) + "}"
    for m in re.finditer(r"\\begin\{(" + "|".join(BOX_PREFIX) + r")\}\s*\{", tex):
        _, j = group(tex, m.end() - 1)
        k = j
        while k < len(tex) and tex[k] in " \n":
            k += 1
        if k < len(tex) and tex[k] == "{":
            ident, _ = group(tex, k)
            if ident.strip():
                want[norm(BOX_PREFIX[m.group(1)] + "-" + ident.strip())] = f"{m.group(1)} {{{ident}}}"
    for m in re.finditer(r"\\redukce(?:or)?\[([^\]]+)\]|\\hypertarget\{red:([^{}]+)\}", tex):
        ident = m.group(1) or m.group(2)
        want[norm("red-" + ident)] = "redukce [" + ident + "]"
    n_cv = 0
    for m in re.finditer(r"\\begin\{cviceni\}\s*\{", tex):
        n_cv += 1
        title, _ = group(tex, m.end() - 1)
        mm = re.match(r"\s*(\d+)\.(\d+)", title)
        if mm:
            want[f"cv-{mm.group(1)}-{mm.group(2)}"] = "cviceni " + title.strip()[:30]
    # štítek, který je v předloze dvakrát (v kapitole 3 i 12): kapitola 12 ho má pod jiným jménem, nikdo na něj neodkazuje
    for (ch, lab), repl in {("12", "def-konstr"): "def-prostor-konstr"}.items():
        if ch == nn and lab in want:
            want[repl] = want.pop(lab)
    have = set(re.findall(r"^\s*label:\s*'?([a-z0-9-]+)'?\s*$", woo, flags=re.M))
    for lab, src in sorted(want.items()):
        if lab not in have:
            errs += 1
            print(f"[E] chybí štítek {lab}   (předloha: {src})")

    # ---- obrázky
    n_tikz_tex = len(re.findall(r"\\begin\{tikzpicture\}", tex)) + len(re.findall(r"\\begin\{forest\}", tex))
    # tikzpicture uvnitř definice makra (\newcommand ... \begin{tikzpicture}) se nepočítá zvlášť – jen upozornění
    n_tikz_woo = len(re.findall(r"^\s*!tikz:\s*$", woo, flags=re.M))
    if n_tikz_woo < n_tikz_tex:
        errs += 1
        print(f"[E] obrázků !tikz: {n_tikz_woo}, v předloze tikzpicture/forest: {n_tikz_tex}")
    elif n_tikz_woo > n_tikz_tex:
        print(f"[W] obrázků !tikz: {n_tikz_woo}, v předloze jen {n_tikz_tex} (nové obrázky? rozdělené?)")

    # ---- rámečky
    cnt_tex = {}
    for env, obj in BOX_OBJECT.items():
        n = len(re.findall(r"\\begin\{" + env + r"\*?\}", tex))
        cnt_tex[obj] = cnt_tex.get(obj, 0) + n
    cnt_tex["Remark"] = cnt_tex.get("Remark", 0)
    n_red = len(re.findall(r"\\redukce(?:or)?(?![A-Za-z])", tex))
    n_red_woo = len(re.findall(r"^\s*title:\s*'Redukce", woo, flags=re.M)) + len(re.findall(r'^\s*"Redukce(?: s orákulem)?:"\.notion', woo, flags=re.M))
    if n_red_woo < n_red:
        errs += 1
        print(f"[E] hlaviček redukce: {n_red_woo}, v předloze \\redukce/\\redukceor: {n_red}")
    for obj in sorted(cnt_tex):
        n_woo = len(re.findall(r"^\." + obj + r":\s*$", woo, flags=re.M))
        n_tex = cnt_tex[obj]
        if obj == "Remark":
            n_woo -= len(re.findall(r"^\s*title:\s*'Redukce", woo, flags=re.M))
        if obj == "Concept":
            n_woo -= len(re.findall(r"^\s*title:\s*'Proč to děláme'", woo, flags=re.M))
        if obj in ("Exercise", "Solution") and n_woo < n_tex:
            errs += 1
            print(f"[E] .{obj}: {n_woo}, v předloze {n_tex}")
        elif n_woo != n_tex:
            print(f"[W] .{obj}: {n_woo}, v předloze {n_tex} (vnořené rámečky se rozpouštějí – ověř, že obsah nechybí)")
    n_tab_tex = len(re.findall(r"\\begin\{(?:tabular|longtable)\}", tex))
    n_tab_woo = len(re.findall(r"^\s*\.table:\s*$", woo, flags=re.M))
    if n_tab_woo < n_tab_tex:
        print(f"[W] tabulek .table: {n_tab_woo}, v předloze {n_tab_tex}")

    # ---- nadpisy
    n_sec = len(re.findall(r"\\section\*?\{", tex))
    n_sub = len(re.findall(r"\\subsection\*?\{", tex))
    w_sec = len(re.findall(r"^\.Section ", woo, flags=re.M))
    w_sub = len(re.findall(r"^\.Subsection ", woo, flags=re.M))
    if nn in ("02", "03"):        # jediný \section: jeho \subsection jsou povýšené na oddíly (stránky)
        n_sec = 0
    if w_sec + w_sub < n_sec + n_sub:
        errs += 1
        print(f"[E] oddílů a pododdílů: {w_sec} + {w_sub}, v předloze \\section {n_sec} + \\subsection {n_sub}")

    # ---- objem textu (mimo obrázky)
    tex_text = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", " ", tex, flags=re.S)
    tex_text = re.sub(r"\\begin\{forest\}.*?\\end\{forest\}", " ", tex_text, flags=re.S)
    tex_text = re.sub(r"\\(?:newcommand|tikzset|def)\b.*?\n\n", " ", tex_text, flags=re.S)
    tex_text = re.sub(r"\\[A-Za-z]+", " ", tex_text)
    woo_lines, skip = [], None
    for line in woo.split("\n"):
        ind = len(line) - len(line.lstrip(" "))
        if skip is not None:
            if not line.strip() or ind > skip:
                continue
            skip = None
        if re.match(r"^\s*!(tikz|codeblock|pseudocode):\s*$", line):
            skip = ind
            continue
        if re.match(r"^\s*(label|filename|options|columns|include_options|head|type|language):", line):
            continue
        woo_lines.append(line)
    woo_text = re.sub(r"\\[A-Za-z]+|\.(?:notion|emphasize|code|reference|footnote)\b", " ", "\n".join(woo_lines))
    a, b = words(tex_text), words(woo_text)
    ratio = b / a if a else 0
    msg = f"objem textu: předloha {a} slov, převod {b} slov, poměr {ratio:.2f}"
    if ratio < 0.9:
        errs += 1
        print(f"[E] {msg} – část textu chybí (čekám 0,93–1,15)")
    else:
        print(msg)
    print(f"{tex_files[0].name} -> {len(woo_files)} souborů, štítků z předlohy {len(want)}, cvičení {n_cv}, chyb {errs}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
