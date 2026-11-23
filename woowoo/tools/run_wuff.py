#!/usr/bin/env python3
"""Pustí linter wuff (analyzátor z WooWoo Language Serveru) na všechny src/*.woo.

wuff nemá příkazovou řádku, je to jen modul pro Python; tenhle skript ho obsluhuje.
Dialekt FIT Math je kopie z woowoo-language-server (tools/dialects/fit_math.yaml).

Použití:  python3.11 tools/run_wuff.py [soubory]      (wuff musí být nainstalovaný pro daný Python)
"""
import sys
from pathlib import Path

import wuff

ROOT = Path(__file__).resolve().parent.parent
SEV = {wuff.DiagnosticSeverity.Error: "E", wuff.DiagnosticSeverity.Warning: "W",
       wuff.DiagnosticSeverity.Information: "I", wuff.DiagnosticSeverity.Hint: "H"}


def main():
    files = [Path(a).resolve() for a in sys.argv[1:]] or sorted((ROOT / "src").glob("*.woo"))
    an = wuff.WooWooAnalyzer()
    an.set_dialect(str(ROOT / "tools" / "dialects" / "fit_math.yaml"))
    an.load_workspace(ROOT.as_uri())
    counts = {}
    for f in files:
        doc = wuff.TextDocumentIdentifier(f.as_uri())
        lines = f.read_text(encoding="utf-8").split("\n")
        for d in an.diagnose(doc):
            s = SEV.get(d.severity, "?")
            counts[s] = counts.get(s, 0) + 1
            ln = d.range.start.line
            src = lines[ln].strip()[:90] if ln < len(lines) else ""
            print(f"{f.name}:{ln + 1}:{d.range.start.character + 1}: [{s}] {d.message}  | {src}")
    print("wuff: souborů %d, " % len(files) + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) if counts
          else "wuff: souborů %d, bez nálezů" % len(files))
    return 1 if counts.get("E") else 0


if __name__ == "__main__":
    sys.exit(main())
