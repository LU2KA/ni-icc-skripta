#!/usr/bin/env python3
"""Kontrola vytištěného PDF skript: počet stran, záložky, velikost písma a nevysázené vzorce.

  python3 tools/check_pdf.py ../skripta/NI-ICC_skripta.pdf

Chyba (návratový kód 1): v textu zůstal zdroj vzorce (MathJax nedoběhl), nebo je základní písmo
menší než 9 bodů (Chrome zmenšil celý dokument, protože se něco nevešlo na šířku stránky).
"""
import collections
import re
import sys

import pymupdf


def main(path):
    doc = pymupdf.open(path)
    sizes = collections.Counter()
    raw = []
    for page in doc:
        text = page.get_text()
        if re.search(r"\\\(|\\\[|\\[A-Za-z]{2,}", text):
            raw.append(page.number + 1)
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    sizes[round(span["size"], 1)] += len(span["text"])
    base = sizes.most_common(1)[0][0] if sizes else 0
    print(f"stran {len(doc)}, záložek {len(doc.get_toc())}, základní písmo {base} b, "
          f"velikost {doc.metadata and round(len(open(path, 'rb').read()) / 1e6, 1)} MB")
    ok = True
    if raw:
        ok = False
        print(f"[E] nevysázené vzorce na stranách: {raw[:20]}")
    if base < 9:
        ok = False
        print(f"[E] základní písmo je jen {base} b – něco přetéká šířku stránky a Chrome dokument zmenšil")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
