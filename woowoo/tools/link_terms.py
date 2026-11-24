#!/usr/bin/env python3
"""Vyskakovací definice na hotovém webu skript (spouští tools/build_web.sh po sestavení MkDocs).

  .venv/bin/python tools/link_terms.py [../skripta/html]
  .venv/bin/python tools/link_terms.py --partial .build/preview-NN/site   (náhled části kapitol: nehlásí
                                                                          pojmy z chybějících kapitol)

Co dělá:
  1. Z hotových stránek vytáhne rámečky definic, problémů, vět, lemmat a důsledků (div.admonition s id)
     a k nim přidá pojmy bez rámečku ze src/pojmy.yaml. Vše uloží do javascripts/pojmy-data.js.
  2. V textu každé stránky obalí výskyty pojmů ze src/pojmy.yaml (klíč `text`, každý výskyt) a ve vzorcích \\prob{…} a makra tříd (klíče `prob`, `makro`) odkazem na definici.
     Uvnitř vlastního rámečku definice a v nadpisech se pojem neobaluje.
  3. Do stránek vloží javascripts/pojmy-data.js a javascripts/pojmy.js (okénko po najetí myší).

Okénko se ukazuje i u obyčejných odkazů na rámeček („věta 8.2“). Stránky musí být čerstvě sestavené
(skript stránky mění na místě a podruhé je nezpracuje).
"""
import html
import json
import os
import posixpath
import re
import sys

import markdown
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POJMY = os.environ.get("POJMY") or os.path.join(ROOT, "src", "pojmy.yaml")
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
PARTIAL = "--partial" in sys.argv
SITE = os.path.abspath(ARGS[0] if ARGS else os.path.join(ROOT, "..", "skripta", "html"))
MARK = "pojmy-data.js"

BOX_KINDS = ("definition", "theorem", "lemma", "corollary")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
NO_PROSE = {"a", "code", "pre", "script", "style", "svg", "kbd", "button", "summary", "h1", "h2", "h3", "h4", "h5", "h6"}
NO_MATH = {"a", "summary", "h1", "h2", "h3", "h4", "h5", "h6", "script", "style"}
TOKEN = re.compile(r"<!--.*?-->|<[^>]*>|[^<]+", re.S)
TAGNAME = re.compile(r"</?([A-Za-z][A-Za-z0-9-]*)")
ATTR = lambda name: re.compile(r'\b' + name + r'="([^"]*)"')
CLASS, ID = ATTR("class"), ATTR("id")
TEXT_MODE = re.compile(r"\\(?:text|textrm|textit|textbf|textsf|texttt|mbox|hbox)\s*\{")
PROB = re.compile(r"\\prob\{([^{}]*)\}")
RELATIONS = {r"\redp"}

warnings = []


def warn(msg):
    warnings.append(msg)


def pages():
    out = []
    for d, _, files in os.walk(SITE):
        for f in files:
            if f.endswith(".html") and f != "404.html":
                out.append(os.path.relpath(os.path.join(d, f), SITE).replace(os.sep, "/"))
    return sorted(out)


def article_span(s):
    a = s.find('<article class="md-content__inner')
    if a < 0:
        return None
    a = s.find(">", a) + 1
    return a, s.find("</article>", a)


def match_div(s, start):
    """Konec elementu <div …> začínajícího na pozici start (index za </div>)."""
    depth = 0
    for m in re.finditer(r"<div\b|</div>", s[start:]):
        depth += 1 if m.group(0) == "<div" else -1
        if depth == 0:
            return start + m.end()
    return len(s)


def rootify(fragment, page):
    """Relativní odkazy a obrázky ve fragmentu stránky page přepíše na @R/cesta-od-kořene."""
    base = posixpath.dirname(page)

    def fix(m):
        attr, url = m.group(1), m.group(2)
        if re.match(r"[a-z]+:|//|@R/", url):
            return m.group(0)
        if url.startswith("#"):
            return f'{attr}="@R/{page}{url}"'
        return f'{attr}="@R/{posixpath.normpath(posixpath.join(base, url))}"'
    return re.sub(r'\b(href|src)="([^"]*)"', fix, fragment)


def rel(from_page, to_page, anchor):
    r = posixpath.relpath(to_page, posixpath.dirname(from_page) or ".")
    if anchor is None:                                  # odkaz na celou stránku (oddíl)
        return r
    return (r if to_page != from_page else "") + "#" + anchor


def anchor_of(page, label):
    return None if posixpath.splitext(posixpath.basename(page))[0] == label else label


def collect(site_pages, texts):
    """id -> stránka (všechna id) a rámečky pro okénka."""
    where, boxes = {}, {}
    box_re = re.compile(r'<div class="admonition [^"]*\bwoo-(%s)\b[^"]*" id="([^"]+)">' % "|".join(BOX_KINDS))
    for p in site_pages:
        s = texts[p]
        for m in re.finditer(r'\bid="([^"]+)"', s):
            where.setdefault(m.group(1), p)
        where.setdefault(posixpath.splitext(posixpath.basename(p))[0], p)   # štítek oddílu = jméno stránky
        span = article_span(s)
        if not span:
            continue
        for m in box_re.finditer(s, *span):
            end = match_div(s, m.start())
            inner = s[m.end():end - len("</div>")]
            t = re.match(r'\s*<p class="admonition-title">(.*?)</p>', inner, re.S)
            title, body = (t.group(1), inner[t.end():]) if t else ("", inner)
            boxes[m.group(2)] = {"t": rootify(title, p).strip(), "b": rootify(body, p).strip(),
                                 "u": f"@R/{p}#{m.group(2)}"}
    return where, boxes


def load_terms(where, boxes):
    with open(POJMY, encoding="utf-8") as f:
        entries = yaml.safe_load(f) or []
    md = lambda src: markdown.markdown(src, extensions=["attr_list", "pymdownx.arithmatex"],
                                       extension_configs={"pymdownx.arithmatex": {"generic": True}})
    data, terms = {}, []          # terms: (klíč, stránka cíle, kotva cíle, záznam)
    for e in entries:
        if "box" in e:
            key = e["box"]
            if key not in boxes:
                PARTIAL or warn(f"pojmy.yaml: rámeček {key} na webu není")
                continue
            page, anchor = where[key], key
        else:
            key = e["id"]
            title = re.sub(r"^<p>(.*)</p>$", r"\1", md(e["title"]).strip(), flags=re.S)
            target = e.get("odkaz")
            if target and target not in where:
                PARTIAL or warn(f"pojmy.yaml: {key}: odkaz {target} na webu není")
                target = None
            page = where[target] if target else None
            anchor = anchor_of(page, target) if target else None
            url = (f"@R/{page}" + (f"#{anchor}" if anchor else "")) if page else ""
            data[key] = {"t": title, "b": md(e["body"]), "u": url}
        terms.append((key, page, anchor, e))
    data.update(boxes)
    return data, terms


class Linker:
    def __init__(self, terms):
        self.terms = {k: (p, a) for k, p, a, _ in terms}
        self.prob, self.macro, pats = {}, {}, []
        for key, _, _, e in terms:
            for n in e.get("prob") or []:
                if n in self.prob:
                    warn(f"pojmy.yaml: \\prob{{{n}}} je u {self.prob[n]} i {key}")
                self.prob[n] = key
            for n in e.get("makro") or []:
                self.macro[n] = key
            # anglické názvy a zkratky problémů ze vzorců se hledají i v textu (česká jména ne – pletla by se
            # s obyčejnými slovy, ta patří do `text`)
            auto = [re.escape(n) for n in e.get("prob") or [] if len(n) >= 2 and re.fullmatch(r"[A-Za-z0-9 ()/.-]+", n)
                    and n not in (e.get("bez_textu") or [])]
            for t in (e.get("text") or []) + auto:
                pats.append((key, re.compile(r"(?<![\w-])(?:%s)(?![\w-])" % t)))
        self.pats = pats
        self.any = re.compile("|".join(f"(?:{p.pattern})" for _, p in pats)) if pats else None
        self.macro_re = (re.compile(r"\\(%s)(?![A-Za-z])" % "|".join(sorted(map(re.escape, self.macro), key=len,
                                                                             reverse=True)))
                         if self.macro else None)
        self.count = {"text": 0, "math": 0}

    def href(self, page, key):
        tp, anchor = self.terms[key]
        return rel(page, tp, anchor) if tp else None

    # --- vzorce ---------------------------------------------------------------------------------------
    def math(self, tex, page, skip):
        raw = html.unescape(tex)
        blocked = []
        for m in TEXT_MODE.finditer(raw):
            depth, i = 1, m.end()
            while i < len(raw) and depth:
                depth += {"{": 1, "}": -1}.get(raw[i], 0) if raw[i - 1] != "\\" else 0
                i += 1
            blocked.append((m.start(), i))
        inside = lambda pos: any(a <= pos < b for a, b in blocked)
        hits = []
        for m in PROB.finditer(raw):
            key = self.prob.get(m.group(1))
            if key and key not in skip and not inside(m.start()):
                hits.append((m.start(), m.end(), key))
        if self.macro_re:
            for m in self.macro_re.finditer(raw):
                key = self.macro[m.group(1)]
                if key not in skip and not inside(m.start()):
                    hits.append((m.start(), m.end(), key))
        if not hits:
            return tex
        out, last = [], 0
        for a, b, key in sorted(hits):
            if a < last:
                continue
            inner = r"\class{woo-pk-%s}{%s}" % (key, raw[a:b])
            url = self.href(page, key)
            linked = r"\href{%s}{%s}" % (url, inner) if url else inner
            if raw[a:b] in RELATIONS:                  # \href dělá z relace obyčejný symbol: vrátit mezery
                linked = r"\mathrel{%s}" % linked
            out += [raw[last:a], linked]
            last = b
            self.count["math"] += 1
        out.append(raw[last:])
        return html.escape("".join(out), quote=False)

    # --- text -----------------------------------------------------------------------------------------
    def prose(self, text, page, skip):
        if not self.any or not self.any.search(text):
            return text
        cands = []
        for key, p in self.pats:
            for m in p.finditer(text):
                cands.append((m.start(), -(m.end() - m.start()), m.end(), key))
        cands.sort()
        out, last = [], 0
        for a, _, b, key in cands:
            if a < last or key in skip:
                continue
            url = self.href(page, key)
            w = text[a:b]
            tag = (f'<a class="woo-term" href="{url}" data-pojem="{key}">{w}</a>' if url else
                   f'<span class="woo-term" tabindex="0" data-pojem="{key}">{w}</span>')
            out += [text[last:a], tag]
            last = b
            self.count["text"] += 1
        out.append(text[last:])
        return "".join(out)

    def page(self, s, page):
        span = article_span(s)
        if not span:
            return s
        a, b = span
        stack, out = [], []
        for m in TOKEN.finditer(s, a, b):
            tok = m.group(0)
            if tok.startswith("<!--"):
                out.append(tok)
                continue
            if tok.startswith("<"):
                t = TAGNAME.match(tok)
                name = t.group(1).lower() if t else ""
                if tok.startswith("</"):
                    while stack and stack.pop()[0] != name:
                        pass
                elif name not in VOID and not tok.endswith("/>"):
                    cls = (CLASS.search(tok) or [None, ""])[1].split()
                    idm = ID.search(tok)
                    stack.append((name, cls, idm.group(1) if idm else None))
                out.append(tok)
                continue
            names = {n for n, _, _ in stack}
            classes = {c for _, cl, _ in stack for c in cl}
            skip = {i for _, _, i in stack if i and i in self.terms}
            if "arithmatex" in classes:
                out.append(tok if names & NO_MATH else self.math(tok, page, skip))
            elif names & NO_PROSE or "admonition-title" in classes:
                out.append(tok)
            else:
                out.append(self.prose(tok, page, skip))
        return s[:a] + "".join(out) + s[b:]


def main():
    site_pages = pages()
    texts = {}
    for p in site_pages:
        with open(os.path.join(SITE, p), encoding="utf-8") as f:
            texts[p] = f.read()
    if any(MARK in t for t in texts.values()):
        sys.exit("link_terms: stránky už jsou zpracované – nejdřív znovu sestav web (tools/build_web.sh)")
    where, boxes = collect(site_pages, texts)
    data, terms = load_terms(where, boxes)
    linker = Linker(terms)
    os.makedirs(os.path.join(SITE, "javascripts"), exist_ok=True)
    with open(os.path.join(SITE, "javascripts", MARK), "w", encoding="utf-8") as f:
        f.write("// GENEROVÁNO skriptem tools/link_terms.py\nwindow.WOO_POJMY = ")
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    for p in site_pages:
        s = linker.page(texts[p], p)
        js = posixpath.relpath("javascripts", posixpath.dirname(p) or ".")
        s = s.replace("</body>", f'<script src="{js}/{MARK}"></script><script src="{js}/pojmy.js"></script>\n</body>', 1)
        with open(os.path.join(SITE, p), "w", encoding="utf-8") as f:
            f.write(s)
    for w in warnings:
        print("[W]", w)
    print(f"link_terms: pojmů {len(terms)}, okének {len(data)}, odkazů v textu {linker.count['text']}, "
          f"ve vzorcích {linker.count['math']}")


if __name__ == "__main__":
    main()
